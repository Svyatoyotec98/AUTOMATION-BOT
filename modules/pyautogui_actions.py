import pyautogui
import pyperclip
import time
from config import COORDINATES, PYAUTOGUI_PAUSE, FAILSAFE

# Безопасность: остановка при перемещении мыши в угол
pyautogui.FAILSAFE = FAILSAFE
pyautogui.PAUSE = PYAUTOGUI_PAUSE

def click_ask_claude_field():
    """Кликнуть в поле 'Ask Claude to write code...'"""
    coords = COORDINATES["claude_code"]["ask_field"]
    pyautogui.click(coords[0], coords[1])
    time.sleep(0.5)

def click_reply_field():
    """Кликнуть в поле Reply"""
    coords = COORDINATES["claude_code"]["reply_field"]
    pyautogui.click(coords[0], coords[1])
    time.sleep(0.5)

def type_text(text):
    """Ввести текст (через буфер обмена для кириллицы)"""
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)

def press_enter():
    """Нажать Enter"""
    pyautogui.press('enter')

def send_prompt_to_claude(prompt):
    """Отправить промпт в Claude Code"""
    print(f"[PyAutoGUI] Отправляю промпт в Claude Code...")
    
    # 1. Кликнуть в поле ввода
    click_ask_claude_field()
    time.sleep(1)
    
    # 2. Ввести текст
    type_text(prompt)
    time.sleep(0.5)
    
    # 3. Отправить
    press_enter()
    
    print(f"[PyAutoGUI] Промпт отправлен!")
    return True

def refresh_page():
    """Обновить страницу (F5)"""
    pyautogui.press('f5')
    time.sleep(3)