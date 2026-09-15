import re
import unicodedata
from typing import Optional, List


# Cyrillic to Latin homoglyph mapping (for anti-evasion matching)
CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': '', 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'ў': "o'", 'қ': 'q', 'ғ': "g'", 'ҳ': 'h'
}

# Common visual confusable characters
CONFUSABLES = {
    '0': 'o', '@': 'a', '$': 's', '1': 'i', '!': 'i'
}


def normalize_username(username: Optional[str]) -> Optional[str]:
    """
    Clean and normalize Telegram username:
    Removes '@' prefix, strips whitespace, converts to lowercase.
    Returns None if username is empty.
    """
    if not username:
        return None
    cleaned = username.strip().lstrip('@').strip().lower()
    return cleaned if cleaned else None


def normalize_text(text: str) -> str:
    """
    Normalize text for robust ad detection:
    1. Unicode NFKC normalization.
    2. Lowercase.
    3. Replace Cyrillic homoglyphs with Latin equivalents.
    4. Collapse repeated characters (e.g. 'soooootiladi' -> 'sotiladi').
    5. Clean excess whitespace.
    """
    if not text:
        return ""
    
    # 1. Unicode normalization
    text = unicodedata.normalize("NFKC", text)
    
    # 2. Lowercase
    text = text.lower()
    
    # 3. Cyrillic to Latin transliteration for uniform keyword checking
    transliterated_chars = []
    for char in text:
        if char in CYRILLIC_TO_LATIN:
            transliterated_chars.append(CYRILLIC_TO_LATIN[char])
        else:
            transliterated_chars.append(char)
    text = "".join(transliterated_chars)
    
    # Standardize apostrophes
    text = re.sub(r"[`'ʻʼ’‘]", "'", text)
    
    # 4. Collapse 3 or more identical consecutive letters to 1
    # e.g., 'soooootiladi' -> 'sotiladi', 'aaaaaksiya' -> 'aksiya'
    text = re.sub(r'(.)\1{2,}', r'\1', text)
    
    # 5. Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def extract_phone_numbers(text: str) -> List[str]:
    """
    Extract Uzbek phone numbers and common phone formats from text.
    Handles:
    +998 90 123 45 67
    998901234567
    90 123-45-67
    (90) 1234567
    """
    phone_pattern = re.compile(
        r'(?:\+?998[\s\-]?)?(?:\(?\d{2}\)?[\s\-]?)?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    )
    matches = phone_pattern.findall(text)
    
    # Filter out short digit sequences that matched by accident (less than 7 digits)
    cleaned = []
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if len(digits) >= 7:
            cleaned.append(m.strip())
    return cleaned


def extract_links(text: str) -> List[str]:
    """
    Extract web links, t.me links, instagram links, etc.
    """
    link_pattern = re.compile(
        r'(?:https?://[^\s]+|t\.me/[^\s]+|instagram\.com/[^\s]+|telegram\.me/[^\s]+)',
        re.IGNORECASE
    )
    return link_pattern.findall(text)
