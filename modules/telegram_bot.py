from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID
from projects.cfa.config import BOOKS
from projects.cfa.prompts import generate_prompt

# Состояние пользователя
user_state = {}

def create_bot():
    """Создать и настроить бота"""
    if not TELEGRAM_BOT_TOKEN:
        return None
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(None).concurrent_updates(False).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    return app

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    keyboard = [
        [
            InlineKeyboardButton("📊 CFA", callback_data="project_cfa"),
            InlineKeyboardButton("🇪🇸 Spanish (скоро)", callback_data="project_spanish"),
        ],
        [
            InlineKeyboardButton("📈 Status", callback_data="status"),
            InlineKeyboardButton("⏸️ Пауза", callback_data="pause"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *AUTOMATION BOT*\n\nВыберите проект:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # === ГЛАВНОЕ МЕНЮ ===
    if data == "project_cfa":
        await show_cfa_menu(query)
    
    elif data == "project_spanish":
        await query.edit_message_text("🇪🇸 Spanish - в разработке!\n\nВозвращайтесь позже.")
    
    elif data == "status":
        await show_status(query)
    
    elif data == "pause":
        await toggle_pause(query)
    
    elif data == "back_main":
        await show_main_menu(query)
    
    # === CFA МЕНЮ ===
    elif data == "cfa_tests":
        user_state[user_id] = {"type": "tests"}
        await show_books_menu(query, "tests")
    
    elif data == "cfa_glossary":
        user_state[user_id] = {"type": "glossary"}
        await show_books_menu(query, "glossary")
    
    elif data == "cfa_merge":
        await do_merge(query)
    
    elif data == "back_cfa":
        await show_cfa_menu(query)
    
    # === ВЫБОР КНИГИ ===
    elif data.startswith("book_"):
        book_code = data.replace("book_", "")
        user_state[user_id]["book"] = book_code
        await show_modules_menu(query, book_code)
    
    elif data == "back_books":
        content_type = user_state.get(user_id, {}).get("type", "tests")
        await show_books_menu(query, content_type)
    
    # === ВЫБОР МОДУЛЯ ===
    elif data.startswith("module_"):
        module_num = int(data.replace("module_", ""))
        user_state[user_id]["module"] = module_num
        await show_confirmation(query, user_id)
    
    elif data == "back_modules":
        book_code = user_state.get(user_id, {}).get("book", "quants")
        await show_modules_menu(query, book_code)
    
    # === ПОДТВЕРЖДЕНИЕ ===
    elif data == "confirm_yes":
        await execute_task(query, user_id)
    
    elif data == "confirm_no":
        book_code = user_state.get(user_id, {}).get("book", "quants")
        await show_modules_menu(query, book_code)


async def show_main_menu(query):
    """Главное меню"""
    keyboard = [
        [
            InlineKeyboardButton("📊 CFA", callback_data="project_cfa"),
            InlineKeyboardButton("🇪🇸 Spanish (скоро)", callback_data="project_spanish"),
        ],
        [
            InlineKeyboardButton("📈 Status", callback_data="status"),
            InlineKeyboardButton("⏸️ Пауза", callback_data="pause"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🤖 *AUTOMATION BOT*\n\nВыберите проект:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def show_cfa_menu(query):
    """CFA меню"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Тесты", callback_data="cfa_tests"),
            InlineKeyboardButton("📖 Глоссарий", callback_data="cfa_glossary"),
        ],
        [
            InlineKeyboardButton("🔀 Merge", callback_data="cfa_merge"),
            InlineKeyboardButton("◀️ Назад", callback_data="back_main"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📊 *CFA Level 1*\n\nВыберите тип контента:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def show_books_menu(query, content_type):
    """Меню выбора книги"""
    type_emoji = "📝" if content_type == "tests" else "📖"
    type_name = "Тесты" if content_type == "tests" else "Глоссарий"
    
    keyboard = [
        [
            InlineKeyboardButton("QM", callback_data="book_quants"),
            InlineKeyboardButton("ECON", callback_data="book_econ"),
            InlineKeyboardButton("FSA", callback_data="book_fsa"),
        ],
        [
            InlineKeyboardButton("CF", callback_data="book_cf"),
            InlineKeyboardButton("EI", callback_data="book_equity"),
            InlineKeyboardButton("FI", callback_data="book_fi"),
        ],
        [
            InlineKeyboardButton("DER", callback_data="book_der"),
            InlineKeyboardButton("ALT", callback_data="book_alt"),
            InlineKeyboardButton("PM", callback_data="book_pm"),
        ],
        [
            InlineKeyboardButton("ETH", callback_data="book_ethics"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="back_cfa"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"{type_emoji} *CFA {type_name}*\n\nВыберите книгу:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def show_modules_menu(query, book_code):
    """Меню выбора модуля"""
    book = BOOKS.get(book_code, {})
    book_name = book.get("name", book_code)
    total_modules = book.get("modules", 10)
    
    # Создаем кнопки для модулей (по 5 в ряд)
    keyboard = []
    row = []
    for i in range(1, total_modules + 1):
        row.append(InlineKeyboardButton(str(i), callback_data=f"module_{i}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_books")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📚 *{book_name}*\n\nВыберите модуль:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def show_confirmation(query, user_id):
    """Подтверждение запуска"""
    state = user_state.get(user_id, {})
    content_type = state.get("type", "tests")
    book_code = state.get("book", "quants")
    module_num = state.get("module", 1)
    
    book = BOOKS.get(book_code, {})
    book_name = book.get("name", book_code)
    
    type_emoji = "📝" if content_type == "tests" else "📖"
    type_name = "Тесты" if content_type == "tests" else "Глоссарий"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Запустить", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Отмена", callback_data="confirm_no"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚡ *Подтверждение*\n\n"
        f"{type_emoji} Тип: {type_name}\n"
        f"📚 Книга: {book_name}\n"
        f"📖 Модуль: {module_num}\n\n"
        f"Запустить задачу?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def execute_task(query, user_id):
    """Запуск задачи"""
    state = user_state.get(user_id, {})
    content_type = state.get("type", "tests")
    book_code = state.get("book", "quants")
    module_num = state.get("module", 1)
    
    book = BOOKS.get(book_code, {})
    book_name = book.get("name", book_code)
    
    # Генерируем промпт
    prompt = generate_prompt(content_type, book_name, module_num)
    
    # TODO: Отправить промпт в Claude Code через PyAutoGUI
    # from modules.pyautogui_actions import send_prompt_to_claude
    # send_prompt_to_claude(prompt)
    
    type_name = "Тесты" if content_type == "tests" else "Глоссарий"
    
    await query.edit_message_text(
        f"🚀 *Задача запущена!*\n\n"
        f"📝 {type_name} для {book_name} Module {module_num}\n"
        f"⏱️ Примерное время: 20-40 мин\n\n"
        f"Промпт отправлен в Claude Code\n"
        f"Мониторинг GitHub запущен...\n\n"
        f"_Я сообщу когда будет готово!_",
        parse_mode="Markdown"
    )


async def show_status(query):
    """Показать статус"""
    await query.edit_message_text(
        "📈 *Статус системы*\n\n"
        "🟢 Бот работает\n"
        "🟡 Мониторинг: не активен\n\n"
        "Текущие задачи: нет\n"
        "Открытые ветки: проверьте GitHub",
        parse_mode="Markdown"
    )


async def toggle_pause(query):
    """Переключить паузу"""
    await query.edit_message_text(
        "⏸️ *Режим паузы*\n\n"
        "Скрипт приостановлен.\n"
        "Claude Code НЕ будет получать новые команды.\n\n"
        "Мониторинг GitHub продолжается.\n"
        "Ты можешь работать вручную.",
        parse_mode="Markdown"
    )


async def do_merge(query):
    """Выполнить merge"""
    # TODO: Реализовать merge через git_operations
    await query.edit_message_text(
        "🔀 *Merge*\n\n"
        "Функция в разработке.\n\n"
        "Пока используй команды вручную:\n"
        "`git fetch origin`\n"
        "`git checkout main`\n"
        "`git merge <branch>`",
        parse_mode="Markdown"
    )