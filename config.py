import os
from dotenv import load_dotenv

load_dotenv()

# === TELEGRAM ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

# === GITHUB ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# === ТАЙМАУТЫ ===
TASK_TIMEOUT_MINUTES = 60
CHECK_INTERVAL_SECONDS = 300
HEARTBEAT_INTERVAL_SECONDS = 600

# === PYAUTOGUI ===
PYAUTOGUI_PAUSE = 0.5
FAILSAFE = True

# === КООРДИНАТЫ (настроить под свой экран!) ===
COORDINATES = {
    "claude_code": {
        "ask_field": (150, 153),
        "reply_field": (600, 700),
    }
}