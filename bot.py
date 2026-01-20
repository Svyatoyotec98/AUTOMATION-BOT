"""
CFA Trainer Automation Bot
Запуск: py -3.12 bot.py
"""

import asyncio
import logging
from modules.telegram_bot import create_bot
from modules.background_monitor import background_monitor_loop
from config import TELEGRAM_ADMIN_ID

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

    app = create_bot()
    if not app:
        print("ERROR: Could not create bot. Check TELEGRAM_BOT_TOKEN in .env")
        return

    if TELEGRAM_ADMIN_ID:
        print(f"Background monitoring enabled for admin ID: {TELEGRAM_ADMIN_ID}")
        
        # Добавляем фоновый мониторинг через post_init
        async def post_init(application):
            asyncio.create_task(
                background_monitor_loop(application.bot, int(TELEGRAM_ADMIN_ID))
            )
        
        app.post_init = post_init
    else:
        print("WARNING: TELEGRAM_ADMIN_ID not set, notifications disabled")

    print("Bot started! Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()