import asyncio
from datetime import datetime
from modules import task_storage
from modules import github_monitor

# Кэш для уведомлений (чтобы не дублировать)
_notified_tasks = set()
_known_branches = set()  # Кэш известных веток
_last_commit_sha = {}  # Кэш последних коммитов для отслеживания checkpoint'ов

async def background_monitor_loop(bot, admin_id):
    """
    Фоновый мониторинг активных задач и новых веток
    Проверка каждые 2 минуты

    Args:
        bot: экземпляр Telegram Bot
        admin_id: Telegram ID администратора для уведомлений
    """
    print("[BackgroundMonitor] Started background monitoring (check every 10 seconds)")

    while True:
        try:
            await asyncio.sleep(10)  # Проверка каждые 10 секунд

            # Получаем все ветки Claude с GitHub
            try:
                all_branches = github_monitor.get_claude_branches()
                print(f"[BackgroundMonitor] Found {len(all_branches)} Claude branches on GitHub")
            except Exception as e:
                print(f"[BackgroundMonitor] Error getting branches: {e}")
                all_branches = []

            # Проверяем новые ветки
            await check_new_branches(bot, admin_id, all_branches)

            # Проверяем активные задачи
            active_tasks = task_storage.get_active_tasks()

            if not active_tasks:
                print("[BackgroundMonitor] No active tasks to monitor")
                continue

            print(f"[BackgroundMonitor] Checking {len(active_tasks)} active tasks...")

            for task in active_tasks:
                task_id = task["task_id"]
                branch = task.get("branch")

                # Пропускаем уже завершённые
                if task.get("status") == "ready_to_merge":
                    continue

                # Если нет ветки — пытаемся найти
                if not branch and all_branches:
                    found_branch = github_monitor.find_branch_for_task(
                        task["type"],
                        task["book"],
                        task["module"],
                        all_branches
                    )
                    if found_branch:
                        task_storage.update_task_branch(task_id, found_branch)
                        branch = found_branch
                        task["branch"] = found_branch  # Обновляем локальный объект
                        task["branch_linked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Обновляем локальный объект
                        await send_branch_linked_notification(bot, admin_id, task, branch)

                # Если ветки всё еще нет — пропускаем
                if not branch:
                    continue

                try:
                    # Проверяем новые коммиты и checkpoint'ы
                    await check_branch_updates(bot, admin_id, task, branch)

                    # Проверяем завершение
                    if github_monitor.check_branch_completed(branch):
                        task_storage.mark_task_completed(task_id)

                        # Отправляем уведомление о завершении
                        completion_key = f"{task_id}_completed"
                        if completion_key not in _notified_tasks:
                            await send_completion_notification(bot, admin_id, task)
                            _notified_tasks.add(completion_key)

                            # Проверяем, готов ли весь модуль
                            if task_storage.is_module_ready(task["book"], task["module"]):
                                await send_module_ready_notification(bot, admin_id, task)
                        continue

                    # Проверяем активность
                    last_commit = github_monitor.get_last_commit_info(branch)

                    if last_commit:
                        # Сначала проверяем — сколько времени прошло с привязки ветки
                        branch_linked_at = task.get("branch_linked_at")

                        if branch_linked_at:
                            from datetime import datetime
                            linked_time = datetime.strptime(branch_linked_at, "%Y-%m-%d %H:%M:%S")
                            mins_since_linked = int((datetime.now() - linked_time).total_seconds() / 60)

                            # Если ветка привязана менее 20 минут назад — не считаем зависшей
                            if mins_since_linked < 20:
                                continue

                        mins_ago = last_commit["minutes_ago"]

                        # Если > 15 минут без коммитов — предупреждаем (один раз)
                        if mins_ago > 15:
                            inactive_key = f"{task_id}_inactive"
                            if inactive_key not in _notified_tasks:
                                await send_inactive_warning(bot, admin_id, task, mins_ago)
                                _notified_tasks.add(inactive_key)

                except Exception as e:
                    print(f"[BackgroundMonitor] Error checking task {task_id}: {e}")

        except Exception as e:
            print(f"[BackgroundMonitor] Loop error: {e}")
            await asyncio.sleep(120)


def is_content_branch(branch_name):
    """
    Проверить что это ветка для контента, а не служебная

    Уведомляем ТОЛЬКО о:
    - claude/add-*-module-*-glossary-*
    - claude/add-*-module-*-tests-*
    - claude/add-*-module-*-qbank-*

    НЕ уведомляем о:
    - claude/fix-*
    - claude/update-*
    - claude/refactor-*
    - claude/merge-*
    """
    branch_lower = branch_name.lower()
    content_patterns = ['-glossary-', '-tests-', '-qbank-']
    return any(pattern in branch_lower for pattern in content_patterns)


async def check_new_branches(bot, admin_id, all_branches):
    """
    Проверить новые ветки и отправить уведомления
    """
    global _known_branches

    # Инициализация при первом запуске
    if not _known_branches:
        _known_branches = set(all_branches)
        return

    # Находим новые ветки
    new_branches = set(all_branches) - _known_branches

    for branch in new_branches:
        print(f"[BackgroundMonitor] New branch detected: {branch}")

        # Уведомляем только о контентных ветках
        if is_content_branch(branch):
            await send_new_branch_notification(bot, admin_id, branch)
        else:
            print(f"[BackgroundMonitor] Skipping notification for service branch: {branch}")

    # Обновляем кэш
    _known_branches = set(all_branches)


async def check_branch_updates(bot, admin_id, task, branch):
    """
    Проверить обновления в ветке (новые коммиты, checkpoint'ы)
    """
    global _last_commit_sha

    try:
        commits = github_monitor.get_branch_commits(branch)
        if not commits:
            return

        last_commit = commits[0]
        last_sha = last_commit["sha"]
        task_id = task["task_id"]

        # Если это первая проверка для этой ветки
        if branch not in _last_commit_sha:
            _last_commit_sha[branch] = last_sha
            return

        # Если коммит изменился — проверяем на checkpoint
        if _last_commit_sha[branch] != last_sha:
            print(f"[BackgroundMonitor] New commit in {branch}: {last_commit['message'][:50]}")

            # Проверяем на checkpoint
            event = github_monitor.parse_commit_message(last_commit["message"])
            if event and event["type"] == "checkpoint":
                checkpoint_key = f"{task_id}_{event['checkpoint_name']}"
                if checkpoint_key not in _notified_tasks:
                    await send_checkpoint_notification(bot, admin_id, task, event)
                    _notified_tasks.add(checkpoint_key)

            # Обновляем кэш
            _last_commit_sha[branch] = last_sha

    except Exception as e:
        print(f"[BackgroundMonitor] Error checking branch updates: {e}")


async def send_completion_notification(bot, admin_id, task):
    """Отправить уведомление о завершении задачи"""
    type_emoji = "📖" if task["type"] == "glossary" else "📝"
    type_name = "Глоссарий" if task["type"] == "glossary" else "Тесты"

    message = (
        f"✅ *Задача завершена!*\n\n"
        f"{type_emoji} {type_name}\n"
        f"📚 {task['book']} Module {task['module']}\n\n"
        f"Готово к merge!"
    )

    try:
        await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
        print(f"[BackgroundMonitor] Sent completion notification for {task['task_id']}")
    except Exception as e:
        print(f"[BackgroundMonitor] Failed to send notification: {e}")


async def send_module_ready_notification(bot, admin_id, task):
    """Отправить уведомление о готовности всего модуля"""
    message = (
        f"🎉 *Модуль полностью готов!*\n\n"
        f"📚 {task['book']} Module {task['module']}\n\n"
        f"✅ Glossary готов\n"
        f"✅ Tests готовы\n\n"
        f"Можно делать merge!"
    )

    try:
        await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
        print(f"[BackgroundMonitor] Sent module ready notification")
    except Exception as e:
        print(f"[BackgroundMonitor] Failed to send notification: {e}")


async def send_inactive_warning(bot, admin_id, task, minutes):
    """Отправить предупреждение об отсутствии активности"""
    type_emoji = "📖" if task["type"] == "glossary" else "📝"
    type_name = "Глоссарий" if task["type"] == "glossary" else "Тесты"

    message = (
        f"⚠️ *Возможно зависла*\n\n"
        f"{type_emoji} {type_name}\n"
        f"📚 {task['book']} Module {task['module']}\n\n"
        f"Последний коммит: {minutes} мин назад\n"
        f"Проверь вкладку Claude Code"
    )

    try:
        await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
        print(f"[BackgroundMonitor] Sent inactive warning for {task['task_id']}")
    except Exception as e:
        print(f"[BackgroundMonitor] Failed to send notification: {e}")


async def send_new_branch_notification(bot, admin_id, branch):
    """Отправить уведомление о новой ветке"""
    branch_short = branch.replace("claude/", "")

    message = (
        f"🌿 *Новая ветка создана!*\n\n"
        f"📋 `{branch_short}`\n\n"
        f"Claude Code начал работу"
    )

    try:
        await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
        print(f"[BackgroundMonitor] Sent new branch notification: {branch}")
    except Exception as e:
        print(f"[BackgroundMonitor] Failed to send notification: {e}")


async def send_branch_linked_notification(bot, admin_id, task, branch):
    """Отправить уведомление о привязке ветки к задаче"""
    type_emoji = "📖" if task["type"] == "glossary" else "📝"
    type_name = "Глоссарий" if task["type"] == "glossary" else "Тесты"
    branch_short = branch.replace("claude/", "")

    message = (
        f"🔗 *Ветка привязана к задаче!*\n\n"
        f"{type_emoji} {type_name}\n"
        f"📚 {task['book']} Module {task['module']}\n"
        f"🌿 `{branch_short}`"
    )

    try:
        await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
        print(f"[BackgroundMonitor] Sent branch linked notification for {task['task_id']}")
    except Exception as e:
        print(f"[BackgroundMonitor] Failed to send notification: {e}")


async def send_checkpoint_notification(bot, admin_id, task, event):
    """Отправить уведомление о достижении checkpoint'а"""
    type_emoji = "📖" if task["type"] == "glossary" else "📝"
    type_name = "Глоссарий" if task["type"] == "glossary" else "Тесты"
    checkpoint_name = event.get("checkpoint_name", "Unknown")

    message = (
        f"🎯 *Checkpoint достигнут!*\n\n"
        f"{type_emoji} {type_name}\n"
        f"📚 {task['book']} Module {task['module']}\n"
        f"✅ {checkpoint_name.title()}\n\n"
        f"Работа продолжается..."
    )

    try:
        await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
        print(f"[BackgroundMonitor] Sent checkpoint notification: {checkpoint_name}")
    except Exception as e:
        print(f"[BackgroundMonitor] Failed to send notification: {e}")
