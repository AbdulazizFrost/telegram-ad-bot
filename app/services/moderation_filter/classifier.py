import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from aiogram.types import Message
from aiogram.enums import MessageEntityType

from app.services.moderation_filter.normalizer import (
    full_normalize_text,
    extract_normalized_phones,
    extract_normalized_links,
)
from app.services.moderation_filter.patterns import (
    HIGH_SALE_PATTERNS,
    HIGH_TAXI_PATTERNS,
    HIGH_CONTACT_PATTERNS,
    MEDIUM_COMMERCIAL_KEYWORDS,
    QUESTION_PATTERNS,
    ACTIVE_OFFER_PATTERNS,
    ACTIVE_CTA_PATTERNS,
    FIRST_PERSON_INQUIRY_PATTERNS,
    INTERROGATIVE_WORDS,
)
from app.config import settings


@dataclass
class ClassificationResult:
    is_ad: bool = False
    score: float = 0.0
    reason: str = ""
    violation_type: str = "OTHER_AD_VIOLATION"
    normalized_text: str = ""
    extracted_phones: List[str] = field(default_factory=list)
    extracted_links: List[str] = field(default_factory=list)


def classify_text(
    raw_text: str,
    entities: Optional[List] = None,
    threshold: Optional[int] = None
) -> ClassificationResult:
    """
    Score-based advertisement classifier with anti-evasion normalization.
    Returns structured ClassificationResult.
    """
    if threshold is None:
        threshold = settings.AD_DETECTION_THRESHOLD

    if not raw_text or len(raw_text.strip()) < 3:
        return ClassificationResult(is_ad=False, score=0.0)

    score = 0.0
    reasons = []
    is_taxi_related = False
    is_sale_related = False

    # 1. Multi-stage normalization
    normalized = full_normalize_text(raw_text)

    # 2. Extract links & handles
    extracted_links = extract_normalized_links(raw_text)
    extracted_phones = extract_normalized_phones(raw_text)

    # Telegram entity check
    if entities:
        for ent in entities:
            if ent.type in (MessageEntityType.URL, MessageEntityType.TEXT_LINK):
                url = ent.url if ent.type == MessageEntityType.TEXT_LINK else ent.extract_from(raw_text)
                if url and url not in extracted_links:
                    extracted_links.append(url)
            elif ent.type == MessageEntityType.PHONE_NUMBER:
                p = ent.extract_from(raw_text)
                if p and p not in extracted_phones:
                    extracted_phones.append(p)

    # Signal: Promotional links (+60)
    if extracted_links:
        score += 60.0
        reasons.append(f"Tashqi reklama havolasi: {extracted_links[0]}")
        is_sale_related = True

    # Signal: High commercial sales (+50)
    for kw in HIGH_SALE_PATTERNS:
        if re.search(r'\b' + re.escape(kw) + r'\b', normalized) or kw in normalized:
            score += 50.0
            reasons.append(f"Tijoriy taklif kalit so'zi: '{kw}'")
            is_sale_related = True
            break

    # Signal: High taxi offers (+50)
    for kw in HIGH_TAXI_PATTERNS:
        if re.search(r'\b' + re.escape(kw) + r'\b', normalized) or kw in normalized:
            score += 50.0
            reasons.append(f"Taksi qatnovi taklifi: '{kw}'")
            is_taxi_related = True
            break

    # Signal: Direct contact / Call to action (+40)
    has_contact_phrase = False
    for kw in HIGH_CONTACT_PATTERNS:
        if re.search(r'\b' + re.escape(kw) + r'\b', normalized) or kw in normalized:
            score += 40.0
            reasons.append(f"Bog'lanish chaqiruvi: '{kw}'")
            has_contact_phrase = True
            break

    # Signal: PM solicitation ('lichkaga', 'lichgaga', 'lsga', 'direkt', 'direct', 'dm')
    has_pm_request = bool(re.search(r'\b(?:lich[kg]a[a-z]*|ls(?:ga)?|pm(?:ga)?|direkt(?:ga)?|direct(?:ga)?|dm(?:ga)?)\b', normalized))
    if has_pm_request:
        taxi_or_travel = bool(re.search(r'\b(?:ta[kx]si[a-z]*|mashina|moshina|yurami[a-z]*|qatnaymi[a-z]*|odam|joy|pochta|ketsa|borsa|ketadi|boradi)\b', normalized))
        if taxi_or_travel:
            score += 55.0
            reasons.append("Taksi qatnovi va shaxsiy xabarga (lichkaga) chaqiruv")
            is_taxi_related = True
        elif is_sale_related or has_contact_phrase or extracted_phones or extracted_links:
            score += 40.0
            reasons.append("Tijoriy taklif va shaxsiy xabarga (lichkaga) chaqiruv")
        else:
            score += 15.0
            reasons.append("Shaxsiy xabarga (lichkaga) yozish taklifi")

    # Signal: Phone numbers (+25 alone, +45 if commercial/transit context)
    if extracted_phones:
        has_context = is_sale_related or is_taxi_related or has_contact_phrase or has_pm_request
        if has_context:
            score += 45.0
            reasons.append(f"Aloqa telefoni tijoriy kontekst bilan: {extracted_phones[0]}")
        else:
            # Check if any soft commercial words present
            soft_matches = [w for w in MEDIUM_COMMERCIAL_KEYWORDS if re.search(r'\b' + re.escape(w) + r'\b', normalized)]
            if soft_matches:
                score += 40.0
                reasons.append(f"Telefon va tijoriy so'z: {soft_matches[0]}")
            else:
                score += 25.0

    # Signal: Medium commercial words (+15)
    soft_found = [w for w in MEDIUM_COMMERCIAL_KEYWORDS if re.search(r'\b' + re.escape(w) + r'\b', normalized)]
    if soft_found and not (is_sale_related or is_taxi_related):
        score += min(len(soft_found) * 15.0, 30.0)

    # Check for Channel/Bot mentions (@username)
    mentions = re.findall(r'@([a-zA-Z0-9_]{4,})', raw_text)
    if mentions:
        has_channel_word = bool(re.search(r'\b(?:kanal[a-z]*|guruh[a-z]*|podpisk[a-z]*|podpis[a-z]*|obuna|qoshil[a-z]*|qo\'shil[a-z]*)\b', normalized))
        if is_sale_related or is_taxi_related or has_contact_phrase or has_pm_request or has_channel_word:
            score += 30.0
            reasons.append(f"Profil/kanal havolasi: @{mentions[0]}")
            if has_channel_word and not is_sale_related:
                is_sale_related = True

    # Negative Signals: Inquiries, questions, recommendation requests
    has_question_mark = "?" in raw_text
    question_words = [q for q in (QUESTION_PATTERNS + INTERROGATIVE_WORDS) if re.search(r'\b' + re.escape(q) + r'\b', normalized)]
    has_verb_question = bool(re.search(r'\b[a-z\']{2,}(?:dimi|dymi|adimi|edimi|asizmi|asilarmi|mikan|mikin|yaptimi|ganmi|kanmi)\b', normalized))
    has_first_person_inquiry = any(re.search(r'\b' + re.escape(fp) + r'\b', normalized) for fp in FIRST_PERSON_INQUIRY_PATTERNS)

    is_inquiry_signal = has_question_mark or len(question_words) > 0 or has_verb_question or has_first_person_inquiry

    # Active seller / promotional check
    has_active_offer = any(re.search(r'\b' + re.escape(p) + r'\b', normalized) for p in ACTIVE_OFFER_PATTERNS)
    has_active_cta = any(re.search(r'\b' + re.escape(c) + r'\b', normalized) for c in ACTIVE_CTA_PATTERNS)
    has_direct_contact = bool(extracted_phones or extracted_links or mentions)

    # Distinguish rhetorical marketing hook questions from genuine user inquiries:
    if has_first_person_inquiry:
        # A person asking where/how to write or apply is a seeker, not a seller
        is_inquiry = True
    elif has_pm_request and not has_question_mark and not has_verb_question:
        # An imperative call to PM without question form (e.g. 'kim ketsa lichkaga yozsin') is an offer, not an inquiry
        is_inquiry = False
    elif has_active_cta and not (has_question_mark or has_verb_question):
        # E.g. 'kimga kerak bo'lsa yozsin' without question is a sales call, not an inquiry
        is_inquiry = False
    elif (has_active_offer or has_active_cta) and (has_direct_contact or has_pm_request):
        # A marketing hook offering services + telling audience to contact author
        is_inquiry = False
    elif has_active_offer and not (has_question_mark or has_verb_question):
        is_inquiry = False
    elif has_active_offer and has_question_mark and not ('bormi' in normalized or 'qidiryapman' in normalized):
        # E.g. 'Kimga ish kerak? Onlayn ishlash imkoniyati mavjud.' -> Rhetorical question selling an offer
        is_inquiry = False
    else:
        is_inquiry = is_inquiry_signal

    if is_inquiry:
        # Question penalty
        score -= 35.0
        # If no commercial link, no phone, and no PM solicitation -> strong reduction to protect user questions
        if not has_direct_contact and not has_pm_request:
            score -= 40.0

    score = max(0.0, score)
    is_ad = score >= threshold

    # Determine specific violation type
    if is_taxi_related:
        violation_type = "UNAUTHORIZED_TAXI_AD"
    elif is_sale_related:
        violation_type = "BUSINESS_AD_WITHOUT_SUBSCRIPTION"
    elif is_ad:
        violation_type = "UNAUTHORIZED_COMMERCIAL_AD"
    else:
        violation_type = "NORMAL_MESSAGE"

    primary_reason = reasons[0] if reasons else ("Reklama deb topildi" if is_ad else "Oddiy xabar")

    return ClassificationResult(
        is_ad=is_ad,
        score=score,
        reason=primary_reason,
        violation_type=violation_type,
        normalized_text=normalized,
        extracted_phones=extracted_phones,
        extracted_links=extracted_links,
    )


def classify_message(message: Message, threshold: Optional[int] = None) -> ClassificationResult:
    """Analyze Telegram Message object using the classifier."""
    text = message.text or message.caption or ""
    entities = (message.entities or []) + (message.caption_entities or [])
    return classify_text(raw_text=text, entities=entities, threshold=threshold)
