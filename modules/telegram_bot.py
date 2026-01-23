from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID
from projects.cfa.config import BOOKS
from projects.cfa.prompts import generate_prompt
from modules.pyautogui_actions import send_prompt_to_claude, launch_module_tasks, close_glossary_tab, close_tests_tab
from modules import task_storage
from modules.github_monitor import get_last_commit_info

# Состояние пользователя
user_state = {}

# Состояния навигации
STATE_MAIN = "main"
STATE_CFA = "cfa"
STATE_CFA_BOOKS = "cfa_books"
STATE_CFA_MODULES = "cfa_modules"
STATE_CFA_CONFIRM = "cfa_confirm"
STATE_STATUS = "status"
STATE_MERGE = "merge"
STATE_CLEAR = "clear"


def ensure_user_state(user_id):
    """Убедиться что user_state существует для пользователя"""
    if user_id not in user_state:
        user_state[user_id] = {}
    return user_state[user_id]


def create_bot():
    """Создать и настроить бота"""
    if not TELEGRAM_BOT_TOKEN:
        return None

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    return app


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    user_id = update.message.from_user.id
    user_state[user_id] = {"state": STATE_MAIN}

    keyboard = [
        [KeyboardButton("📊 CFA"), KeyboardButton("🇪🇸 Spanish")],
        [KeyboardButton("📈 Статус"), KeyboardButton("⏸️ Пауза")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🤖 Выберите проект:",
        reply_markup=reply_markup
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от ReplyKeyboard"""
    text = update.message.text
    user_id = update.message.from_user.id

    # Получаем текущее состояние пользователя
    state_data = user_state.get(user_id, {})
    current_state = state_data.get("state", STATE_MAIN)

    # === ГЛАВНОЕ МЕНЮ ===
    if current_state == STATE_MAIN:
        if text == "📊 CFA":
            await show_cfa_menu(update, user_id)
        elif text == "🇪🇸 Spanish":
            await update.message.reply_text("🇪🇸 Spanish - в разработке!")
        elif text == "📈 Статус":
            await show_status(update, user_id)
        elif text == "⏸️ Пауза":
            await update.message.reply_text("⏸️ Пауза активирована")

    # === CFA МЕНЮ ===
    elif current_state == STATE_CFA:
        if text == "📝 Модульный режим":
            user_state[user_id]["mode"] = "module"
            await show_books_menu(update, user_id)
        elif text == "🔀 Merge модуль":
            await show_merge_module_menu(update, user_id)
        elif text == "◀️ Назад":
            await show_main_menu(update, user_id)

    # === ВЫБОР КНИГИ ===
    elif current_state == STATE_CFA_BOOKS:
        if text == "◀️ Назад":
            await show_cfa_menu(update, user_id)
        else:
            # Проверяем какая книга выбрана
            book_map = {
                "QM": "quants",
                "ECON": "econ",
                "FSA": "fsa",
                "CF": "cf",
                "EI": "equity",
                "FI": "fi",
                "DER": "der",
                "ALT": "alt",
                "PM": "pm",
                "ETH": "ethics"
            }
            book_code = book_map.get(text)
            if book_code:
                user_state[user_id]["book"] = book_code
                await show_modules_menu(update, user_id, book_code)

    # === ВЫБОР МОДУЛЯ ===
    elif current_state == STATE_CFA_MODULES:
        if text == "◀️ Назад":
            await show_books_menu(update, user_id)
        else:
            # Проверяем что это число
            try:
                module_num = int(text)
                user_state[user_id]["module"] = module_num
                await show_confirmation(update, user_id)
            except ValueError:
                pass

    # === ПОДТВЕРЖДЕНИЕ ===
    elif current_state == STATE_CFA_CONFIRM:
        if text == "✅ Запустить":
            await execute_module_task(update, user_id)
        elif text == "❌ Отмена":
            book_code = user_state[user_id].get("book", "quants")
            await show_modules_menu(update, user_id, book_code)

    # === СТАТУС ===
    elif current_state == STATE_STATUS:
        if text == "🔄 Обновить":
            await refresh_and_show_status(update, user_id)
        elif text == "🗑 Очистить":
            await clear_tasks_menu(update, user_id)
        elif text == "◀️ Назад":
            await show_main_menu(update, user_id)

    # === MERGE ===
    elif current_state == STATE_MERGE:
        if text == "◀️ Назад":
            await show_cfa_menu(update, user_id)
        else:
            # Проверяем формат "Book Module N"
            await handle_merge_selection(update, user_id, text)

    # === ОЧИСТКА ===
    elif current_state == STATE_CLEAR:
        if text == "🧹 Очистить задачи":
            await clear_tasks_only(update, user_id)
        elif text == "💣 Очистить ВСЁ (ветки + задачи)":
            await clear_everything(update, user_id)
        elif text == "◀️ Назад":
            await show_status(update, user_id)


async def show_main_menu(update: Update, user_id: int):
    """Главное меню"""
    user_state[user_id] = {"state": STATE_MAIN}

    keyboard = [
        [KeyboardButton("📊 CFA"), KeyboardButton("🇪🇸 Spanish")],
        [KeyboardButton("📈 Статус"), KeyboardButton("⏸️ Пауза")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🤖 Выберите проект:",
        reply_markup=reply_markup
    )


async def show_cfa_menu(update: Update, user_id: int):
    """CFA меню"""
    ensure_user_state(user_id)
    user_state[user_id]["state"] = STATE_CFA

    keyboard = [
        [KeyboardButton("📝 Модульный режим")],
        [KeyboardButton("🔀 Merge модуль")],
        [KeyboardButton("◀️ Назад")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "📊 CFA - выберите действие:",
        reply_markup=reply_markup
    )


async def show_books_menu(update: Update, user_id: int):
    """Меню выбора книги"""
    ensure_user_state(user_id)
    user_state[user_id]["state"] = STATE_CFA_BOOKS

    keyboard = [
        [KeyboardButton("QM"), KeyboardButton("ECON"), KeyboardButton("FSA")],
        [KeyboardButton("CF"), KeyboardButton("EI"), KeyboardButton("FI")],
        [KeyboardButton("DER"), KeyboardButton("ALT"), KeyboardButton("PM")],
        [KeyboardButton("ETH")],
        [KeyboardButton("◀️ Назад")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "📚 Выберите книгу:",
        reply_markup=reply_markup
    )


async def show_modules_menu(update: Update, user_id: int, book_code: str):
    """Меню выбора модуля"""
    ensure_user_state(user_id)
    book = BOOKS.get(book_code, {})
    book_name = book.get("name", book_code)
    total_modules = book.get("modules", 10)

    user_state[user_id]["state"] = STATE_CFA_MODULES

    # Создаем кнопки для модулей (по 5 в ряд)
    keyboard = []
    row = []
    for i in range(1, total_modules + 1):
        row.append(KeyboardButton(str(i)))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([KeyboardButton("◀️ Назад")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"📖 {book_name} - выберите модуль:",
        reply_markup=reply_markup
    )


async def show_confirmation(update: Update, user_id: int):
    """Подтверждение запуска"""
    state = user_state.get(user_id, {})
    book_code = state.get("book", "quants")
    module_num = state.get("module", 1)

    book = BOOKS.get(book_code, {})
    book_name = book.get("name", book_code)

    user_state[user_id]["state"] = STATE_CFA_CONFIRM

    keyboard = [
        [KeyboardButton("✅ Запустить"), KeyboardButton("❌ Отмена")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"⚡ Запустить {book_name} Module {module_num}?",
        reply_markup=reply_markup
    )


async def execute_module_task(update: Update, user_id: int):
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

    # Возвращаемся в главное меню
    await show_main_menu(update, user_id)

    # Отправляем уведомление о запуске
    await update.message.reply_text(
        f"🚀 Задача запущена! {book_name} Module {module_num}"
    )


async def refresh_and_show_status(update: Update, user_id: int):
    """Обновить статус — синхронизировать с GitHub"""
    from modules.github_monitor import get_claude_branches, check_branch_completed, find_branch_for_task
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

        # === Привязка веток к задачам без ветки ===
        if not branch and github_branches:
            found_branch = find_branch_for_task(
                task["type"],
                task["book"],
                task["module"],
                github_branches
            )

            if found_branch:
                task_storage.update_task_branch(task["task_id"], found_branch)
                branch = found_branch
                linked_count += 1
                print(f"[Refresh] Linked task {task['task_id'][:8]} to branch {found_branch}")

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
    if messages:
        await update.message.reply_text(" | ".join(messages))

    await show_status(update, user_id)


async def show_status(update: Update, user_id: int):
    """Показать статус с индикаторами активности"""
    from datetime import datetime

    ensure_user_state(user_id)
    user_state[user_id]["state"] = STATE_STATUS

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
                print(f"[Status] Getting commit info for task {task['task_id'][:8]} branch: {branch}")
                last_commit = get_last_commit_info(branch)
                if last_commit:
                    print(f"[Status] Last commit was {last_commit['minutes_ago']} minutes ago")

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
        [KeyboardButton("🔄 Обновить"), KeyboardButton("🗑 Очистить")],
        [KeyboardButton("◀️ Назад")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")


async def clear_all_tasks(update: Update, user_id: int):
    """Очистить все задачи"""
    task_storage.clear_all_tasks()
    await update.message.reply_text("🗑 Все задачи очищены!")
    await show_status(update, user_id)


async def clear_tasks_menu(update: Update, user_id: int):
    """Меню очистки — выбор режима"""
    if user_id not in user_state:
        user_state[user_id] = {}
    user_state[user_id]["state"] = STATE_CLEAR

    keyboard = [
        [KeyboardButton("🧹 Очистить задачи")],
        [KeyboardButton("💣 Очистить ВСЁ (ветки + задачи)")],
        [KeyboardButton("◀️ Назад")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🗑 *Выберите режим очистки:*\n\n"
        "🧹 *Очистить задачи* — только tasks.json\n"
        "💣 *Очистить ВСЁ* — удалить ВСЕ ветки claude/* на GitHub + tasks.json",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def clear_tasks_only(update: Update, user_id: int):
    """Очистить только tasks.json"""
    task_storage.clear_all_tasks()
    await update.message.reply_text("🧹 Задачи очищены!")
    await show_status(update, user_id)


async def clear_everything(update: Update, user_id: int):
    """Очистить ВСЁ — ветки на GitHub + tasks.json"""
    from modules.git_operations import delete_all_claude_branches

    await update.message.reply_text("💣 Удаляю все ветки claude/* на GitHub...")

    result = delete_all_claude_branches()

    if result["deleted"]:
        deleted_list = "\n".join([f"• {b}" for b in result["deleted"]])
        await update.message.reply_text(f"✅ Удалено веток: {len(result['deleted'])}\n\n{deleted_list}")

    if result["errors"]:
        await update.message.reply_text(f"⚠️ Ошибки: {len(result['errors'])}")

    # Очистить tasks.json
    task_storage.clear_all_tasks()

    await update.message.reply_text("🧹 Задачи очищены!")
    await show_status(update, user_id)


async def show_merge_module_menu(update: Update, user_id: int):
    """Показать модули готовые к merge"""
    ensure_user_state(user_id)
    ready_tasks = task_storage.get_ready_to_merge_tasks()

    if not ready_tasks:
        await update.message.reply_text(
            "🔀 Нет задач готовых к merge.\n\n"
            "Дождись завершения glossary и tests для модуля."
        )
        await show_cfa_menu(update, user_id)
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
        await update.message.reply_text(
            "🔀 Нет полностью готовых модулей.\n\n"
            "Нужны ОБА: glossary ✅ и tests ✅"
        )
        await show_cfa_menu(update, user_id)
        return

    user_state[user_id]["state"] = STATE_MERGE
    user_state[user_id]["modules"] = complete_modules

    # Создаём кнопки для каждого готового модуля
    keyboard = []
    for key, data in complete_modules.items():
        keyboard.append([KeyboardButton(f"{data['book']} Module {data['module']}")])

    keyboard.append([KeyboardButton("◀️ Назад")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    message = "🔀 *Merge модуль*\n\n"
    message += "Готовы к merge:\n\n"
    for key, data in complete_modules.items():
        message += f"📚 *{data['book']} Module {data['module']}*\n"
        for task in data["tasks"]:
            type_emoji = "📖" if task["type"] == "glossary" else "📝"
            message += f"  {type_emoji} {task['type']} ✅\n"
        message += "\n"

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")


async def handle_merge_selection(update: Update, user_id: int, text: str):
    """Обработка выбора модуля для merge"""
    state = user_state.get(user_id, {})
    complete_modules = state.get("modules", {})

    # Ищем выбранный модуль
    for key, data in complete_modules.items():
        module_text = f"{data['book']} Module {data['module']}"
        if text == module_text:
            await execute_merge_module(update, user_id, key, data)
            return


async def execute_merge_module(update: Update, user_id: int, module_key: str, module_data: dict):
    """Выполнить merge модуля"""
    from modules.git_operations import merge_module_branches

    book = module_data["book"]
    module = module_data["module"]

    # Находим задачи для этого модуля
    ready_tasks = task_storage.get_ready_to_merge_tasks()
    module_tasks = [t for t in ready_tasks if t["book"] == book and t["module"] == module]

    if len(module_tasks) != 2:
        await update.message.reply_text(f"❌ Ошибка: нужны обе задачи (glossary + tests) для merge")
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
        await update.message.reply_text(
            f"❌ Ошибка: не найдены ветки для merge\n\n"
            f"Glossary branch: {glossary_branch}\n"
            f"Tests branch: {tests_branch}"
        )
        return

    # Показываем процесс
    await update.message.reply_text(f"🔄 Выполняю merge {book} Module {module}...")

    # Выполняем merge
    result = merge_module_branches(glossary_branch, tests_branch)

    # Возвращаемся в главное меню
    await show_main_menu(update, user_id)

    if result["success"]:
        # Удаляем задачи из storage
        for task in module_tasks:
            task_storage.complete_task(task["task_id"])

        await update.message.reply_text(
            f"✅ Merge выполнен!\n\n"
            f"📚 {book} Module {module}\n\n"
            f"Модуль смёржен в main и ветки удалены."
        )
    else:
        await update.message.reply_text(
            f"❌ Merge не удался\n\n"
            f"📚 {book} Module {module}\n\n"
            f"Ошибка: {result['message']}\n\n"
            f"Попробуй смёржить вручную."
        )
