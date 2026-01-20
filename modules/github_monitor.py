import os
import re
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
    Проверить, завершена ли ветка (есть ли коммит с 'complete')

    Args:
        branch_name: название ветки

    Returns:
        bool: True если ветка завершена
    """
    event = get_latest_branch_event(branch_name)
    return event and event["type"] == "complete"
