import re
import unicodedata


def normalize_paragraph(text: str) -> str:
    """Normalize a single paragraph from a Vietnamese legal .docx file.

    Applied BEFORE the state machine parser sees any text.
    """
    text = text.replace("\xa0", " ")       # non-breaking space — found in Luật 36
    text = text.replace("​", "")      # zero-width space
    text = text.replace("’", "'")     # curly right apostrophe
    text = text.replace("‘", "'")     # curly left apostrophe
    text = re.sub(r"[ \t]+", " ", text)   # collapse spaces/tabs (not newlines)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_legal_terms(query: str) -> str:
    """Map colloquial terms to legal Vietnamese terminology."""
    mappings = {
        r"\bvượt đèn đỏ\b": "không chấp hành hiệu lệnh của đèn tín hiệu giao thông",
        r"\bxe máy\b": "xe mô tô",
        r"\bbằng lái\b": "giấy phép lái xe",
        r"\bgiữ bằng\b": "tạm giữ giấy phép lái xe",
        r"\bphạt nguội\b": "xử phạt qua phương tiện thiết bị kỹ thuật nghiệp vụ",
    }
    result = query.lower()
    for pattern, replacement in mappings.items():
        result = re.sub(pattern, replacement, result)
    return result
