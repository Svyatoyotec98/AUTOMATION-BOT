import asyncio
from datetime import datetime
from modules import task_storage
from modules import github_monitor

# Кэш для уведомлений (чтобы не дублировать)
_notified_tasks = set()

async def background_monitor_loop(bot, admin_id):
    """
    Фоновый мониторинг активных задач
    Проверка каждую минуту

    Args:
        bot: экземпляр Telegram Bot
        admin_id: Telegram ID администратора для уведомлений
    """
    print("[BackgroundMonitor] Started background monitoring")

    while True:
        try:
            await asyncio.sleep(60)  # Проверка каждую минуту

            active_tasks = task_storage.get_active_tasks()

            if not active_tasks:
                continue

            print(f"[BackgroundMonitor] Checking {len(active_tasks)} active tasks...")

            for task in active_tasks:
                task_id = task["task_id"]
                branch = task.get("branch")

                # Пропускаем уже завершённые
                if task.get("status") == "ready_to_merge":
                    continue

                # Если нет ветки — пропускаем (ещё создаётся)
                if not branch:
                    continue

                try:
                    # Проверяем завершение
                    if github_monitor.check_branch_completed(branch):
                        task_storage.mark_task_completed(task_id)

                        # Отправляем уведомление о завершении
                        if task_id not in _notified_tasks:
                            await send_completion_notification(bot, admin_id, task)
                            _notified_tasks.add(task_id)

                            # Проверяем, готов ли весь модуль
                            if task_storage.is_module_ready(task["book"], task["module"]):
                                await send_module_ready_notification(bot, admin_id, task)
                        continue

                    # Проверяем активность по последнему коммиту
                    last_commit = github_monitor.get_last_commit_info(branch)

                    if last_commit:
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
            await asyncio.sleep(60)


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
