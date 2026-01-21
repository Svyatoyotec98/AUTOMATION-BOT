PROMPTS = {
    "tests": """Привет! Будем заполнять наш проект контентом.

⚠️ ПЕРВЫМ ДЕЛОМ создай ветку в ТОЧНОМ формате:
git checkout -b claude/add-{book_lower}-module-{module}-tests-XXXXX
git push -u origin claude/add-{book_lower}-module-{module}-tests-XXXXX

Где XXXXX - любые 5 случайных символов.
Пример для этой задачи: claude/add-{book_lower}-module-{module}-tests-aB3nQ

⛔ НЕ НАЧИНАЙ РАБОТУ пока ветка не создана и не запушена!

Найди в папке Instructions инструкцию для создания тестов (QBANK_INSTRUCTION.md), и исполни её.
Это нужно сделать для {module} главы книги {book}.
Удачи""",

    "glossary": """Привет! Будем заполнять наш проект контентом.

⚠️ ПЕРВЫМ ДЕЛОМ создай ветку в ТОЧНОМ формате:
git checkout -b claude/add-{book_lower}-module-{module}-glossary-XXXXX
git push -u origin claude/add-{book_lower}-module-{module}-glossary-XXXXX

Где XXXXX - любые 5 случайных символов.
Пример для этой задачи: claude/add-{book_lower}-module-{module}-glossary-aB3nQ

⛔ НЕ НАЧИНАЙ РАБОТУ пока ветка не создана и не запушена!

Найди в папке Instructions инструкцию для создания глоссария (GLOSSARY_INSTRUCTION.md), и исполни её.
Это нужно сделать для {module} главы книги {book}.
Удачи""",
}


def generate_prompt(content_type: str, book_name: str, module_num: int) -> str:
    """Генерация промпта для Claude Code"""
    template = PROMPTS.get(content_type)
    if not template:
        raise ValueError(f"Unknown content type: {content_type}")

    # Создаём book_lower для названия ветки
    book_lower = book_name.lower().replace(" ", "-").split("-")[0]  # "Economics" -> "economics"

    return template.format(
        module=module_num,
        book=book_name,
        book_lower=book_lower
    )