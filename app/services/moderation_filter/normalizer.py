import re
import unicodedata
from typing import List

# Emoji and stylized digits mapping
EMOJI_DIGITS = {
    '0️⃣': '0', '1️⃣': '1', '2️⃣': '2', '3️⃣': '3', '4️⃣': '4',
    '5️⃣': '5', '6️⃣': '6', '7️⃣': '7', '8️⃣': '8', '9️⃣': '9',
    '⓪': '0', '①': '1', '②': '2', '③': '3', '④': '4',
    '⑤': '5', '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9',
    '➊': '1', '➋': '2', '➌': '3', '➍': '4', '➎': '5',
    '➏': '6', '➐': '7', '➑': '8', '➒': '9', '⓿': '0',
    '𝟢': '0', '𝟣': '1', '𝟤': '2', '𝟥': '3', '𝟦': '4',
    '𝟧': '5', '𝟨': '6', '𝟩': '7', '𝟪': '8', '𝟫': '9',
    '𝟘': '0', '𝟙': '1', '𝟚': '2', '𝟛': '3', '𝟜': '4',
    '𝟝': '5', '𝟞': '6', '𝟟': '7', '𝟠': '8', '𝟡': '9',
    '𝟬': '0', '𝟭': '1', '𝟮': '2', '𝟯': '3', '𝟰': '4',
    '𝟱': '5', '𝟲': '6', '𝟳': '7', '𝟴': '8', '𝟵': '9'
}

# Cyrillic to Latin homoglyphs mapping
CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': '', 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'ў': "o'", 'қ': 'q', 'ғ': "g'", 'ҳ': 'h'
}

UZBEK_OPERATOR_CODES = {
    "90", "91", "93", "94", "95", "97", "98", "99",
    "88", "77", "33", "20", "50", "55", "71"
}


def replace_emoji_digits(text: str) -> str:
    """Convert emoji & mathematical stylized digits to standard ASCII digits."""
    for emoji_char, digit in EMOJI_DIGITS.items():
        if emoji_char in text:
            text = text.replace(emoji_char, digit)
    return text


def full_normalize_text(text: str) -> str:
    """
    Advanced multi-stage text normalization for evasion-proof filtering:
    1. Emoji and circled digit replacement
    2. Unicode NFKC normalization
    3. Lowercase conversion
    4. Cyrillic to Latin transliteration
    5. Standardize apostrophes
    6. Fix spaced URLs ('t.me / username' -> 't.me/username')
    7. Fix spaced Telegram mentions ('@ u s e r' -> '@user')
    8. De-space single letters ('т а к с и' -> 'taksi')
    9. De-space spaced digits ('9 0 1 2 3 4 5 6 7' -> '901234567')
    10. Remove punctuation separators in words ('так-си' -> 'taksi')
    11. Collapse repeated characters ('таааксиии' -> 'taksi')
    12. Whitespace consolidation
    """
    if not text:
        return ""

    # 1. Emoji digits
    text = replace_emoji_digits(text)

    # 2. Unicode NFKC
    text = unicodedata.normalize("NFKC", text)

    # 3. Lowercase
    text = text.lower()

    # 4. Cyrillic to Latin transliteration
    chars = []
    for ch in text:
        chars.append(CYRILLIC_TO_LATIN.get(ch, ch))
    text = "".join(chars)

    # 5. Standardize apostrophes
    text = re.sub(r"[`'ʻʼ’‘]", "'", text)

    # 6. Fix spaced URLs
    text = re.sub(r'\bt\s*\.\s*me\s*/\s*([a-z0-9_]+)', r't.me/\1', text)
    text = re.sub(r'\btelegram\s*\.\s*me\s*/\s*([a-z0-9_]+)', r't.me/\1', text)
    text = re.sub(r'https?\s*:\s*/\s*/\s*', r'https://', text)

    # 7. Fix spaced Telegram mentions: '@ u s e r' -> '@user'
    def fix_spaced_mention(match):
        raw_nick = match.group(1)
        return "@" + re.sub(r'\s+', '', raw_nick)
    text = re.sub(r'@\s+([a-z0-9_\s]{2,32})', fix_spaced_mention, text)

    # 8. De-space single letters: 't a k s i' -> 'taksi', 't e l e g r a m' -> 'telegram'
    # Repeat until no more isolated single letters with spaces remain
    prev_text = None
    while prev_text != text:
        prev_text = text
        text = re.sub(r'(?<=\b[a-z])\s+(?=[a-z]\b)', '', text)

    # 9. De-space sequences of single digits: '9 0 1 2 3 4 5 6 7' -> '901234567'
    # Only if sequence forms 7 or more digits to avoid collapsing legitimate numbers
    def despace_digit_run(match):
        digits = re.sub(r'\D', '', match.group(0))
        return digits if len(digits) >= 7 else match.group(0)
    text = re.sub(r'(?:\b\d\s+){6,}\d\b', despace_digit_run, text)

    # 10. Punctuation separators in and between words:
    # Multiple separators (e.g. 'soz..soz', 'soz...soz') -> replace with space
    text = re.sub(r'[._\-*]{2,}', ' ', text)
    # Digits attached directly to words: '2odam' -> '2 odam', '3kishi' -> '3 kishi'
    text = re.sub(r'(\d+)([a-z]+)', r'\1 \2', text)
    # Punctuation between digits and letters -> replace with space (e.g. '3.odam' -> '3 odam')
    text = re.sub(r'(?<=\d)[._\-*]+(?=[a-z])', ' ', text)
    text = re.sub(r'(?<=[a-z])[._\-*]+(?=\d)', ' ', text)
    # Single separator between words/syllables:
    # If both sides are full words (len >= 3) -> replace with space (e.g. 'gulistonga.tez.ketamiz' -> 'gulistonga tez ketamiz')
    # If short syllables/single letters (e.g. 't-a-k-s-i', 'tak-si') -> collapse to word
    prev_sep = None
    while prev_sep != text:
        prev_sep = text
        def handle_sep(m):
            w1, sep, w2 = m.group(1), m.group(2), m.group(3)
            if (len(w1) >= 3 and len(w2) >= 3) or w2 in ('kk', 'bor', 'yoq', 'da', 'ga', 'go', 'ka'):
                return f"{w1} {w2}"
            return f"{w1}{w2}"
        text = re.sub(r'\b([a-z]+)([-_.*])([a-z]+)\b', handle_sep, text)

    # 11. Collapse repeated characters in words (letters only, preserving phone number digits): 'taaaaksiiii' -> 'taksi'
    text = re.sub(r'([a-zA-Zа-яА-ЯёЁ])\1{2,}', r'\1', text)

    # 12. Clean excess whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def extract_normalized_phones(raw_text: str) -> List[str]:
    """
    Extract phone numbers even if obfuscated by spaces, hyphens, dots, or parentheses.
    E.g.:
    +998901234567, +998 90 123 45 67, 90-123-45-67, 90.123.45.67,
    (90) 123 45 67, 9 0 1 2 3 4 5 6 7, 9️⃣0️⃣1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣.

    Safeguards:
    Does NOT match non-phone numeric sequences like times ('19:00'),
    years ('2026'), or prices ('100000').
    """
    if not raw_text:
        return []

    # Replace emoji digits
    text = replace_emoji_digits(raw_text)

    # Pattern for phone sequences: optional +998, 2-digit operator code, and 7 digits with arbitrary separators
    # Example: (+998)? [ -.]? (90) [ -.]? 123 [ -.]? 45 [ -.]? 67
    phone_regex = re.compile(
        r'(?<!\d)(?:\+?998[\s\-.]*)?(?:\(?(?:9[0-9]|88|77|95|97|98|99|93|94|91|33|20|50|55|71)\)?[\s\-.]*)'
        r'(?:\d[\s\-.]*){6,7}\d\b'
    )

    results = []
    for match in phone_regex.finditer(text):
        matched_str = match.group(0)
        digits = re.sub(r'\D', '', matched_str)
        # Check standard Uzbek phone lengths: 9 digits (operator + 7) or 12 digits (998 + operator + 7)
        if len(digits) == 9 and digits[:2] in UZBEK_OPERATOR_CODES:
            results.append(matched_str.strip())
        elif len(digits) == 12 and digits.startswith("998") and digits[3:5] in UZBEK_OPERATOR_CODES:
            results.append(matched_str.strip())

    return results


def extract_normalized_links(text: str) -> List[str]:
    """Extract web links and telegram invite links with obfuscation handling."""
    if not text:
        return []
    # Normalize spaced protocol, domains and t.me links
    cleaned = re.sub(r'https?:\s*/\s*/\s*', 'https://', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\w+)\s*\.\s*(me|uz|com|ru|org|net|io|shop|info)\b', r'\1.\2', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bt\s*\.\s*me\s*/\s*', 't.me/', cleaned, flags=re.IGNORECASE)
    link_pattern = re.compile(
        r'(?:https?://[^\s]+|t\.me/[^\s]+|instagram\.com/[^\s]+|telegram\.me/[^\s]+|www\.[a-zA-Z0-9_.-]+|[a-zA-Z0-9_-]+\.(?:uz|com|ru|org|net|me)(?:/[^\s]*)?)',
        re.IGNORECASE
    )
    return link_pattern.findall(cleaned)

