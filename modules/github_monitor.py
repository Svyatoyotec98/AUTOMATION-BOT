import os
import re
from datetime import datetime, timezone
from github import Github
from config import GITHUB_TOKEN

# Репозиторий для мониторинга
REPO_NAME = "Svyatoyotec98/CFA-LVL-I-TRAINER"

def _get_github_client():
    """Получить клиент GitHub API"""
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not found in environment variables")
    return Github(GITHUB_TOKEN)

def _get_repo():
    """Получить репозиторий"""
    client = _get_github_client()
    return client.get_repo(REPO_NAME)

def get_claude_branches():
    """
    Получить список веток Claude (claude/*)

    Returns:
        list: список названий веток, начинающихся с 'claude/'
    """
    try:
        repo = _get_repo()
        branches = repo.get_branches()

        claude_branches = [
            branch.name for branch in branches
            if branch.name.startswith("claude/")
        ]

        print(f"[GitHubMonitor] Found {len(claude_branches)} Claude branches")
        return claude_branches

    except Exception as e:
        print(f"[GitHubMonitor] Error getting branches: {e}")
        return []

def get_branch_commits(branch_name):
    """
    Получить список коммитов для ветки

    Args:
        branch_name: название ветки

    Returns:
        list: список коммитов (dict с полями: sha, message, date)
    """
    try:
        repo = _get_repo()
        commits = repo.get_commits(sha=branch_name)

        commit_list = []
        for commit in commits:
            commit_list.append({
                "sha": commit.sha,
                "message": commit.commit.message,
                "date": commit.commit.author.date.strftime("%Y-%m-%d %H:%M:%S")
            })

        print(f"[GitHubMonitor] Found {len(commit_list)} commits in branch {branch_name}")
        return commit_list

    except Exception as e:
        print(f"[GitHubMonitor] Error getting commits for {branch_name}: {e}")
        return []

def parse_commit_message(message):
    """
    Парсить сообщение коммита для определения типа события

    Паттерны:
    - "checkpoint 1", "checkpoint 2" -> checkpoint
    - "complete" в сообщении -> complete

    Args:
        message: сообщение коммита

    Returns:
        dict: {"type": "checkpoint/complete", "checkpoint_name": "...", "checkpoint_num": N}
              или None если не распознано
    """
    message_lower = message.lower()

    # Проверка на complete
    if "complete" in message_lower:
        return {
            "type": "complete",
            "checkpoint_name": None,
            "checkpoint_num": None
        }

    # Проверка на checkpoint
    checkpoint_match = re.search(r'checkpoint\s+(\d+)', message_lower)
    if checkpoint_match:
        checkpoint_num = int(checkpoint_match.group(1))
        return {
            "type": "checkpoint",
            "checkpoint_name": f"checkpoint {checkpoint_num}",
            "checkpoint_num": checkpoint_num
        }

    return None

def get_latest_branch_event(branch_name):
    """
    Получить последнее событие (checkpoint/complete) для ветки

    Args:
        branch_name: название ветки

    Returns:
        dict: {"type": "checkpoint/complete", "checkpoint_name": "...", "date": "..."}
              или None если событий нет
    """
    commits = get_branch_commits(branch_name)

    for commit in commits:
        event = parse_commit_message(commit["message"])
        if event:
            event["date"] = commit["date"]
            return event

    return None

def get_all_branch_checkpoints(branch_name):
    """
    Получить все checkpoint'ы для ветки

    Args:
        branch_name: название ветки

    Returns:
        list: список checkpoint'ов [{"name": "checkpoint 1", "date": "..."}]
    """
    commits = get_branch_commits(branch_name)
    checkpoints = []

    for commit in commits:
        event = parse_commit_message(commit["message"])
        if event and event["type"] == "checkpoint":
            checkpoints.append({
                "name": event["checkpoint_name"],
                "date": commit["date"]
            })

    # Сортировать по номеру checkpoint
    checkpoints.sort(key=lambda x: int(re.search(r'\d+', x["name"]).group()))
    return checkpoints

def check_branch_completed(branch_name):
    """
    Проверить завершена ли задача в ветке.
    Проверяем ТОЛЬКО ПОСЛЕДНИЙ коммит на наличие паттернов завершения:
    - "complete"
    - "готов"
    - "checkpoint 2" или выше
    - "finished"
    - "done"
    """
    try:
        repo = _get_repo()
        branch = repo.get_branch(branch_name)
        last_commit = branch.commit

        # Проверяем ТОЛЬКО последний коммит
        message = last_commit.commit.message.lower()

        # Паттерны завершения
        completion_patterns = [
            "complete",
            "готов",
            "finished",
            "done"
        ]

        # Проверка базовых паттернов
        for pattern in completion_patterns:
            if pattern in message:
                print(f"[GitHubMonitor] Branch {branch_name} is COMPLETED (found '{pattern}' in last commit)")
                return True

        # Проверка checkpoint 2 или выше
        checkpoint_match = re.search(r'checkpoint\s+(\d+)', message)
        if checkpoint_match:
            checkpoint_num = int(checkpoint_match.group(1))
            if checkpoint_num >= 2:
                print(f"[GitHubMonitor] Branch {branch_name} is COMPLETED (checkpoint {checkpoint_num} >= 2)")
                return True

        return False

    except Exception as e:
        print(f"[GitHubMonitor] Error checking branch {branch_name}: {e}")
        return False

def get_last_commit_info(branch_name):
    """
    Получить информацию о последнем коммите ветки.
    """
    try:
        repo = _get_repo()
        branch = repo.get_branch(branch_name)
        commit = branch.commit

        # Время коммита (aware datetime)
        commit_time = commit.commit.author.date

        # Текущее время тоже делаем aware (UTC)
        now = datetime.now(timezone.utc)

        # Теперь можно вычитать
        minutes_ago = int((now - commit_time).total_seconds() / 60)

        return {
            "message": commit.commit.message,
            "time": commit_time,
            "minutes_ago": minutes_ago
        }
    except Exception as e:
        print(f"[GitHubMonitor] Error getting last commit for {branch_name}: {e}")
        return None

def find_branch_for_task(task_type, book, module, branches):
    """
    Найти подходящую ветку для задачи по гибким паттернам.

    Args:
        task_type: тип задачи ("glossary" или "tests")
        book: название книги (например, "Financial Reporting", "Quantitative Methods")
        module: номер модуля
        branches: список веток для поиска

    Returns:
        str: название найденной ветки или None
    """
    # Извлекаем первое слово книги (например, "financial" из "Financial Reporting")
    first_word = book.lower().split()[0] if book else ""

    module_str = str(module)

    for branch in branches:
        branch_lower = branch.lower()

        # Проверка первого слова книги (например, "financial", "quantitative")
        book_match = first_word in branch_lower if first_word else False

        # Проверка номера модуля в разных форматах:
        # - module-5
        # - module5
        # - -5-
        # - заканчивается на -5
        module_match = (
            f"module-{module_str}" in branch_lower or
            f"module{module_str}" in branch_lower or
            f"-{module_str}-" in branch_lower or
            branch_lower.endswith(f"-{module_str}")
        )

        # Проверка типа задачи
        if task_type == "glossary":
            # Ищем "glossary" или "glossar" (без y)
            type_match = "glossar" in branch_lower
        else:  # tests
            # Ищем "test" или "qbank"
            type_match = "test" in branch_lower or "qbank" in branch_lower

        # Если все совпало - возвращаем ветку
        if book_match and module_match and type_match:
            print(f"[GitHubMonitor] Found branch for {book} Module {module} {task_type}: {branch}")
            return branch

    print(f"[GitHubMonitor] No branch found for {book} Module {module} {task_type}")
    return None
