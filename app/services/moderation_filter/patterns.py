import re

# High score signals: Explicit sales, commercial offers (+50 each)
HIGH_SALE_PATTERNS = [
    "sotiladi", "sotaman", "sotamiz", "sotuvda", "sotib oling", "sotiladi!",
    "optom", "ulgurji", "arzon narxda", "eng arzon", "narxi arzon",
    "aksiya", "chegirma", "skidka", "shoshiling aksiya",
    "buyurtma bering", "buyurtma qabul", "zakaz oling", "zakaz bering",
    "yetkazib berish bepul", "yetkazib berish tekin", "dostavka bepul",
    "dostavka tekin", "dostavka xizmati", "yetkazib beramiz",
    "xizmat korsatamiz", "xizmat ko'rsatamiz", "xizmatlarimiz", "xizmat korsatish",
    "usta xizmati", "remont qilamiz", "remont xizmati", "tamirlaymiz", "ta'mirlaymiz",
    "manikyur", "pedikyur", "narashivaniye",
    "kvartira arenda", "ijaraga beriladi", "ijaraga beramiz", "arenda beriladi"
]

# High score signals: Driver taxi ride offers (+50 each)
HIGH_TAXI_PATTERNS = [
    "odam olamiz", "odam olaman", "odam bor olamiz",
    "pochta olamiz", "pochta olaman", "pochta yetkazamiz",
    "yuk olamiz", "yuk olaman", "yuk tashish",
    "joy bor", "bitta joy bor", "ikkita joy bor", "1 ta joy bor", "2 ta joy bor", "3 ta joy bor", "4 ta joy bor",
    "yuramiz", "yuraman", "qatnaymiz", "qatnayman",
    "salon bosh", "salon bo'sh", "zapravkada turibmiz", "zapravkadamiz",
    "moshina bor", "mashina bor", "yolovchi olamiz", "yo'lovchi olamiz",
    "taksistman", "taksichiman"
]

# High score signals: Commercial calls-to-action & direct contact solicitation (+40 each)
HIGH_CONTACT_PATTERNS = [
    "murojaat uchun", "murojat uchun", "murojaat qiling", "murojaat:",
    "lichkaga yozing", "lichkaga o'ting", "lichkaga chiqing", "lichkaga yozsin",
    "lichgaga yozing", "lichgaga yozsin", "lichgaga chiqing",
    "lsga yozing", "lsga yozsin", "aloqa uchun", "bog'lanish uchun",
    "zakaz uchun", "buyurtma uchun", "batafsil ma'lumot uchun",
    "24/7", "kun-u tun", "admin:", "zakaz:", "tel:", "telefon:", "nomer:"
]

# Medium score signals: Commercial & transit keywords (+15 to +25 each)
MEDIUM_COMMERCIAL_KEYWORDS = [
    "narx", "narxi", "som", "so'm", "dollar", "usd", "sum",
    "kafe", "restoran", "magazin", "dokon", "do'kon",
    "taksi", "taxsi", "taxi", "taksis", "taxsis", "taksist", "taxsist", "taksichi", "taxsichi",
    "mashina", "moshina", "avto", "telefon", "remont", "usta",
    "tovar", "mahsulot", "kartoshka", "go'sht", "gosht", "meva",
    "odam", "joy", "pochta", "yuk", "ketsa", "borsa", "ketadi", "boradi"
]

# Negative score signals: Inquiries, casual questions, recommendations (-30 to -45 each)
QUESTION_PATTERNS = [
    "kim", "kimda", "kimga", "kimdan", "kim boryapti", "kim bor", "kim ketyapti",
    "qayerda", "qayerga", "qayerdan", "qattay", "qatta",
    "qancha", "qanchadan", "necha", "nechchi", "nechidan",
    "bormi", "bormikin", "bormikan", "bomi", "bormi?",
    "bilasizmi", "bilasilarmi", "biladigan", "biladiganlar", "bilganlar",
    "aytvorilar", "aytvorin", "aytib yuboring", "maslahat bering",
    "qaysi", "qanaqa", "qanday", "kerak edi", "kerakmi", "qidiryapman"
]

# Inquiry questions asking for recommendations / info (-40 each)
RECOMMENDATION_QUESTIONS = [
    "kimda ... bor", "kim ... biladi", "qaysi ... yaxshi", "qayerda arzon",
    "usta bormi", "taksist bormi", "taksi bormi", "nomeri bormi", "nomeri bor"
]
