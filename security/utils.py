import html
import re

def sanitize_text(text):
    safe_text = html.escape(text)
    safe_text = re.sub(r'<[^>]*>', '', safe_text)
    return safe_text