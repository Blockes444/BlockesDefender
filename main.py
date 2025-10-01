from flask import Flask
from threading import Thread
import os
import datetime
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import asyncio

# ==================== ВЕБ-СЕРВЕР ДЛЯ UPTIMEROBOT ====================
app = Flask('')

@app.route('/')
def home():
    return "✅ Telegram Admin Bot is Alive! | Blockes444 System"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Запускаем веб-сервер
keep_alive()

# ==================== НАСТРОЙКИ БОТА ====================
user_data_file = "user_data.json"

# Прогрессивная система мутов
MUTE_LEVELS = [1, 5, 10, 30, 60]  # минуты
RESET_TIME = 3 * 60 * 60  # 3 часа в секундах

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ====================
def load_user_data():
    """Загрузка данных пользователей из файла"""
    try:
        with open(user_data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_user_data(data):
    """Сохранение данных пользователей в файл"""
    try:
        with open(user_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения данных: {e}")

def get_next_mute_duration(user_id):
    """Получить следующую длительность мута по прогрессивной системе"""
    user_data = load_user_data()
    user_id_str = str(user_id)
    
    # Инициализация пользователя если нет в базе
    if user_id_str not in user_data:
        user_data[user_id_str] = {
            'mute_level': 0,
            'last_mute_time': None,
            'total_mutes': 0,
            'first_mute_time': None
        }
    
    user = user_data[user_id_str]
    current_time = datetime.datetime.now().timestamp()
    
    # Проверяем ресет каждые 3 часа
    if user['last_mute_time'] and (current_time - user['last_mute_time']) > RESET_TIME:
        user['mute_level'] = 0  # Сбрасываем уровень
        user['total_mutes'] = 0
    
    # Получаем текущий уровень
    current_level = user['mute_level']
    if current_level >= len(MUTE_LEVELS):
        current_level = len(MUTE_LEVELS) - 1  # Максимальный уровень
    
    mute_duration = MUTE_LEVELS[current_level]
    
    # Увеличиваем уровень и обновляем время
    user['mute_level'] = current_level + 1
    user['last_mute_time'] = current_time
    user['total_mutes'] += 1
    
    if not user['first_mute_time']:
        user['first_mute_time'] = current_time
    
    save_user_data(user_data)
    return mute_duration, current_level + 1

def reset_user_mute_level(user_id):
    """Сбросить уровень мута пользователя"""
    user_data = load_user_data()
    user_id_str = str(user_id)
    
    if user_id_str in user_data:
        user_data[user_id_str]['mute_level'] = 0
        user_data[user_id_str]['total_mutes'] = 0
        save_user_data(user_data)
        return True
    return False

def get_user_mute_info(user_id):
    """Получить информацию о мутах пользователя"""
    user_data = load_user_data()
    user_id_str = str(user_id)
    
    if user_id_str not in user_data:
        return {
            'level': 0,
            'total_mutes': 0,
            'last_mute': None,
            'first_mute': None,
            'next_mute': MUTE_LEVELS[0]
        }
    
    user = user_data[user_id_str]
    current_level = user['mute_level']
    next_mute = MUTE_LEVELS[current_level] if current_level < len(MUTE_LEVELS) else 60
    
    return {
        'level': current_level,
        'total_mutes': user['total_mutes'],
        'last_mute': user['last_mute_time'],
        'first_mute': user['first_mute_time'],
        'next_mute': next_mute
    }

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверка является ли пользователь администратором"""
    try:
        user = update.effective_user
        chat = update.effective_chat
        
        if chat.type == 'private':
            return True  # В личных сообщениях все команды доступны
            
        admins = await context.bot.get_chat_administrators(chat.id)
        admin_ids = [admin.user.id for admin in admins]
        
        return user.id in admin_ids
    except Exception as e:
        print(f"❌ Ошибка проверки админки: {e}")
        return False

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить целевого пользователя из сообщения"""
    try:
        # Если это ответ на сообщение
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user
        
        # Если есть аргументы (упоминание)
        if context.args:
            # В реальном боте здесь должна быть логика поиска по username
            # Для демо возвращаем None
            return None
            
        return update.effective_user
    except Exception as e:
        print(f"❌ Ошибка получения пользователя: {e}")
        return None

def format_time(timestamp):
    """Форматирование времени"""
    if not timestamp:
        return "никогда"
    return datetime.datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")

# ==================== КОМАНДЫ БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

🤖 <b>Blockes444 Admin Bot</b>
Система прогрессивной модерации

⚡ <b>Система мутов:</b>
1️⃣ 1-е нарушение: <b>1 минута</b>
2️⃣ 2-е нарушение: <b>5 минут</b>  
3️⃣ 3-е нарушение: <b>10 минут</b>
4️⃣ 4-е нарушение: <b>30 минут</b>
5️⃣ 5-е нарушение: <b>60 минут</b>

🔄 <b>Авто-ресет:</b> каждые <b>3 часа</b>

📝 Используйте /help для списка команд
    """
    
    await update.message.reply_text(welcome_text, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🛠️ <b>КОМАНДЫ БОТА</b>

👮‍♂️ <b>ДЛЯ АДМИНИСТРАТОРОВ:</b>
/mute - прогрессивный мут (ответом на сообщение)
/unmute - размутить (ответом на сообщение)  
/ban - забанить (ответом на сообщение)
/warn - выдать предупреждение
/reset_mute - сбросить уровень мута
/clear_mutes - очистить всю статистику

📊 <b>ИНФОРМАЦИЯ:</b>
/status - статус бота
/my_mute - мой уровень мута
/mute_info - информация о мутах пользователя
/stats - статистика сервера

⚙️ <b>СИСТЕМА МУТОВ:</b>
• Прогрессивная система: 1м → 5м → 10м → 30м → 60м
• Авто-сброс через 3 часа
• Уровень сохраняется между нарушениями
    """
    
    await update.message.reply_text(help_text, parse_mode='HTML')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status"""
    user_data = load_user_data()
    total_users = len(user_data)
    total_mutes = sum(user['total_mutes'] for user in user_data.values())
    
    status_text = f"""
📊 <b>СТАТУС БОТА</b>

⏰ <b>Время:</b> {datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")}
👥 <b>Пользователей в базе:</b> {total_users}
🔇 <b>Всего мутов выдано:</b> {total_mutes}
✅ <b>Статус:</b> Работает нормально

⚡ <b>Прогрессивная система:</b>
🔄 Авто-ресет: каждые 3 часа
📈 Уровни: 1м → 5м → 10м → 30м → 60м

🤖 <b>Blockes444 System</b>
    """
    
    await update.message.reply_text(status_text, parse_mode='HTML')

# ==================== КОМАНДЫ МОДЕРАЦИИ ====================
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mute"""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ <b>Эта команда только для администраторов!</b>", parse_mode='HTML')
        return
    
    target_user = await get_target_user(update, context)
    if not target_user:
        await update.message.reply_text(
            "❌ <b>Укажите пользователя!</b>\n"
            "Ответьте командой /mute на сообщение пользователя", 
            parse_mode='HTML'
        )
        return
    
    try:
        # Получаем причину из аргументов
        reason = " ".join(context.args) if context.args else "Нарушение правил"
        
        # Получаем длительность мута по прогрессивной системе
        mute_duration, mute_level = get_next_mute_duration(target_user.id)
        mute_info = get_user_mute_info(target_user.id)
        
        # Устанавливаем мут
        until_date = datetime.datetime.now() + datetime.timedelta(minutes=mute_duration)
        chat_permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id,
            permissions=chat_permissions,
            until_date=until_date
        )
        
        # Сообщение о муте
        mute_message = await update.message.reply_text(
            f"🔇 <b>Пользователь получил мут!</b>\n\n"
            f"👤 <b>Пользователь:</b> {target_user.mention_html()}\n"
            f"⏰ <b>Длительность:</b> {mute_duration} минут\n"
            f"📈 <b>Уровень мута:</b> {mute_level}/5\n"
            f"🔢 <b>Всего мутов:</b> {mute_info['total_mutes']}\n"
            f"📝 <b>Причина:</b> {reason}\n\n"
            f"🔄 <b>Следующее нарушение:</b> {mute_info['next_mute']} минут",
            parse_mode='HTML'
        )
        
        # Авто-удаление через 15 секунд
        await asyncio.sleep(15)
        await mute_message.delete()
        
    except Exception as e:
        await update.message.reply_text(f"❌ <b>Ошибка:</b> {str(e)}", parse_mode='HTML')

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /unmute"""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ <b>Эта команда только для администраторов!</b>", parse_mode='HTML')
        return
    
    target_user = await get_target_user(update, context)
    if not target_user:
        await update.message.reply_text(
            "❌ <b>Укажите пользователя!</b>\n"
            "Ответьте командой /unmute на сообщение пользователя", 
            parse_mode='HTML'
        )
        return
    
    try:
        # Снимаем все ограничения
        chat_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id,
            permissions=chat_permissions
        )
        
        # Сбрасываем уровень мута
        reset_user_mute_level(target_user.id)
        
        message = await update.message.reply_text(
            f"🔊 <b>Пользователь размучен!</b>\n"
            f"👤 {target_user.mention_html()}\n"
            f"🔄 Уровень мута сброшен",
            parse_mode='HTML'
        )
        
        await asyncio.sleep(10)
        await message.delete()
        
    except Exception as e:
        await update.message.reply_text(f"❌ <b>Ошибка:</b> {str(e)}", parse_mode='HTML')

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /warn"""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ <b>Эта команда только для администраторов!</b>", parse_mode='HTML')
        return
    
    target_user = await get_target_user(update, context)
    if not target_user:
        await update.message.reply_text(
            "❌ <b>Укажите пользователя!</b>\n"
            "Ответьте командой /warn на сообщение пользователя", 
            parse_mode='HTML'
        )
        return
    
    reason = " ".join(context.args) if context.args else "Нарушение правил"
    
    warn_message = await update.message.reply_text(
        f"⚠️ <b>Предупреждение выдано!</b>\n\n"
        f"👤 <b>Пользователь:</b> {target_user.mention_html()}\n"
        f"📝 <b>Причина:</b> {reason}\n\n"
        f"💡 <b>Следующее нарушение</b> может привести к муту",
        parse_mode='HTML'
    )
    
    await asyncio.sleep(10)
    await warn_message.delete()

async def reset_mute_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reset_mute"""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ <b>Эта команда только для администраторов!</b>", parse_mode='HTML')
        return
    
    target_user = await get_target_user(update, context)
    if not target_user:
        await update.message.reply_text(
            "❌ <b>Укажите пользователя!</b>\n"
            "Ответьте командой /reset_mute на сообщение пользователя", 
            parse_mode='HTML'
        )
        return
    
    if reset_user_mute_level(target_user.id):
        message = await update.message.reply_text(
            f"🔄 <b>Уровень мута сброшен!</b>\n"
            f"👤 {target_user.mention_html()}\n"
            f"📊 Теперь следующий мут: 1 минута",
            parse_mode='HTML'
        )
    else:
        message = await update.message.reply_text(
            f"❌ <b>Пользователь не найден в базе!</b>\n"
            f"👤 {target_user.mention_html()}",
            parse_mode='HTML'
        )
    
    await asyncio.sleep(10)
    await message.delete()

# ==================== КОМАНДЫ ИНФОРМАЦИИ ====================
async def my_mute_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /my_mute"""
    user = update.effective_user
    mute_info = get_user_mute_info(user.id)
    
    level_text = f"""
📊 <b>ВАША СТАТИСТИКА МУТОВ</b>

👤 <b>Пользователь:</b> {user.mention_html()}
📈 <b>Текущий уровень:</b> {mute_info['level']}/5
🔢 <b>Всего мутов:</b> {mute_info['total_mutes']}
⏰ <b>Следующий мут:</b> {mute_info['next_mute']} минут

🕒 <b>Последний мут:</b> {format_time(mute_info['last_mute'])}
📅 <b>Первый мут:</b> {format_time(mute_info['first_mute'])}

🔄 <b>Система сбрасывается</b> каждые 3 часа
    """
    
    await update.message.reply_text(level_text, parse_mode='HTML')

async def mute_info_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mute_info"""
    target_user = await get_target_user(update, context)
    if not target_user:
        target_user = update.effective_user
    
    mute_info = get_user_mute_info(target_user.id)
    
    level_text = f"""
📊 <b>СТАТИСТИКА МУТОВ</b>

👤 <b>Пользователь:</b> {target_user.mention_html()}
📈 <b>Текущий уровень:</b> {mute_info['level']}/5
🔢 <b>Всего мутов:</b> {mute_info['total_mutes']}
⏰ <b>Следующий мут:</b> {mute_info['next_mute']} минут

🕒 <b>Последний мут:</b> {format_time(mute_info['last_mute'])}
📅 <b>Первый мут:</b> {format_time(mute_info['first_mute'])}

🔄 <b>Система сбрасывается</b> каждые 3 часа
    """
    
    await update.message.reply_text(level_text, parse_mode='HTML')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats"""
    user_data = load_user_data()
    
    total_users = len(user_data)
    total_mutes = sum(user['total_mutes'] for user in user_data.values())
    
    # Пользователи с наибольшим количеством мутов
    top_muted = sorted(
        [(user_id, data['total_mutes']) for user_id, data in user_data.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    stats_text = f"""
📈 <b>СТАТИСТИКА СЕРВЕРА</b>

👥 <b>Всего пользователей:</b> {total_users}
🔇 <b>Всего мутов выдано:</b> {total_mutes}

🏆 <b>Топ по мутам:</b>
"""
    
    for i, (user_id, mutes) in enumerate(top_muted, 1):
        stats_text += f"{i}. ID {user_id}: {mutes} мутов\n"
    
    stats_text += f"\n🤖 <b>Blockes444 System</b>"
    
    await update.message.reply_text(stats_text, parse_mode='HTML')

async def clear_mutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /clear_mutes"""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ <b>Эта команда только для администраторов!</b>", parse_mode='HTML')
        return
    
    # Создаем пустую базу данных
    save_user_data({})
    
    message = await update.message.reply_text(
        "🗑️ <b>Вся статистика мутов очищена!</b>\n"
        "📊 База данных сброшена",
        parse_mode='HTML'
    )
    
    await asyncio.sleep(10)
    await message.delete()

# ==================== ЗАПУСК БОТА ====================
def main():
    """Основная функция запуска бота"""
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ Токен бота не найден! Установите TELEGRAM_BOT_TOKEN в Secrets")
        return
    
    print("🤖 Запуск Telegram Admin Bot...")
    print("🔧 Инициализация приложения...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    commands = [
        ('start', start),
        ('help', help_command),
        ('status', status),
        ('mute', mute_user),
        ('unmute', unmute_user),
        ('warn', warn_user),
        ('reset_mute', reset_mute_level),
        ('my_mute', my_mute_info),
        ('mute_info', mute_info_user),
        ('stats', stats_command),
        ('clear_mutes', clear_mutes),
    ]
    
    for command, handler in commands:
        application.add_handler(CommandHandler(command, handler))
    
    print("✅ Обработчики команд добавлены")
    print("🚀 Бот запускается...")
    
    # Запускаем бота
    application.run_polling()
    print("✅ Бот успешно запущен!")

if __name__ == '__main__':
    main()