from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID
from projects.cfa.config import BOOKS
from projects.cfa.prompts import generate_prompt
from modules.pyautogui_actions import send_prompt_to_claude, launch_module_tasks, close_glossary_tab, close_tests_tab
from modules import task_storage
from modules.github_monitor import get_last_commit_info

# Состояние пользователя
user_state = {}

def create_bot():
    """Создать и настроить бота"""
    if not TELEGRAM_BOT_TOKEN:
        return None
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
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
    elif data == "cfa_module_mode":
        user_state[user_id] = {"mode": "module"}
        await show_books_menu(query, "module")

    elif data == "cfa_single_mode":
        await query.edit_message_text(
            "📄 *Единичный режим*\n\n"
            "Функция в разработке.\n\n"
            "Пока используйте Модульный режим.",
            parse_mode="Markdown"
        )

    elif data == "cfa_merge_module":
        await show_merge_module_menu(query)

    elif data == "back_cfa":
        await show_cfa_menu(query)
    
    # === ВЫБОР КНИГИ ===
    elif data.startswith("book_"):
        book_code = data.replace("book_", "")
        user_state[user_id]["book"] = book_code
        await show_modules_menu(query, book_code)
    
    elif data == "back_books":
        mode = user_state.get(user_id, {}).get("mode", "module")
        await show_books_menu(query, mode)
    
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
        mode = user_state.get(user_id, {}).get("mode", "module")
        if mode == "module":
            await execute_module_task(query, user_id)
        else:
            await execute_task(query, user_id)

    elif data == "confirm_no":
        book_code = user_state.get(user_id, {}).get("book", "quants")
        await show_modules_menu(query, book_code)

    # === MERGE ===
    elif data.startswith("merge_"):
        task_id_short = data.replace("merge_", "")
        await perform_merge(query, task_id_short)

    # === REFRESH STATUS ===
    elif data == "refresh_status":
        await refresh_and_show_status(query)

    # === CLEAR ALL TASKS ===
    elif data == "clear_all_tasks":
        await clear_all_tasks(query)

    # === DO MERGE MODULE ===
    elif data.startswith("do_merge_"):
        module_key = data.replace("do_merge_", "")
        await execute_merge_module(query, module_key)


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
            InlineKeyboardButton("📝 Модульный режим", callback_data="cfa_module_mode"),
        ],
        [
            InlineKeyboardButton("🔀 Merge модуль", callback_data="cfa_merge_module"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="back_main"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📊 *CFA Level 1*\n\nВыберите действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def show_books_menu(query, mode):
    """Меню выбора книги"""
    if mode == "module":
        type_emoji = "📦"
        type_name = "Модульный режим"
    else:
        type_emoji = "📄"
        type_name = mode.capitalize()

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
    mode = state.get("mode", "module")
    book_code = state.get("book", "quants")
    module_num = state.get("module", 1)

    book = BOOKS.get(book_code, {})
    book_name = book.get("name", book_code)

    keyboard = [
        [
            InlineKeyboardButton("✅ Запустить", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Отмена", callback_data="confirm_no"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if mode == "module":
        message = (
            f"⚡ *Подтверждение*\n\n"
            f"📦 Режим: Модульный\n"
            f"📚 Книга: {book_name}\n"
            f"📖 Модуль: {module_num}\n\n"
            f"Будет запущено:\n"
            f"• Glossary для Module {module_num}\n"
            f"• Tests для Module {module_num}\n\n"
            f"Запустить модуль?"
        )
    else:
        message = (
            f"⚡ *Подтверждение*\n\n"
            f"📄 Режим: Единичный\n"
            f"📚 Книга: {book_name}\n"
            f"📖 Модуль: {module_num}\n\n"
            f"Запустить задачу?"
        )

    await query.edit_message_text(
        message,
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

    # Создаем задачу в системе мониторинга
    task_id = task_storage.create_task(content_type, book_name, module_num)

    # Отправить промпт в Claude Code через PyAutoGUI
    send_prompt_to_claude(prompt)

    type_name = "Тесты" if content_type == "tests" else "Глоссарий"

    # Создаем кнопку возврата в главное меню
    keyboard = [[InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🚀 *Задача запущена!*\n\n"
        f"📝 {type_name} для {book_name} Module {module_num}\n"
        f"⏱️ Примерное время: 20-40 мин\n\n"
        f"Промпт отправлен в Claude Code\n"
        f"Мониторинг GitHub запущен...\n\n"
        f"Task ID: `{task_id[:8]}`\n\n"
        f"_Я сообщу когда будет готово!_",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def execute_module_task(query, user_id):
    """Запуск модуля в модульном режиме (glossary + tests)"""
    state = user_state.get(user_id, {})
    book_code = state.get("book", "quants")
    module_num = state.get("module", 1)

    book = BOOKS.get(book_code, {})
    book_name = book.get("name", book_code)

    # Генерируем промпты для обеих задач
    glossary_prompt = generate_prompt("glossary", book_name, module_num)
    tests_prompt = generate_prompt("tests", book_name, module_num)

    # Создаем парные задачи в системе мониторинга
    module_tasks = task_storage.create_module_tasks(book_name, module_num)

    # Отправить оба промпта в Claude Code через PyAutoGUI
    launch_module_tasks(glossary_prompt, tests_prompt)

    # Создаем кнопку возврата в главное меню
    keyboard = [[InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🚀 *Модуль запущен!*\n\n"
        f"📦 Модульный режим\n"
        f"📚 Книга: {book_name}\n"
        f"📖 Модуль: {module_num}\n\n"
        f"Запущены задачи:\n"
        f"• 📖 Glossary\n"
        f"• 📝 Tests\n\n"
        f"⏱️ Примерное время: 40-80 мин\n\n"
        f"Промпты отправлены в Claude Code\n"
        f"Мониторинг GitHub запущен...\n\n"
        f"Module ID: `{module_tasks['module_id'][:8]}`\n"
        f"Glossary ID: `{module_tasks['glossary_id'][:8]}`\n"
        f"Tests ID: `{module_tasks['tests_id'][:8]}`\n\n"
        f"_Я сообщу когда будет готово!_",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def refresh_and_show_status(query):
    """Обновить статус — синхронизировать с GitHub"""
    from modules.github_monitor import get_claude_branches, check_branch_completed
    from datetime import datetime

    try:
        github_branches = get_claude_branches()
        print(f"[Refresh] Found {len(github_branches)} GitHub branches")
    except Exception as e:
        print(f"[Refresh] GitHub error: {e}")
        github_branches = []

    active_tasks = task_storage.get_active_tasks()

    removed_count = 0
    completed_count = 0
    linked_count = 0

    for task in active_tasks[:]:
        branch = task.get("branch")

        # === НОВОЕ: Привязка веток к задачам без ветки ===
        if not branch and github_branches:
            # Ищем подходящую ветку по паттерну
            book_lower = task["book"].lower()
            task_type = task["type"]  # "glossary" или "tests"
            module = str(task["module"])

            for gb in github_branches:
                gb_lower = gb.lower()

                # Проверяем что ветка соответствует задаче
                book_match = any(word in gb_lower for word in book_lower.split()[:1])  # первое слово книги
                module_match = f"module-{module}" in gb_lower or f"module{module}" in gb_lower or f"-{module}-" in gb_lower or gb_lower.endswith(f"-{module}")

                if task_type == "glossary":
                    type_match = "glossary" in gb_lower
                else:
                    type_match = "test" in gb_lower or "qbank" in gb_lower

                if book_match and module_match and type_match:
                    task_storage.update_task_branch(task["task_id"], gb)
                    branch = gb
                    linked_count += 1
                    print(f"[Refresh] Linked task {task['task_id'][:8]} to branch {gb}")
                    break

        # Проверка: если ветка есть, но её нет в GitHub — удаляем задачу
        if branch and github_branches and branch not in github_branches:
            task_storage.remove_task(task["task_id"])
            removed_count += 1
            print(f"[Refresh] Removed task {task['task_id'][:8]} (branch {branch} deleted)")
            continue

        # Проверка завершения
        if branch and task.get("status") != "ready_to_merge":
            try:
                if check_branch_completed(branch):
                    task_storage.mark_task_completed(task["task_id"])
                    completed_count += 1
                    print(f"[Refresh] Task {task['task_id'][:8]} marked as completed")
            except Exception as e:
                print(f"[Refresh] Error checking {branch}: {e}")

    # Формируем ответ
    messages = []
    if linked_count > 0:
        messages.append(f"🔗 Привязано: {linked_count}")
    if completed_count > 0:
        messages.append(f"✅ Завершено: {completed_count}")
    if removed_count > 0:
        messages.append(f"🗑 Удалено: {removed_count}")
    if not messages:
        messages.append("✅ Всё актуально")

    await query.answer(" | ".join(messages), show_alert=True)
    await show_status(query)


async def show_status(query):
    """Показать статус с индикаторами активности"""
    from datetime import datetime

    active_tasks = task_storage.get_active_tasks()
    ready_to_merge = task_storage.get_ready_to_merge_tasks()
    completed_today = task_storage.get_completed_tasks_today()

    message = "📊 *Статус системы*\n\n"
    message += "🟢 Бот работает\n"

    if active_tasks:
        message += f"🟢 Мониторинг: активен ({len(active_tasks)} задач)\n"
    else:
        message += "🟡 Мониторинг: нет активных задач\n"

    message += "━━━━━━━━━━━━━━━\n"

    # Активные задачи с индикаторами
    if active_tasks:
        message += "📋 *Активные задачи:*\n\n"

        for task in active_tasks:
            started = datetime.strptime(task["started_at"], "%Y-%m-%d %H:%M:%S")
            started_time = task["started_at"].split()[1][:5]
            minutes_since_start = (datetime.now() - started).total_seconds() / 60

            branch = task.get("branch")
            last_commit = None

            if branch:
                last_commit = get_last_commit_info(branch)

            # Определяем статус
            if task.get("status") == "ready_to_merge":
                status_icon = "✅"
                status_text = "Готов к merge"
            elif not branch:
                # Нет ветки
                if minutes_since_start < 5:
                    status_icon = "🕐"
                    status_text = "Ожидает создания ветки"
                else:
                    status_icon = "❓"
                    status_text = "Ветка не найдена"
            elif last_commit:
                # Есть ветка и информация о коммите
                mins_ago = last_commit["minutes_ago"]

                if mins_ago < 5:
                    status_icon = "🟢"
                    status_text = f"Работает (коммит {mins_ago} мин назад)"
                elif mins_ago < 15:
                    status_icon = "🔵"
                    status_text = f"В процессе (коммит {mins_ago} мин назад)"
                else:
                    status_icon = "⚠️"
                    status_text = f"Нет активности {mins_ago} мин"
            else:
                # Есть ветка, но не удалось получить коммит
                status_icon = "🔵"
                status_text = "Проверяю..."

            type_emoji = "📖" if task["type"] == "glossary" else "📝"
            type_name = "Глоссарий" if task["type"] == "glossary" else "Тесты"

            message += f"{status_icon} {type_emoji} *{type_name}* {task['book']} Module {task['module']}\n"
            message += f"⏱ Начато: {started_time} | {status_text}\n"

            # Показываем ветку если есть
            if branch:
                branch_short = branch.replace("claude/", "")[:30]
                message += f"🌿 `{branch_short}`\n"

            # Показываем последний коммит если есть
            if last_commit and task.get("status") != "ready_to_merge":
                commit_msg = last_commit["message"].split("\n")[0][:40]  # первая строка, до 40 символов
                message += f"💬 _{commit_msg}_\n"

            message += "\n"

        message += "━━━━━━━━━━━━━━━\n"
    else:
        message += "📋 *Активные задачи:* нет\n"
        message += "━━━━━━━━━━━━━━━\n"

    # Готовы к мержу
    message += f"✅ *Готовы к мёржу:* {len(ready_to_merge)}\n"

    # Проверяем готовые модули
    modules_ready = {}
    for task in ready_to_merge:
        key = f"{task['book']}_{task['module']}"
        if key not in modules_ready:
            modules_ready[key] = []
        modules_ready[key].append(task["type"])

    for key, types in modules_ready.items():
        if len(types) == 2:  # glossary + tests
            book, module = key.rsplit("_", 1)
            message += f"🎉 _{book} Module {module} — полностью готов!_\n"

    message += "━━━━━━━━━━━━━━━\n"
    message += f"📁 *Завершено сегодня:* {len(completed_today)}"

    # Кнопки
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_status")],
        [InlineKeyboardButton("🗑 Очистить всё", callback_data="clear_all_tasks")],
        [InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")


async def clear_all_tasks(query):
    """Очистить все задачи"""
    task_storage.clear_all_tasks()
    await query.answer("🗑 Все задачи очищены!", show_alert=True)
    await show_status(query)


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


async def perform_merge(query, task_id_short):
    """Выполнить merge для конкретной задачи"""
    # Найти задачу по короткому ID
    active_tasks = task_storage.get_active_tasks()
    task = None

    for t in active_tasks:
        if t["task_id"].startswith(task_id_short):
            task = t
            break

    if not task:
        await query.edit_message_text(
            "❌ *Ошибка*\n\n"
            "Задача не найдена.",
            parse_mode="Markdown"
        )
        return

    task_type = task["type"]
    book = task["book"]
    module = task["module"]

    # TODO: Здесь должна быть логика git merge через git_operations
    # Пока просто закрываем вкладку и завершаем задачу

    # Закрыть вкладку в зависимости от типа
    if task_type == "glossary":
        close_glossary_tab()
        type_emoji = "📖"
        type_name = "Glossary"
    else:  # tests
        close_tests_tab()
        type_emoji = "📝"
        type_name = "Tests"

    # Завершить задачу
    task_storage.complete_task(task["task_id"])

    # Создаем кнопку возврата
    keyboard = [[InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ *Merge завершен!*\n\n"
        f"{type_emoji} {type_name} - {book} Module {module}\n\n"
        f"Вкладка закрыта\n"
        f"Задача перемещена в завершенные\n\n"
        f"_Можете запустить следующую задачу_",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def show_merge_module_menu(query):
    """Показать модули готовые к merge"""
    ready_tasks = task_storage.get_ready_to_merge_tasks()

    if not ready_tasks:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="project_cfa")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔀 *Merge модуль*\n\n"
            "Нет задач готовых к merge.\n\n"
            "_Дождись завершения glossary и tests для модуля._",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    # Группируем по модулям
    modules = {}
    for task in ready_tasks:
        key = f"{task['book']}_{task['module']}"
        if key not in modules:
            modules[key] = {"book": task["book"], "module": task["module"], "tasks": []}
        modules[key]["tasks"].append(task)

    # Показываем только модули где готовы ОБА (glossary + tests)
    complete_modules = {k: v for k, v in modules.items() if len(v["tasks"]) == 2}

    if not complete_modules:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="project_cfa")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔀 *Merge модуль*\n\n"
            "Нет полностью готовых модулей.\n\n"
            "_Нужны ОБА: glossary ✅ и tests ✅_",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    # Создаём кнопки для каждого готового модуля
    keyboard = []
    for key, data in complete_modules.items():
        keyboard.append([InlineKeyboardButton(
            f"🔀 {data['book']} Module {data['module']}",
            callback_data=f"do_merge_{key}"
        )])

    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="project_cfa")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = "🔀 *Merge модуль*\n\n"
    message += "Готовы к merge:\n\n"
    for key, data in complete_modules.items():
        message += f"📚 *{data['book']} Module {data['module']}*\n"
        for task in data["tasks"]:
            type_emoji = "📖" if task["type"] == "glossary" else "📝"
            message += f"  {type_emoji} {task['type']} ✅\n"
        message += "\n"

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")


async def execute_merge_module(query, module_key):
    """Выполнить merge модуля"""
    from modules.git_operations import merge_module_branches

    # Парсим ключ
    parts = module_key.rsplit("_", 1)
    book = parts[0]
    module = int(parts[1])

    # Находим задачи для этого модуля
    ready_tasks = task_storage.get_ready_to_merge_tasks()
    module_tasks = [t for t in ready_tasks if t["book"] == book and t["module"] == module]

    if len(module_tasks) != 2:
        await query.edit_message_text(
            f"❌ Ошибка: нужны обе задачи (glossary + tests) для merge",
            parse_mode="Markdown"
        )
        return

    # Находим ветки
    glossary_branch = None
    tests_branch = None

    for task in module_tasks:
        if task["type"] == "glossary":
            glossary_branch = task.get("branch")
        else:
            tests_branch = task.get("branch")

    if not glossary_branch or not tests_branch:
        await query.edit_message_text(
            f"❌ Ошибка: не найдены ветки для merge\n\n"
            f"Glossary branch: {glossary_branch}\n"
            f"Tests branch: {tests_branch}",
            parse_mode="Markdown"
        )
        return

    # Показываем процесс
    await query.edit_message_text(
        f"🔄 *Выполняю merge...*\n\n"
        f"📚 {book} Module {module}\n\n"
        f"📖 Glossary: `{glossary_branch}`\n"
        f"📝 Tests: `{tests_branch}`",
        parse_mode="Markdown"
    )

    # Выполняем merge
    result = merge_module_branches(glossary_branch, tests_branch)

    # Создаем кнопку возврата
    keyboard = [[InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if result["success"]:
        # Удаляем задачи из storage
        for task in module_tasks:
            task_storage.complete_task(task["task_id"])

        await query.edit_message_text(
            f"✅ *Merge выполнен!*\n\n"
            f"📚 {book} Module {module}\n\n"
            f"{result['message']}\n\n"
            f"_Модуль смёржен в main и ветки удалены._",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"❌ *Merge не удался*\n\n"
            f"📚 {book} Module {module}\n\n"
            f"Ошибка: {result['message']}\n\n"
            f"_Попробуй смёржить вручную._",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def do_merge(query):
    """Выполнить merge"""
    # Получаем активные задачи
    active_tasks = task_storage.get_active_tasks()

    if not active_tasks:
        await query.edit_message_text(
            "🔀 *Merge*\n\n"
            "Нет активных задач для merge.\n\n"
            "Запустите задачу через CFA меню.",
            parse_mode="Markdown"
        )
        return

    # Создаем кнопки для каждой задачи
    keyboard = []
    for task in active_tasks:
        task_type = task["type"]
        type_emoji = "📝" if task_type == "tests" else "📖"
        type_name = "Tests" if task_type == "tests" else "Glossary"

        button_text = f"{type_emoji} {type_name} - {task['book']} M{task['module']}"
        callback_data = f"merge_{task['task_id'][:8]}"

        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_cfa")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🔀 *Merge*\n\n"
        "Выберите задачу для merge:\n\n"
        "_После merge вкладка будет автоматически закрыта_",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )