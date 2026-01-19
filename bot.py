"""
CFA Trainer Automation Bot
Запуск: python bot.py
"""


import logging



from modules.telegram_bot import create_bot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)



def main():
    print("=" * 50)
    print("  AUTOMATION BOT")
    print("  Starting...")
    print("=" * 50)
    
    bot = create_bot()
    if bot:
        print("Bot started! Press Ctrl+C to stop.")
        import asyncio
        bot.run_polling()
    else:
        print("ERROR: Could not create bot. Check TELEGRAM_BOT_TOKEN in .env")

if __name__ == "__main__":
    main()