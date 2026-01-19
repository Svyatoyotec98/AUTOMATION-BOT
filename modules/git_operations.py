import subprocess
from projects.cfa.config import REPO_PATH

def run_git_command(args, repo_path=REPO_PATH):
    """Выполнить git команду в папке проекта"""
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    return result

def git_fetch():
    """Подтянуть изменения с remote"""
    return run_git_command(["fetch", "origin"])

def git_checkout(branch):
    """Переключиться на ветку"""
    return run_git_command(["checkout", branch])

def git_pull():
    """Подтянуть изменения в текущую ветку"""
    return run_git_command(["pull"])

def git_merge(branch, message=None):
    """Смёрджить ветку в текущую"""
    if message:
        return run_git_command(["merge", branch, "-m", message])
    return run_git_command(["merge", branch, "--no-edit"])

def git_push():
    """Запушить изменения"""
    return run_git_command(["push", "origin", "main"])

def git_delete_branch_local(branch):
    """Удалить локальную ветку"""
    return run_git_command(["branch", "-D", branch])

def git_delete_branch_remote(branch):
    """Удалить remote ветку"""
    return run_git_command(["push", "origin", "--delete", branch])

def git_get_branches():
    """Получить список веток"""
    result = run_git_command(["branch", "-a"])
    return result.stdout

def git_add(file_path):
    """Добавить файл в stage"""
    return run_git_command(["add", file_path])

def git_commit(message):
    """Создать коммит"""
    return run_git_command(["commit", "-m", message])

def get_claude_branches():
    """Получить список веток claude/*"""
    result = run_git_command(["branch", "-r"])
    branches = []
    for line in result.stdout.split("\n"):
        line = line.strip()
        if "claude/" in line:
            branch = line.replace("origin/", "")
            branches.append(branch)
    return branches