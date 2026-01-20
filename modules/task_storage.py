import json
import uuid
from datetime import datetime
from pathlib import Path

TASKS_FILE = "data/tasks.json"

def _load_tasks():
    """Загрузить задачи из файла"""
    if not Path(TASKS_FILE).exists():
        return {"active_tasks": [], "completed_tasks": []}

    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"active_tasks": [], "completed_tasks": []}

def _save_tasks(data):
    """Сохранить задачи в файл"""
    Path(TASKS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_task(task_type, book, module, module_id=None):
    """
    Создать новую задачу

    Args:
        task_type: тип задачи (tests/glossary)
        book: название книги (ECON, QM, etc)
        module: номер модуля
        module_id: ID модуля для связывания задач (опционально)

    Returns:
        task_id: уникальный идентификатор задачи
    """
    data = _load_tasks()

    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "type": task_type,
        "book": book,
        "module": module,
        "module_id": module_id,
        "branch": None,
        "status": "in_progress",
        "checkpoints": [],
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": None
    }

    data["active_tasks"].append(task)
    _save_tasks(data)

    print(f"[TaskStorage] Created task {task_id}: {task_type} {book} Module {module}")
    return task_id

def update_task_status(task_id, status):
    """
    Обновить статус задачи

    Args:
        task_id: ID задачи
        status: новый статус (in_progress/completed)
    """
    data = _load_tasks()

    for task in data["active_tasks"]:
        if task["task_id"] == task_id:
            task["status"] = status
            _save_tasks(data)
            print(f"[TaskStorage] Updated task {task_id} status to {status}")
            return True

    return False

def update_task_branch(task_id, branch):
    """
    Обновить ветку задачи

    Args:
        task_id: ID задачи
        branch: название ветки GitHub
    """
    data = _load_tasks()

    for task in data["active_tasks"]:
        if task["task_id"] == task_id:
            task["branch"] = branch
            _save_tasks(data)
            print(f"[TaskStorage] Updated task {task_id} branch to {branch}")
            return True

    return False

def add_checkpoint(task_id, checkpoint_name):
    """
    Добавить контрольную точку к задаче

    Args:
        task_id: ID задачи
        checkpoint_name: название контрольной точки
    """
    data = _load_tasks()

    for task in data["active_tasks"]:
        if task["task_id"] == task_id:
            checkpoint = {
                "name": checkpoint_name,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            task["checkpoints"].append(checkpoint)
            _save_tasks(data)
            print(f"[TaskStorage] Added checkpoint '{checkpoint_name}' to task {task_id}")
            return True

    return False

def complete_task(task_id):
    """
    Завершить задачу (переместить в completed_tasks)

    Args:
        task_id: ID задачи
    """
    data = _load_tasks()

    for i, task in enumerate(data["active_tasks"]):
        if task["task_id"] == task_id:
            task["status"] = "completed"
            task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Переместить в completed_tasks
            completed_task = data["active_tasks"].pop(i)
            data["completed_tasks"].append(completed_task)

            _save_tasks(data)
            print(f"[TaskStorage] Completed task {task_id}")
            return True

    return False

def get_active_tasks():
    """
    Получить список активных задач

    Returns:
        list: список активных задач
    """
    data = _load_tasks()
    return data["active_tasks"]

def get_completed_tasks_today():
    """
    Получить задачи завершенные сегодня

    Returns:
        list: список задач завершенных сегодня
    """
    data = _load_tasks()
    today = datetime.now().strftime("%Y-%m-%d")

    today_tasks = [
        task for task in data["completed_tasks"]
        if task["completed_at"] and task["completed_at"].startswith(today)
    ]

    return today_tasks

def get_task_by_id(task_id):
    """
    Получить задачу по ID

    Args:
        task_id: ID задачи

    Returns:
        dict: задача или None
    """
    data = _load_tasks()

    for task in data["active_tasks"]:
        if task["task_id"] == task_id:
            return task

    for task in data["completed_tasks"]:
        if task["task_id"] == task_id:
            return task

    return None

def get_task_by_branch(branch):
    """
    Получить задачу по названию ветки

    Args:
        branch: название ветки GitHub

    Returns:
        dict: задача или None
    """
    data = _load_tasks()

    for task in data["active_tasks"]:
        if task["branch"] == branch:
            return task

    return None

def create_module_tasks(book, module):
    """
    Создать парные задачи для модульного режима (glossary + tests)

    Args:
        book: название книги (ECON, QM, etc)
        module: номер модуля

    Returns:
        dict: {"module_id": "...", "glossary_id": "...", "tests_id": "..."}
    """
    # Создать общий module_id для связывания задач
    module_id = str(uuid.uuid4())

    # Создать задачу glossary
    glossary_id = create_task("glossary", book, module, module_id=module_id)

    # Создать задачу tests
    tests_id = create_task("tests", book, module, module_id=module_id)

    print(f"[TaskStorage] Created module tasks for {book} Module {module}")
    print(f"[TaskStorage] Module ID: {module_id}")
    print(f"[TaskStorage] Glossary ID: {glossary_id}")
    print(f"[TaskStorage] Tests ID: {tests_id}")

    return {
        "module_id": module_id,
        "glossary_id": glossary_id,
        "tests_id": tests_id
    }

def get_tasks_by_module_id(module_id):
    """
    Получить все задачи модуля по module_id

    Args:
        module_id: ID модуля

    Returns:
        list: список задач модуля
    """
    data = _load_tasks()
    module_tasks = []

    for task in data["active_tasks"]:
        if task.get("module_id") == module_id:
            module_tasks.append(task)

    for task in data["completed_tasks"]:
        if task.get("module_id") == module_id:
            module_tasks.append(task)

    return module_tasks

def remove_task(task_id):
    """
    Удалить задачу по ID (если ветка была удалена вручную)

    Args:
        task_id: ID задачи
    """
    data = _load_tasks()
    data["active_tasks"] = [t for t in data["active_tasks"] if t["task_id"] != task_id]
    _save_tasks(data)
    print(f"[TaskStorage] Removed task {task_id}")

def mark_task_completed(task_id):
    """
    Пометить задачу как завершённую (готова к merge)

    Args:
        task_id: ID задачи

    Returns:
        bool: True если задача найдена и обновлена
    """
    data = _load_tasks()
    for task in data["active_tasks"]:
        if task["task_id"] == task_id:
            task["status"] = "ready_to_merge"
            task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _save_tasks(data)
            print(f"[TaskStorage] Task {task_id} marked as ready_to_merge")
            return True
    return False

def get_ready_to_merge_tasks():
    """
    Получить задачи готовые к merge

    Returns:
        list: список задач со статусом ready_to_merge
    """
    data = _load_tasks()
    return [t for t in data["active_tasks"] if t.get("status") == "ready_to_merge"]

def get_module_tasks(book, module):
    """
    Получить все задачи для конкретного модуля (glossary + tests)

    Args:
        book: название книги
        module: номер модуля

    Returns:
        list: список задач модуля
    """
    data = _load_tasks()
    return [t for t in data["active_tasks"]
            if t["book"] == book and t["module"] == module]

def is_module_ready(book, module):
    """
    Проверить, готов ли весь модуль (обе задачи завершены)

    Args:
        book: название книги
        module: номер модуля

    Returns:
        bool: True если обе задачи (glossary + tests) готовы к merge
    """
    tasks = get_module_tasks(book, module)
    if len(tasks) < 2:
        return False
    return all(t.get("status") == "ready_to_merge" for t in tasks)
