"""
CFA Trainer Automation Bot
Запуск: python bot.py
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

async def main():
    print("=" * 50)
    print("  AUTOMATION BOT")
    print("  Starting...")
    print("=" * 50)

    app = create_bot()
    if not app:
        print("ERROR: Could not create bot. Check TELEGRAM_BOT_TOKEN in .env")
        return

    # Запускаем с фоновым мониторингом если есть ADMIN_ID
    if TELEGRAM_ADMIN_ID:
        print(f"Background monitoring enabled for admin ID: {TELEGRAM_ADMIN_ID}")
        async with app:
            await app.initialize()
            await app.start()

            # Запускаем мониторинг в фоне
            monitor_task = asyncio.create_task(
                background_monitor_loop(app.bot, int(TELEGRAM_ADMIN_ID))
            )

            print("Bot started! Press Ctrl+C to stop.")

            try:
                await app.updater.start_polling()
                # Ждём бесконечно
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                print("\nStopping bot...")
            finally:
                monitor_task.cancel()
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
    else:
        print("WARNING: TELEGRAM_ADMIN_ID not set, notifications disabled")
        print("Bot started! Press Ctrl+C to stop.")
        app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())