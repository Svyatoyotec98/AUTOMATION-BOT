import subprocess
import json
import re
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

def resolve_meta_json_conflict(repo_path, book_folder):
    """
    Разрешить конфликт в meta.json методом Accept Both Changes.
    Объединяет glossary_file и qbank_file из обеих версий.
    """
    meta_path = f"{repo_path}/frontend/data/v2/books/{book_folder}/meta.json"

    with open(meta_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Если нет маркеров конфликта - ничего делать не нужно
    if '<<<<<<<' not in content:
        return True

    # Читаем оригинальный meta.json из HEAD (до конфликта)
    # и incoming версию, затем объединяем

    # Паттерн для поиска конфликтных блоков
    # Формат: <<<<<<< HEAD ... ======= ... >>>>>>> branch

    # Простой подход: построчно обработать
    lines = content.split('\n')
    result_lines = []
    in_conflict = False
    head_lines = []
    incoming_lines = []
    in_head = False
    in_incoming = False

    for line in lines:
        if '<<<<<<<' in line:
            in_conflict = True
            in_head = True
            continue
        elif '=======' in line and in_conflict:
            in_head = False
            in_incoming = True
            continue
        elif '>>>>>>>' in line and in_conflict:
            # Конец конфликта - объединяем
            # Берём обе строки (glossary_file и qbank_file)
            for h_line in head_lines:
                if h_line.strip() and h_line.strip() not in [l.strip() for l in incoming_lines]:
                    result_lines.append(h_line)
            for i_line in incoming_lines:
                result_lines.append(i_line)

            head_lines = []
            incoming_lines = []
            in_conflict = False
            in_head = False
            in_incoming = False
            continue

        if in_head:
            head_lines.append(line)
        elif in_incoming:
            incoming_lines.append(line)
        else:
            result_lines.append(line)

    # Записываем результат
    with open(meta_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result_lines))

    return True

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

        # 4. Merge tests (с ручным разрешением конфликта если нужно)
        print(f"[Git] Merging tests: {tests_branch}...")
        tests_result = git_merge(tests_branch, f"Merge {tests_branch}")

        if tests_result.returncode != 0:
            # Проверяем есть ли конфликт
            if "CONFLICT" in tests_result.stdout or "CONFLICT" in tests_result.stderr:
                print("[Git] Conflict detected in meta.json, resolving with Accept Both Changes...")

                # Определяем book_folder из имени ветки
                # Формат: claude/add-{book}-module-{N}-tests-{random}
                # Например: claude/add-fsa-module-8-tests-KchHy
                branch_name = tests_branch.replace("origin/", "")

                # Маппинг коротких имён на папки
                book_folder_map = {
                    "quants": "book1_quants",
                    "qm": "book1_quants",
                    "econ": "book2_economics",
                    "economics": "book2_economics",
                    "fsa": "book3_fsa",
                    "financial": "book3_fsa",
                    "cf": "book4_cf",
                    "corporate": "book4_cf",
                    "equity": "book5_equity",
                    "ei": "book5_equity",
                    "fi": "book6_fi",
                    "fixed": "book6_fi",
                    "der": "book7_derivatives",
                    "derivatives": "book7_derivatives",
                    "alt": "book8_alt",
                    "alternative": "book8_alt",
                    "pm": "book9_pm",
                    "portfolio": "book9_pm",
                    "ethics": "book10_ethics",
                    "eth": "book10_ethics",
                }

                # Извлекаем book из имени ветки
                book_folder = None
                for key, folder in book_folder_map.items():
                    if f"add-{key}-module" in branch_name.lower():
                        book_folder = folder
                        break

                if book_folder:
                    try:
                        resolve_meta_json_conflict(repo_path, book_folder)
                        git_add(f"frontend/data/v2/books/{book_folder}/meta.json")
                        git_commit("Merge resolved: accept both changes for meta.json")
                        results.append(f"✅ Tests merged (conflict resolved)")
                    except Exception as e:
                        return {"success": False, "message": f"Failed to resolve conflict: {str(e)}"}
                else:
                    return {"success": False, "message": f"Could not determine book folder from branch: {branch_name}"}
            else:
                return {"success": False, "message": f"Merge tests failed: {tests_result.stderr}"}
        else:
            results.append(f"✅ Tests merged")

        # 5. Push
        print("[Git] Pushing to origin...")
        push_result = git_push()
        if push_result.returncode != 0:
            return {"success": False, "message": f"Push failed: {push_result.stderr}"}
        results.append(f"✅ Pushed to main")

        # 6. Удалить ветки
        print("[Git] Deleting branches...")
        git_delete_branch_remote(glossary_branch)
        git_delete_branch_remote(tests_branch)
        results.append(f"✅ Branches deleted")

        return {"success": True, "message": "\n".join(results)}

    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}