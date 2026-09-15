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


def test_job_recruitment_ads_detected():
    """Detect business advertisements for hiring, recruitment, job vacancies."""
    job_ads = [
        "Gurlan o'shga ishchi kerak",
        "Gurlan osh ga ishchi kerak",
        "Restaran ba ishchi garak ayliqni galishamiz",
        "Kafemizga oshpaz va ofitsiant kerak",
        "Do'konga sotuvchi ishga qabul qilamiz, oylik maosh yaxshi",
        "Toshkentda yangi vakansiya! Ishga taklif qilamiz",
    ]
    for ad in job_ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Job ad missed: '{ad}' (reason: {reason})"


def test_casual_pm_mention_not_flagged():
    """Ensure casual 'Lichkaga yozing' without ad context is NOT treated as an ad."""
    casual_pm = [
        "Lichkaga yozing",
        "Menga lichkaga yozing",
        "Bo'pti, lichkaga yoz",
    ]
    for msg in casual_pm:
        is_ad, reason = is_ad_text(msg)
        assert not is_ad, f"Casual PM falsely flagged as ad: '{msg}' (reason: {reason})"


def test_digital_services_and_taxi_routes_ads_detected():
    """Detect digital services, website creation, invitation sites, and short taxi ads."""
    ads = [
        "Taxsi toshkenga arzon",
        "Kimga kerak bolsa yozsin",
        "To'yga taklifnoma kerakmi? Siz uchun zamonaviy va chiroyli taklifnoma-sayt yaratib beramiz! Narxlar 150 000 so'mdan boshlanadi. Batafsil ma'lumot uchun lichkaga yozing!",
        "Sifatli sayt kerak bo'lsa, bizga murojaat qiling! Biz biznes, portfolio... saytlarni yaratamiz. Buyurtma berish uchun DM ga yozing.",
        "MAXSUS TAKLIF! To'yingiz uchun oddiy qog'oz taklifnoma o'rniga zamonaviy elektron taklifnoma-sayt yarating. Batafsil ma'lumot uchun yozing.",
        "To'y uchun zamonaviy taklifnoma-sayt kerakmi? DM ga yozing.",
        "Taklifnoma-sayt qilamiz",
    ]
    for ad in ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Digital service / taxi ad missed: '{ad}' (reason: {reason})"


def test_russian_and_uzbek_group_spam_ads_detected():
    """Detect Russian and Uzbek commercial ads (clothes, repairs, courses, channels, PM prices)."""
    spam_ads = [
        "Кто хочет заказать недорогую одежду — пишите.",
        "Такси по городу. Заказ в Telegram.",
        "Yangi kiyimlar keldi Narxlari hamyonbop. Yetkazib berish mavjud.",
        "Kompyuter va noutbuklarni ta'mirlash xizmati",
        "Ingliz tili kurslariga qabul boshlandi Batafsil ma'lumot uchun yozing.",
        "Kimga ish kerak? Onlayn ishlash imkoniyati mavjud.",
        "Qiziqqanlar lichkaga yozsin.",
        "Batafsil ma'lumot lichkada.",
        "Narxi lichkada.",
        "Buyurtma uchun yozing.",
        "Kimga kerak bo'lsa, yozib qo'ying.",
        "Kanalimizga obuna bo'ling @example",
        "Telegram kanalimizda barcha ma'lumotlar bor.",
        "Assalomu alaykum, kimga kerak bo'lsa lichkaga yozsin.",
    ]
    for ad in spam_ads:
        is_ad, reason = is_ad_text(ad)
        assert is_ad, f"Group spam ad missed: '{ad}' (reason: {reason})"


def test_reported_speech_and_commercial_inquiries_not_flagged():
    """Ensure reported speech, inquiries about discounts/courses, and seeker questions are NOT flagged as ads."""
    inquiries = [
        # Video 1: Reported speech questioning about discounts/promotions
        "Bugun barcha mahsulotlarga chegirmada dedimi aksiya muddati cheklangan dedi",
        # Video 2: Resident asking where to write/apply for courses
        "Ingliz tili kurslariga qabul boshlandi dedi Batafsil ma'lumotni uchun qayerga yozay yozing.",
        # General questions about promotions and discounts
        "Bugun chegirma bormi?",
        "Kim biladi bugun aksiya bormi?",
        "Do'konda chegirmalar rostmi?",
        "Aksiya muddati qachongacha davom etadi?",
        # General questions about courses and vacancies
        "Ingliz tili kurslari qayerda o'tiladi?",
        "Ish bormi?",
    ]
    for msg in inquiries:
        is_ad, reason = is_ad_text(msg)
        assert not is_ad, f"Inquiry falsely flagged as ad: '{msg}' (reason: {reason})"


def test_comprehensive_user_scenarios():
    """Test 10 realistic user scenarios: clients, drivers, businesses, borderline cases, and Russian language."""
    cases = [
        # 1. Clients looking for services / masters / goods (NOT ads)
        ("Menga to'y uchun yaxshi taklifnoma tayyorlaydigan usta kerak, kimni tavsiya qilasiz?", False),
        ("Kir yuvish mashinam buzilib qoldi, yaxshi remont qiladigan usta bormi?", False),
        ("Toshkentdan Samarqandga borishim kerak, bugun soat 5 larda yuradigan taksi bormi?", False),
        ("Kvartira ijaraga olmoqchiman 2 xonali Chilonzordan, kimda variant bor?", False),
        # 2. Short messages (Inquiry vs Short Ad)
        ("Taksi bormi?", False),
        ("Taksi bor", True),
        ("Sotiladi", True),
        ("Joy bor", True),
        ("Yuramiz", True),
        # 3. Product ads & craft orders
        ("Uy sharoitida pishirilgan tort va shirinliklarga buyurtma olamiz!", True),
        ("Barcha turdagi avtomobillarni sifatli moykalash va polirovka qilish xizmatimiz mavjud.", True),
        ("Ximchistka xizmati gilam va divanlarni yuvamiz", True),
        # 4. Taxi variations (Driver offers)
        ("Toshkentga taksi bor, 2 kishi olamiz", True),
        ("Toshkentga 1 kishi kerak ketamiz", True),
        ("Toshkentga bitta odam kerak ketdik", True),
        ("Такси Ташкент Бухара выезжаем сегодня в 18:00, есть свободные места.", True),
        # 5. Channel promotions
        ("Kanalimizga ulaning va eng so'nggi yangiliklardan xabardor bo'ling: @mybusiness_uz", True),
        ("Kanalimizga qo'shiling barcha yangiliklar shu yerda @yangiliklar", True),
        ("Подписывайтесь на наш телеграм канал со скидками: @skidki_tashkent", True),
        # 6. Concealed price in PM
        ("Narxini lichkada aytaman yozvorila", True),
        # 7. Borderline lost and found (has phone number, but NOT ad)
        ("Hujjatlarimni yo'qotib qo'ydim, topib olgan bo'lsa xabar bering: +998901112233", False),
        ("Потерялся щенок хаски, нашедшего просим позвонить по номеру: +998901112233", False),
    ]
    for text, expected in cases:
        is_ad, reason = is_ad_text(text)
        assert is_ad == expected, f"Scenario failed: '{text}' (expected={expected}, got={is_ad}, reason={reason})"


def test_live_group_screenshot_scenarios():
    """Verify live group screenshot messages: passenger requests vs driver ads."""
    cases = [
        # Inquiries (Passengers & Courses) -> MUST BE ALLOWED
        ("Salom taqsi nechi pul bolyapdi", False),
        ("Toshkenka taqsi bormi", False),
        ("Menga toshkenga taqsi kerak", False),
        ("Taxsi kerak", False),
        ("Ingliz tili kurslariga qabul boshlandimi qayerda borish kerak?", False),
        ("Toksi bormi", False),
        ("Taqsi toshkentga 4 odam miz", False),
        ("такси в ташкен 4 чел", False),
        # Driver Taxi Offers -> MUST BE FLAGGED AS ADS
        ("Такси в ташкен беру 4 человек", True),
        ("🔥 ТАШКЕНТ — ЕДЕМ! Есть места для 4 человек. За подробностями в ЛС.", True),
    ]
    for text, expected in cases:
        is_ad, reason = is_ad_text(text)
        assert is_ad == expected, f"Screenshot test failed: '{text}' (expected={expected}, got={is_ad}, reason={reason})"


def test_regional_live_ads_from_screenshot():
    """Verify all 16 live ad messages from user's actual group video and screenshots."""
    live_ads = [
        ("ГУЛИСТОНГО КЕТАМИЗ 777957709", True),
        ("Гурландан гулистанга кетамиз 3 одам к к 945242540", True),
        ("Gurlanda Gulistonga ketamiz 970906069", True),
        ("Гулистонга кетамиз 943150975", True),
        ("Гурланга кетамиз тел 97 607 83 83 🚘🚘🚘", True),
        ("Гулистанго кетамиз 1 одам кк +998970150521 Мансур кул", True),
        ("""Qavun bor mazali zor qavun\nKadi bol kadi keldi  mazasi ajoyib  tel 99.319.14.16 dastabki bor""", True),
        ("Гулистонга кетамиз 94 001 07 69", True),
        ("ГУРЛАНГА.. ТАКСИ.. БОР.. ЧОРИЕВ.. ТИРКАШ.. 976085665", True),
        ("Gurlandan gulistonga 1 odam karak 975129500", True),
        ("Гулстонга кетамиз 3 одам кк 501036054", True),
        ("Гурланга.. Кетамиз.. Такси.. Бор.. 976085665.. ЧОРИЕВ.. ТИРКАШ", True),
        ("Гурландан гулистонга кетамс 2одом карак 945930344", True),
        ("ГУЛИСТОНГА.ТЕЗ.КЕТАМИЗ..973630570...935630516.....3.Одам.кк", True),
        ("Urganchdan gulistongo moshinbor 2 da +998937576307", True),
        ("Гурланга 2 одам кк 880916262", True),
        ("Гурланга 2 одам карак 997154983", True),
        ("""Гурланга кетамис 2одом карак\n\nТанлавда адашманглар\n\n945930344""", True),
        ("Urganchdan Gulistanga ketamiz Soat 1 larda 975156400", True),
        ("Ассалому алейкум. Тошкентда аёл , кизларга уборка , мойкага 200 мингдан иш бор..", True),
        ("Урганга 2 одам керак хозир кетамиз", True),
        ("Гулистонга Кетамиз 2одам Керак 991250171", True),
        ("Гурландан гулистанга кетамиз 930782083", True),
        ("Гурландан гулистанга кетамиз 2 одам карак 776236252", True),
    ]
    for text, expected in live_ads:
        is_ad, reason = is_ad_text(text)
        assert is_ad == expected, f"Live ad detection failed: '{text}' (expected={expected}, got={is_ad}, reason={reason})"





