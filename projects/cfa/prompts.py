PROMPTS = {
    "tests": """Привет! Будем заполнять наш проект контентом. 
Найди в папке Instructions инструкцию для создания тестов, и исполни её. 
Это нужно сделать для {module} главы книги {book}. 
Удачи""",

    "glossary": """Привет! Будем заполнять наш проект контентом. 
Найди в папке Instructions инструкцию для создания глоссария, и исполни её. 
Это нужно сделать для {module} главы книги {book}. 
Удачи""",
}


def generate_prompt(content_type: str, book_name: str, module_num: int) -> str:
    """Генерация промпта для Claude Code"""
    template = PROMPTS.get(content_type)
    if not template:
        raise ValueError(f"Unknown content type: {content_type}")
    
    return template.format(module=module_num, book=book_name)