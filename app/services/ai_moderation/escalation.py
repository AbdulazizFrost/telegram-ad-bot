"""
Tier 1 to Tier 2 Escalation Engine.
Determines whether a message is suspicious/borderline enough to warrant AI classification,
preserving zero-overhead throughput for obvious non-ads while catching evasive ads.
"""

import re
from typing import List, Optional
from app.services.moderation_filter.normalizer import full_normalize_text

# Broad semantic signals for commercial solicitation, buying, selling, or services
COMMERCIAL_INTENT_PATTERNS = [
    # Buying up / buyout / collection
    r'\b(?:sotib\s*olami[sz]|olami[sz]|olaman|pokupk[a-z]*|kuplyu|priyom[a-z]*|vykup[a-z]*|skupk[a-z]*)\b',
    # Selling / offers
    r'\b(?:sotilad[a-z]*|sotami[sz]|sotaman|proday[a-z]*|proda[a-z]*|rasprodaj[a-z]*)\b',
    # Scrap metal, batteries, raw materials
    r'\b(?:metal[a-z]*|alyumin[a-z]*|alimin[a-z]*|akku?mul[a-z]*|latun|med|mis)\b',
    # Service execution verbs
    r'\b(?:qilib\s*berami[sz]|qilami[sz]|tayyorlami[sz]|tamirlami[sz]|o\'rnatami[sz]|ornatami[sz])\b',
    # Work and hiring
    r'\b(?:ish\s*bor|ishchi\s*kerak|ishga\s*qabul|vakansiy[a-z]*|trebuyutsya|ishga\s*taklif)\b',
    # Commercial pricing & currency indicators
    r'\b(?:\d+\s*(?:ming|som|so\'m|rubl|dollar|\$|usd|uzs))\b',
    # PM / Direct contact invitations
    r'\b(?:lichkaga|lichkaga\s*yoz|lsga|ls\s*yoz|v\s*ls|dm|direkt)\b',
    # Trade and barter
    r'\b(?:obmen|barter|almashtirami[sz]|ijarag[a-z]*|arendag[a-z]*)\b',
    # Product arrivals, sets, wholesale, and promotions
    r'\b(?:keldi|kelgan|sotuvda|mavjud|nabor|komplekt|optom|donag[a-z]*|aksiya|chegirma|skidk[a-z]*)\b',
    # Dot prices or grouped digits: e.g. 5.000, 15.000, 30.000, 50 000, 50000 som
    r'\b(?:\d{1,3}(?:[\.\s]\d{3})+(?:\s*(?:som|so\'m|ming|uzs|rubl|\$))?)\b',
    # Services: e.g. xizmati bor, xizmatlar, remont, usta
    r'\b(?:xizmati\s*bor|xizmatlar|xizmat|buyurtma)\b',
]


# Genuine personal questions or seeker phrases that lack commercial contact info
GENUINE_SEEKER_PATTERNS = [
    r'\b(?:qayerga|qayerda|qachon|qanaqa|qanday|kimda|kimdir|topshirsa\s*bolad[a-z]*|sotsa\s*bolad[a-z]*)\b',
    r'\b(?:maslahat|bilasizmi|bilmaysizmi|tavsiya|qidiryapman|kerak\s*edi)\b',
]


def should_escalate_to_ai(
    raw_text: str,
    local_score: float,
    threshold: float = 40.0,
    extracted_phones: Optional[List[str]] = None,
    extracted_links: Optional[List[str]] = None,
    detected_locations: Optional[List[str]] = None,
) -> bool:
    """
    Decide whether a message should be escalated from Tier 1 (local) to Tier 2 (AI).

    Returns:
        True: Message is suspicious / borderline -> send to AI.
        False: Message is either confident ad (handled by Tier 1) or clean non-ad (allow immediately).
    """
    # 1. If local classifier is already confident that it is an ad, no need for AI
    if local_score >= threshold:
        return False

    if not raw_text or len(raw_text.strip()) < 4:
        return False

    normalized = full_normalize_text(raw_text)
    phones = extracted_phones or []
    links = extracted_links or []

    # 2. Borderline score (between 15.0 and threshold)
    if local_score >= 15.0:
        return True

    # 3. Presence of phone number or external link
    # An unknown message with a phone or link should always be scrutinized by AI
    if phones or links:
        # Check if it's an inquiry
        has_question_word = any(bool(re.search(pat, normalized)) for pat in GENUINE_SEEKER_PATTERNS)
        # Even with questions, if a contact phone is given, let AI determine if it's an ad or seeker
        return True

    # 4. Check for commercial intent patterns in text
    has_commercial_intent = any(bool(re.search(pat, normalized)) for pat in COMMERCIAL_INTENT_PATTERNS)
    if has_commercial_intent:
        # Check if it's a pure question without any seller/buyer imperative
        is_pure_question = (
            "?" in raw_text
            and any(bool(re.search(pat, normalized)) for pat in GENUINE_SEEKER_PATTERNS)
            and not bool(re.search(r'\b(?:olamiz|olaman|beramiz|qilamiz|yozing|telefon)\b', normalized))
        )
        if is_pure_question:
            # E.g. "Eski akumlyatorni qayerga topshirsa boladi?" -> Pure question, skip AI!
            return False

        # Otherwise, commercial words with offers/solicitations escalate to AI!
        return True

    # 5. Clean conversational message with 0 score -> DO NOT escalate
    return False
