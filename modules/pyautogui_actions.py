import pyautogui
import pyperclip
import time
import keyboard
from config import COORDINATES, PYAUTOGUI_PAUSE, FAILSAFE

# Безопасность: остановка при перемещении мыши в угол
pyautogui.FAILSAFE = FAILSAFE
pyautogui.PAUSE = PYAUTOGUI_PAUSE

def click_ask_claude_field():
    """Кликнуть в поле 'Ask Claude to write code...'"""
    pyautogui.click(30, 214)
    time.sleep(0.5)

def click_reply_field():
    """Кликнуть в поле Reply"""
    coords = COORDINATES["claude_code"]["reply_field"]
    pyautogui.click(coords[0], coords[1])
    time.sleep(0.5)

def type_text(text):
    """Ввести текст (через буфер обмена для кириллицы)"""
    pyperclip.copy(text)
    keyboard.press_and_release('ctrl+v')
    time.sleep(0.3)

def press_enter():
    """Нажать Enter"""
    keyboard.press_and_release('enter')

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

def click_code_button():
    """Кликнуть по кнопке 'Code' в сайдбаре"""
    pyautogui.click(38, 337)
    time.sleep(0.5)

def launch_module_tasks(glossary_prompt, tests_prompt):
    """
    Запустить модуль в модульном режиме (glossary + tests)

    Args:
        glossary_prompt: промпт для создания глоссария
        tests_prompt: промпт для создания тестов

    Алгоритм:
        1. Code → ждать 5 сек → Ctrl+V (glossary) → Enter → Ctrl+Shift+Tab
        2. Code → ждать 5 сек → Ctrl+V (tests) → Enter → Ctrl+Shift+Tab
    """
    print("[PyAutoGUI] Запуск модуля: Glossary + Tests...")

    # === GLOSSARY ===
    print("[PyAutoGUI] [1/8] Кликаю Code для Glossary...")
    click_code_button()

    print("[PyAutoGUI] [2/8] Жду 5 сек загрузки...")
    time.sleep(5)

    print("[PyAutoGUI] [3/8] Вставляю промпт Glossary...")
    type_text(glossary_prompt)

    print("[PyAutoGUI] [4/8] Отправляю промпт...")
    press_enter()
    time.sleep(1)

    print("[PyAutoGUI] [5/8] Возвращаюсь на чат (Ctrl+Shift+Tab)...")
    keyboard.press_and_release('ctrl+shift+tab')
    time.sleep(2)  # Критично: ждём стабилизации вкладки

    # === TESTS ===
    print("[PyAutoGUI] [6/8] Пауза перед запуском Tests...")
    time.sleep(1)

    print("[PyAutoGUI] [7/8] Кликаю Code для Tests...")
    click_code_button()

    print("[PyAutoGUI] [8/8] Жду 5 сек загрузки...")
    time.sleep(5)

    print("[PyAutoGUI] [9/8] Вставляю промпт Tests...")
    type_text(tests_prompt)

    print("[PyAutoGUI] [10/8] Отправляю промпт...")
    press_enter()
    time.sleep(1)

    print("[PyAutoGUI] [11/8] Возвращаюсь на чат (Ctrl+Shift+Tab)...")
    keyboard.press_and_release('ctrl+shift+tab')
    time.sleep(2)  # Критично: ждём стабилизации вкладки

    print("[PyAutoGUI] ✅ Модуль запущен! Обе задачи отправлены.")
    return True

def close_glossary_tab():
    """
    Закрыть вкладку glossary после merge

    Алгоритм:
        Ctrl+Tab → Ctrl+Tab → Ctrl+W
        После этого мы на вкладке tests
    """
    print("[PyAutoGUI] Закрываю вкладку Glossary...")

    # Переключиться на следующую вкладку
    keyboard.press_and_release('ctrl+tab')
    time.sleep(0.5)

    # Ещё раз переключиться
    keyboard.press_and_release('ctrl+tab')
    time.sleep(0.5)

    # Закрыть вкладку
    keyboard.press_and_release('ctrl+w')
    time.sleep(0.5)

    print("[PyAutoGUI] Вкладка Glossary закрыта. Теперь на Tests.")
    return True

def close_tests_tab():
    """
    Закрыть вкладку tests после merge

    Алгоритм:
        Ctrl+W
        После этого мы на вкладке чат
    """
    print("[PyAutoGUI] Закрываю вкладку Tests...")

    # Закрыть вкладку
    keyboard.press_and_release('ctrl+w')
    time.sleep(0.5)

    print("[PyAutoGUI] Вкладка Tests закрыта. Теперь на Чат.")
    return True