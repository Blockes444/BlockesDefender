import os
import datetime
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import asyncio

# ==================== НАСТРОЙКИ БОТА ====================
user_data_file = "/data/user_data.json"

# Прогрессивная система мутов
MUTE_LEVELS = [1, 5, 10, 30, 60]  # минуты
RESET_TIME = 3 * 60 * 60  # 3 часа в секундах

# ... (ВЕСЬ код бота из предыдущих сообщений, но УБЕРИТЕ блок с Flask)
# Уберите эти строки:
# from flask import Flask
# from threading import Thread
# app = Flask('')
# и весь код связанный с Flask

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        print("❌ Токен бота не найден!")
        return
    
    print("🤖 BlockesDefender Bot запускается...")
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
    
    print("✅ BlockesDefender готов к работе!")
    application.run_polling()

if __name__ == '__main__':
    main()
