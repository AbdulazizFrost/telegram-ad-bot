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
    "kvartira arenda", "ijaraga beriladi", "ijaraga beramiz", "arenda beriladi",
    # Job recruitment and hiring (+50)
    "ishchi kerak", "ishchilar kerak", "ishchi garak", "ishchilar garak",
    "ishga olamiz", "ishga taklif", "ishga qabul", "ishga marhamat",
    "vakansiya", "vakansiyalar", "ayliqni galishamiz", "oylikni kelishamiz",
    "oylik maosh", "oshpaz kerak", "ofitsiant kerak", "sotuvchi kerak",
    # Digital products, creation, custom services (+50)
    "yaratib beramiz", "yaratamiz", "tayyorlab beramiz", "tayyorlaymiz",
    "yasab beramiz", "yasaymiz", "qilib beramiz",
    "taklifnoma-sayt", "taklifnoma sayt", "taklifnoma qilamiz", "sayt yaratamiz",
    "sayt qilamiz", "sayt yaratish", "sayt tayyorlaymiz", "sayt yaratib",
    "maxsus taklif", "qaynoq taklif", "biznes sayt",
    "somdan boshlanadi", "so'mdan boshlanadi", "narxlar boshlanadi",
    # Service calls and orders (+50)
    # Retail, goods & clothing
    "yangi kiyimlar", "hamyonbop", "narxlari hamyonbop", "yetkazib berish mavjud", "yetkazib berish bor",
    "dostavka mavjud", "dostavka bor",
    # Computer & electronics repair
    "tamirlash xizmati", "ta'mirlash xizmati", "tuzatish xizmati",
    # Courses & training
    "kurslariga qabul", "kurslarga qabul", "kurslar boshlandi", "kurslariga taklif",
    "darslar boshlandi", "oquv markazi", "o'quv markazi",
    # Remote work / online income
    "onlayn ishlash", "onlayn ish", "onlayn daromad", "kunlik daromad",
    # Channel & social promotions
    "kanalimizga obuna", "kanalga obuna", "obuna boling", "obuna bo'ling",
    "a'zo boling", "a'zo bo'ling", "kanalimizda barcha", "telegram kanalimizda",
    # Commercial PM solicitation formats
    "qiziqqanlar lichkaga", "qiziqqanlar yozsin", "qiziqqanlar dm",
    "narxi lichkada", "narx lichkada", "narxini lichkada", "narxini lichkaga", "narxi lichka",
    "bahosi lichkada", "bahosi lichkaga",
    "batafsil malumot lichkada", "batafsil ma'lumot lichkada", "malumot lichkada", "ma'lumot lichkada",
    "batafsil lichkada", "narxi lichkaga",
    "buyurtma uchun yozing", "buyurtma uchun", "buyurtma berish uchun", "buyurtma berish", "bizga murojaat qiling",
    "buyurtma olamiz", "buyurtma olaman", "zakaz olamiz", "zakaz olaman",
    "buyurtma qabul qilamiz", "zakaz qabul qilamiz", "buyurtma asosida", "zakaz asosida",
    # Service availability & cleaning
    "xizmatimiz mavjud", "xizmatlar mavjud", "xizmatlarimiz mavjud", "xizmat mavjud",
    "ximchistka", "ximchistka xizmati", "gilam yuvish", "divan yuvish",
    "polirovka", "moykalash", "avtomoyka",
    # Channel and group invitations
    "kanalimizga ulaning", "kanalga ulaning",
    "kanalimizga qo'shiling", "kanalga qo'shiling", "guruhimizga qo'shiling", "guruhga qo'shiling",
    "kanalimizga kiring", "kanalga kiring",
    "podpisivaytes na nash telegram", "podpisivaytes na nash",
    "kimga kerak bolsa yozsin", "kimga kerak bo'lsa yozsin", "kerak bolsa yozsin", "kerak bo'lsa yozsin",
    "kerak bolsa yozing", "kerak bo'lsa yozing",
    "kimga kerak bolsa yozib qoying", "kimga kerak bo'lsa, yozib qo'ying",
    "kimga kerak bolsa, yozib qoying", "kimga kerak bolsa yozib qoying",
    "yozib qoying", "yozib qo'ying",
    "kimga kerak bolsa lichkaga", "kimga kerak bo'lsa lichkaga",
    # Russian commercial phrases (normalized / transliterated)
    "zakazat", "zakaz v telegram", "nedoroguyu odejdu", "nedoroguyu",
    "pishite v lichku", "v nalichii", "podpisivaytes", "nash kanal",
    "kursi", "onlayn zarabotok", "zarabotok", "kupit nedorogo", "prodayu",
    "prodam", "prodayetsya", "tsena v ls", "podrobnosti v ls"
]

# High score signals: Driver taxi ride offers (+50 each)
HIGH_TAXI_PATTERNS = [
    "odam olamiz", "odam olaman", "odam bor olamiz",
    "pochta olamiz", "pochta olaman", "pochta yetkazamiz",
    "yuk olamiz", "yuk olaman", "yuk tashish",
    "joy bor", "bitta joy bor", "ikkita joy bor", "1 ta joy bor", "2 ta joy bor", "3 ta joy bor", "4 ta joy bor",
    "yuramiz", "yuraman", "qatnaymiz", "qatnayman",
    "salon bosh", "salon bo'sh", "zapravkada turibmiz", "zapravkadamiz",
    "moshina bor", "mashina bor", "taksi bor", "taxsi bor", "taxi bor",
    "moshinamiz bor", "mashinamiz bor",
    "yolovchi olamiz", "yo'lovchi olamiz", "kishi olamiz", "kishi olaman",
    "1 kishi kerak", "2 kishi kerak", "3 kishi kerak", "4 kishi kerak",
    "1 ta odam kerak", "2 ta odam kerak", "bitta odam kerak", "ikkita odam kerak",
    "odam kerak ketamiz", "odam kerak ketdik", "kishi kerak ketamiz", "kishi kerak ketdik", "odam garak",
    "taksistman", "taksichiman",
    # Taxi routes and cheap taxi offers (+50)
    "taxsi toshkenga", "taksi toshkenga", "taxsi toshkentga", "taksi toshkentga",
    "taxsi samarqandga", "taksi samarqandga", "taxsi gulistonga", "taksi gulistonga",
    "taksi toshkent", "taksi samarqand", "taksi buxoro", "taksi farg'ona", "taksi andijon", "taksi namangan",
    "taxsi toshkent", "taxsi samarqand", "taxsi buxoro",
    "arzon taksi", "arzon taxsi", "taxsi arzon", "taksi arzon",
    "toshkenga arzon", "toshkentga arzon", "samarqandga arzon", "gulistonga arzon",
    "taksi po gorodu", "taxsi po gorodu", "zakaz v telegram",
    "svobodnie mesta", "mesta yest", "viezjaem", "beru poputchikov"
]

# High score signals: Commercial calls-to-action & direct contact solicitation (+40 each)
HIGH_CONTACT_PATTERNS = [
    "murojaat uchun", "murojat uchun", "murojaat qiling", "murojaat:",
    "aloqa uchun", "bog'lanish uchun",
    "zakaz uchun", "buyurtma uchun", "batafsil ma'lumot uchun",
    "batafsil ma'lumot uchun yozing", "ma'lumot uchun yozing", "batafsil yozing",
    "dm ga yozing", "dmga yozing", "dm ga", "dmga", "directga", "direktga",
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

# Active seller / provider commercial offers (used to detect marketing hooks)
ACTIVE_OFFER_PATTERNS = [
    "yaratib beramiz", "yaratamiz", "tayyorlab beramiz", "tayyorlaymiz",
    "yasab beramiz", "yasaymiz", "qilib beramiz", "tamirlaymiz", "ta'mirlaymiz",
    "sotamiz", "sotaman", "yetkazib beramiz", "ishga olamiz", "ishga qabul",
    "ishga taklif", "imkoniyati mavjud",
    "buyurtma olamiz", "buyurtma olaman", "zakaz olamiz", "zakaz olaman",
    "yuvamiz", "tozalaymiz", "polirovka",
    "odam olamiz", "odam olaman", "kishi olamiz", "kishi olaman",
    "joy bor", "bitta joy bor", "ikkita joy bor",
    "taksi bor", "taxsi bor", "svobodnie mesta", "viezjaem",
    "yuramiz", "qatnaymiz", "salon bosh", "salon bo'sh", "zapravkada turibmiz",
    "taksistman", "taksichiman", "zakazat", "v nalichii", "kupit nedorogo",
    "prodayu", "prodam", "onlayn zarabotok", "onlayn ishlash", "onlayn ish",
    "onlayn daromad", "kunlik daromad"
]

# Active commercial calls-to-action directed to chat members to contact seller
ACTIVE_CTA_PATTERNS = [
    "lichkaga yozing", "lichkaga yozsin", "lichgaga yozing", "lichgaga yozsin",
    "dm ga yozing", "dmga yozing", "directga yozing", "direktga yozing",
    "murojaat qiling", "bizga murojaat qiling", "buyurtma bering",
    "buyurtma uchun yozing", "obuna bo'ling", "obuna boling",
    "kimga kerak bolsa yozsin", "kimga kerak bo'lsa yozsin",
    "kerak bolsa yozsin", "kerak bo'lsa yozsin",
    "kimga kerak bolsa yozing", "kerak bolsa yozing",
    "yozib qoying", "yozib qo'ying",
    "pishite v lichku", "pishite"
]

# First-person inquiry phrases (a user asking where/how THEY should write or apply)
FIRST_PERSON_INQUIRY_PATTERNS = [
    "qayerga yozay", "kimga yozay", "qayerga boray", "kimga murojaat",
    "qayerdan olay", "qayerdan olsam", "qayerdan topsam", "qanday qilib",
    "qayerga tolay", "qayerga to'lay", "qayerga yozsam", "qayerga murojaat qilay"
]

# Interrogative words and reported speech particles in Uzbek/Russian
INTERROGATIVE_WORDS = [
    "dedimi", "eshitdingizmi", "eshitdizmi", "bilasizmi", "bilasilarmi",
    "rostmi", "to'g'rimi", "togrimi", "haqiqatmi", "shunaqami", "bormi", "bomi",
    "bormikin", "bormikan", "rostmikin", "rostmikan", "kerakmi", "mumkinmi",
    "bo'ladimi", "boladimi", "emasmi", "yuradimi", "boshlandimi", "ochildimi",
    "beriladimi", "qilinadimi", "qiladimi", "keladimi", "ketadimi",
    "aksiyami", "chegirmami",
    "deb eshitdim", "deb aytishdi", "deb yozishibdi", "deyishyapti", "deyapti"
]

