import asyncio
from datetime import datetime
from modules import task_storage
from modules import github_monitor

# Кэш для уведомлений (чтобы не дублировать)
_notified_tasks = set()

async def background_monitor_loop(bot, admin_id):
    """
    Фоновый мониторинг активных задач

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

                # Если есть ветка — проверяем завершение
                if branch:
                    try:
                        if github_monitor.check_branch_completed(branch):
                            # Помечаем как готовую
                            task_storage.mark_task_completed(task_id)

                            # Отправляем уведомление
                            if task_id not in _notified_tasks:
                                await send_completion_notification(bot, admin_id, task)
                                _notified_tasks.add(task_id)

                                # Проверяем, готов ли весь модуль
                                if task_storage.is_module_ready(task["book"], task["module"]):
                                    await send_module_ready_notification(bot, admin_id, task)

                    except Exception as e:
                        print(f"[BackgroundMonitor] Error checking task {task_id}: {e}")

                # Проверка на отсутствие активности
                started = datetime.strptime(task["started_at"], "%Y-%m-%d %H:%M:%S")
                minutes_passed = (datetime.now() - started).total_seconds() / 60

                if minutes_passed > 20 and len(task.get("checkpoints", [])) == 0:
                    # Нет активности > 20 минут
                    if f"{task_id}_inactive" not in _notified_tasks:
                        await send_inactive_warning(bot, admin_id, task, int(minutes_passed))
                        _notified_tasks.add(f"{task_id}_inactive")

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
        print(f"[BackgroundMonitor] Sent module ready notification for {task['book']} M{task['module']}")
    except Exception as e:
        print(f"[BackgroundMonitor] Failed to send notification: {e}")

async def send_inactive_warning(bot, admin_id, task, minutes):
    """Отправить предупреждение об отсутствии активности"""
    type_emoji = "📖" if task["type"] == "glossary" else "📝"
    type_name = "Глоссарий" if task["type"] == "glossary" else "Тесты"

    message = (
        f"⚠️ *Нет активности*\n\n"
        f"{type_emoji} {type_name}\n"
        f"📚 {task['book']} Module {task['module']}\n\n"
        f"Прошло {minutes} минут без активности.\n"
        f"Возможно задача зависла?"
    )

    try:
        await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
        print(f"[BackgroundMonitor] Sent inactive warning for {task['task_id']}")
    except Exception as e:
        print(f"[BackgroundMonitor] Failed to send notification: {e}")
