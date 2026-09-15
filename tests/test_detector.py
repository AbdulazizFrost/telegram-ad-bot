import pytest
from app.services.advertisement_detector import is_ad_text


def test_regular_questions_not_flagged():
    """Requirement 1: Regular questions must NOT be considered ads."""
    questions = [
        "Kim kartoshka narxini biladi?",
        "Bugun Samarqandga kim boryapti?",
        "Yaxshi usta bormi?",
        "Avtosalonlarda Gentra bormi?",
        "Kimda taksistning nomeri bor?",
        "Telefon narxi qancha?",
        "Qaysi kafeda ovqat yaxshi?",
        "Kimda yaxshi taksistning nomeri bor?",
        "Buxoroga poezd qachon yuradi?",
        "Bolalar uchun qaysi bog'cha yaxshi, maslahat bering?",
    ]
    for q in questions:
        is_ad, reason = is_ad_text(q)
        assert not is_ad, f"Question falsely flagged as ad: '{q}' (reason: {reason})"


def test_casual_conversation_not_flagged():
    """Requirement 2: Normal conversation and friendly chats must remain."""
    chats = [
        "Assalomu alaykum hammaga! Kuningiz xayrli o'tsin.",
        "Rahmat kattakon, yordam berganingiz uchun!",
        "Ertaga havo qanaqa bo'larkan, yomg'ir yog'maydimi?",
        "Ha, men ham o'sha yerda edim kecha.",
        "Vaalaykum assalom, qalesiz do'stim?",
    ]
    for c in chats:
        is_ad, reason = is_ad_text(c)
        assert not is_ad, f"Casual chat falsely flagged as ad: '{c}' (reason: {reason})"


def test_explicit_commercial_ads_detected():
    """Requirement 3: Commercial ads must be detected."""
    ads = [
        "Sotiladi! Yangi iPhone 15 Pro Max, karobka dokument, narxi arzon.",
        "Kafemizda yangi aksiya! Buyurtma bering, yetkazib berish bepul!",
        "Optom kiyimlar Toshkentdan! Arzon narxda buyurtma qabul qilamiz.",
        "Bizning telegram kanalimizga obuna bo'ling: https://t.me/arzondokon",
        "Kvartira arenda beriladi, 2 xona shinam, tel: +998901234567",
        "Usta xizmati! Kir yuvish mashinalarini arzon ta'mirlaymiz.",
    ]
    for ad in ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Explicit commercial ad missed: '{ad}'"


def test_taxi_driver_offers_detected():
    """Requirement 4: Taxi driver ride offers must be detected."""
    taxi_ads = [
        "Toshkent - Samarqand mashina bor, 2 ta joy bor yuramiz!",
        "Bugun kechga Toshkentdan Buxoroga odam olamiz va pochta olamiz.",
        "Men taksistman, Samarqandga odam olaman. Tel: +998901234567",
        "Zapravkadamiz, 1 ta odam bo'lsa darhol yuramiz!",
        "Cobalt mashinam bor, Farg'onaga qatnaymiz har kuni.",
    ]
    for ad in taxi_ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Taxi offer missed: '{ad}'"


def test_question_vs_offer_nuance():
    """
    Carefully distinguish:
    - User looking for taxi (Question) -> NOT AD
    - Driver offering taxi (Commercial offer) -> AD
    """
    user_question = "Kimda yaxshi taksistning nomeri bor?"
    driver_offer = "Men taksistman, Samarqandga odam olaman. Tel: +998901234567"

    is_ad_q, _ = is_ad_text(user_question)
    is_ad_o, _ = is_ad_text(driver_offer)

    assert not is_ad_q, "User question was flagged as ad"
    assert is_ad_o, "Driver offer was NOT flagged as ad"


# =========================================================================
# ANTI-EVASION TESTS: Spaced words, separators, phone masks, spaced URLs
# =========================================================================

def test_spaced_words_evasion_detected():
    """Detect ads using spaced letters (t a k s i, т а к с и, s o t i l a d i)."""
    evasion_ads = [
        "т а к с и Toshkent Samarqand 2 ta joy bor",
        "t a k s i xizmati Toshkentga yuramiz",
        "s o t i l a d i yangi iphone narxi arzon",
        "t a x s i bor toshkentga odam olamiz",
    ]
    for ad in evasion_ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Spaced words evasion missed: '{ad}' (reason: {reason})"


def test_word_separators_evasion_detected():
    """Detect ads using separators like dashes/dots/special chars (ТАК-СИ, tak.si)."""
    evasion_ads = [
        "ТАК-СИ xizmati! Toshkentga yuramiz 2 ta joy",
        "tak.si Toshkent Samarqand mashina bor",
        "sotiladi!!! yangi telefon karobka bor",
        "s-o-t-i-l-a-d-i arzon narxda",
    ]
    for ad in evasion_ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Word separator evasion missed: '{ad}' (reason: {reason})"


def test_spaced_and_masked_phone_numbers_detected():
    """Detect ads with spaced, hyphenated, dotted, and emoji-masked phone numbers."""
    evasion_ads = [
        # Spaced phone
        "Toshkentga taksi tel: 9 0 1 2 3 4 5 6 7",
        "Mashina bor Toshkentga: + 9 9 8 9 0 1 2 3 4 5 6 7",
        # Hyphenated & dotted phone
        "Taksi xizmati qatnaymiz: 90-123-45-67",
        "Toshkentga odam olamiz tel 90.123.45.67",
        # Emoji digits phone
        "Toshkent Samarqand mashina bor: 9️⃣0️⃣1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣",
        "Taksi: 9️⃣0️⃣-1️⃣2️⃣3️⃣-4️⃣5️⃣-6️⃣7️⃣",
    ]
    for ad in evasion_ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Phone evasion missed: '{ad}' (reason: {reason})"


def test_spaced_urls_and_mentions_detected():
    """Detect ads with spaced domain names or broken link structures."""
    evasion_ads = [
        "Bizning kanalimizga kiring: t.me / arzondokon",
        "Obuna bo'ling: https:// t . me / sotuvlar",
        "Telegram kanalimiz: t.me / rasmiy_kanal",
    ]
    for ad in evasion_ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Spaced link evasion missed: '{ad}' (reason: {reason})"


def test_pm_solicitation_taxi_detected():
    """Detect typical group evasion: 'Gulistonga taxsi kim ketsa lichgaga yozsin'."""
    ads = [
        "Gulustonga taxsi kim ketsa lichgaga yozsin",
        "Toshkentga kim borsa lichkaga yozsin 2 ta joy bor",
        "Taksistman lichkaga yozinglar",
    ]
    for ad in ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"PM solicitation ad missed: '{ad}' (reason: {reason})"


def test_ordinary_numbers_and_times_not_flagged():
    """Ensure normal numbers, times, years, and quantities are NOT mistaken for phones or ads."""
    normal_messages = [
        "Bugun soat 19:00 da yig'ilamiz",
        "2026 yilda yangi stadion ochiladi",
        "Avtobus 15 daqiqada keladi",
        "Men 90 yoshli buvimnikiga ketayapman",
        "Dars soat 09:30 da boshlanadi",
        "Uchrashuv 14:00 da bo'ladi",
        "Magazinda 5000 so'm qolib ketibdi",
    ]
    for msg in normal_messages:
        is_ad, reason = is_ad_text(msg)
        assert not is_ad, f"Ordinary number falsely flagged as ad: '{msg}' (reason: {reason})"
