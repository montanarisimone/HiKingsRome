def escape_markdown(text):
    """Escape Telegram markdown special characters in a string."""
    if not isinstance(text, str):
        text = str(text)
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def escape_markdown_v2(text):
    """Escape Telegram MarkdownV2 special characters."""
    if not isinstance(text, str):
        text = str(text)
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text
