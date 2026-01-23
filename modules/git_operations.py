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

def git_merge_theirs(branch):
    """
    Смёрджить ветку с автоматическим разрешением конфликтов.
    -X theirs = при конфликте брать версию из входящей ветки (Accept Incoming Change)
    """
    return run_git_command(["merge", branch, "-X", "theirs", "-m", f"Merge {branch}"])

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

def merge_module_branches(glossary_branch, tests_branch, repo_path=REPO_PATH):
    """
    Смёрджить обе ветки модуля (glossary + tests) в main.

    Алгоритм:
    1. git fetch origin
    2. git checkout main && git pull
    3. git merge glossary-ветка (обычно без конфликтов)
    4. git merge tests-ветка -X theirs (автоматически Accept Incoming при конфликте)
    5. git push origin main
    6. Удалить обе ветки

    Returns:
        dict: {"success": bool, "message": str}
    """
    results = []

    # Добавляем origin/ если нет
    if not glossary_branch.startswith("origin/"):
        glossary_branch = f"origin/{glossary_branch}"
    if not tests_branch.startswith("origin/"):
        tests_branch = f"origin/{tests_branch}"

    try:
        # 1. Fetch
        print("[Git] Fetching origin...")
        git_fetch()

        # 2. Checkout main и pull
        print("[Git] Checkout main...")
        checkout_result = git_checkout("main")
        if checkout_result.returncode != 0:
            return {"success": False, "message": f"Checkout main failed: {checkout_result.stderr}"}

        pull_result = git_pull()
        if pull_result.returncode != 0:
            return {"success": False, "message": f"Pull failed: {pull_result.stderr}"}

        # 3. Merge glossary (первым, обычно без конфликтов)
        print(f"[Git] Merging glossary: {glossary_branch}...")
        glossary_result = git_merge(glossary_branch, f"Merge {glossary_branch}")
        if glossary_result.returncode != 0:
            # Попробуем с -X theirs
            glossary_result = git_merge_theirs(glossary_branch)
            if glossary_result.returncode != 0:
                return {"success": False, "message": f"Merge glossary failed: {glossary_result.stderr}"}
        results.append(f"✅ Glossary merged")

        # 4. Merge tests с -X theirs (автоматическое разрешение конфликтов)
        print(f"[Git] Merging tests: {tests_branch}...")
        tests_result = git_merge_theirs(tests_branch)
        if tests_result.returncode != 0:
            return {"success": False, "message": f"Merge tests failed: {tests_result.stderr}"}
        results.append(f"✅ Tests merged")

        # 5. Push
        print("[Git] Pushing to origin...")
        push_result = git_push()
        if push_result.returncode != 0:
            return {"success": False, "message": f"Push failed: {push_result.stderr}"}
        results.append(f"✅ Pushed to main")

        # 6. Удалить ветки на GitHub
        print("[Git] Deleting branches...")
        glossary_branch_clean = glossary_branch.replace("origin/", "")
        tests_branch_clean = tests_branch.replace("origin/", "")
        git_delete_branch_remote(glossary_branch_clean)
        git_delete_branch_remote(tests_branch_clean)

        # 7. Очистить локальный кэш удалённых веток
        print("[Git] Pruning local cache...")
        run_git_command(["fetch", "--prune"])

        results.append(f"✅ Branches deleted")

        return {"success": True, "message": "\n".join(results)}

    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def delete_all_claude_branches():
    """
    Удалить ВСЕ ветки claude/* на GitHub и очистить локальный кэш.

    Returns:
        dict: {"success": bool, "deleted": list, "errors": list}
    """
    deleted = []
    errors = []

    try:
        # Получить список веток
        git_fetch()
        branches = get_claude_branches()

        # Удалить каждую ветку
        for branch in branches:
            branch_clean = branch.replace("origin/", "")
            result = git_delete_branch_remote(branch_clean)
            if result.returncode == 0:
                deleted.append(branch_clean)
                print(f"[Git] Deleted branch: {branch_clean}")
            else:
                errors.append({"branch": branch_clean, "error": result.stderr})
                print(f"[Git] Failed to delete {branch_clean}: {result.stderr}")

        # Очистить локальный кэш
        run_git_command(["fetch", "--prune"])

        return {"success": len(errors) == 0, "deleted": deleted, "errors": errors}

    except Exception as e:
        return {"success": False, "deleted": deleted, "errors": [str(e)]}