import re

# High score signals: Explicit sales, commercial offers (+50 each)
HIGH_SALE_PATTERNS = [
    "sotiladi", "sotaman", "sotamiz", "sotuvda", "sotib oling", "sotiladi!",
    "optom", "ulgurji", "arzon narxda", "eng arzon", "narxi arzon",
    "aksiya", "chegirma", "skidka", "shoshiling aksiya",
    "buyurtma bering", "buyurtma qabul", "zakaz oling", "zakaz bering",
    "yetkazib berish", "yetkazib beramiz", "yetkazib berish bepul", "yetkazib berish tekin", "dostavka bepul",
    "dostavka tekin", "dostavka xizmati", "dostavka",
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
    "yangi kiyimlar", "kiyimlari kelgan", "kiyimlar kelgan", "tovarlar keldi", "tovarlar kelgan", "tovar keldi", "tovar kelgan",
    "hamyonbop", "narxlari hamyonbop", "yetkazib berish mavjud", "yetkazib berish bor",
    "dostavka mavjud", "dostavka bor",
    # Graphic design & media creation (+50)
    "dizayn qilaman", "dizayn qilamiz", "dizayn xizmati", "bannerlar dizayn", "banner dizayn",
    "post va bannerlar", "video oladigan", "rasmga oladigan",
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
    "prodam", "prodayetsya", "tsena v ls", "podrobnosti v ls",
    "rasprodaja", "samie nizkie tseni", "nizkie tseni", "deshevo",
    "besplatnaya dostavka", "dostavka besplatno", "dostavka besplatnaya",
    "v chest otkritiya", "kafe otkrilos",
    "remont kvartir", "remont ofisov", "pod klyuch",
    "stroitelnaya kompaniya", "postroit dom", "postroim dom",
    "uyutnaya gostinitsa", "uyutnaya gostinica", "gostinitsa", "gostinica",
    "broniruyte", "bronirovanie",
    "na zakaz", "dlya zakaza", "zakaz po telefonu",
    "domashnie torti", "torti na zakaz",
    "moyka i polirovka", "ximchistka salona",
    "salon krasoti", "manikyur i pedikyur",
    "zvonite pryamo seychas", "zvonite v lyuboe vremya",
    "uspeyte zapisatsya", "zapisivaytes",
    # Regional delivery dialects & agricultural food sales
    "dastabki bor", "dastabka bor", "dastavka bor", "dastafka bor",
    "dastabki", "dastabka", "dastavka", "dastafka",
    "qavun bor", "qovun bor", "tarvuz bor", "kadi bor", "qovoq bor", "kadi keldi",
    # Job recruitment / Hiring ads (+50)
    "ish bor", "ish mavjud", "ish taklif", "uborka", "kunlik ish", "200 mingdan",
    "trebuyutsya", "trebuetsya", "ischem", "na postoyannuyu rabotu",
    "rabota v tashkente", "rabota v toshkente", "rabota tashkent", "rabota toshkent",
    "yejednevnaya oplata", "ejednevnaya oplata", "oplata yejednevnaya", "oplata ejednevnaya", "oplata visokaya",
    "srochno trebuetsya", "srochno trebuyutsya", "novvoy kerak", "usta kerak", "haydovchi kerak",
    "kuryer kerak", "posudomoyka kerak", "posudomoyshitsa", "kassir kerak",
    # Trade services and business services (+50)
    "santexnika", "santexnik", "elektrik", "konditsioner", "konditsioner tamirlash",
    "kompyuter tuzatish", "kompyuter tamirlash", "noutbuklarni tuzatish",
    "svarka xizmati", "svarka", "avtoelektrik", "buxgalteriya",
    "gruzoperevozki", "pereezdi", "gruzchiki", "labo bor", "yuk tashish",
    "xizmati", "xizmatlari", "xizmatlar", "uslugi", "servis",
    # Commercial goods & property (+50)
    "goshti bor", "go'shti bor", "gosht bor", "go'sht bor", "yangi soyilgan",
    "arzon kiyimlar", "dokonimizga marhamat", "kupite nedorogo", "kupite",
    "arenda kvartira", "kvartira arenda", "arenda", "kurslarimizga qabul", "qabul boshlandi",
    # Agricultural / seasonal field labor & harvesting (+50)
    "sholi yer bor", "sholi bor", "sholi o'rish", "sholi orish", "sholi o'romon", "sholi oromon",
    "o'roq o'rish", "oroq orish", "o'roq o'romon", "oroq oromon", "o'romon deganlar", "oromon deganlar",
    "o'romon", "oromon", "qo'l o'roq", "qol oroq", "o'roqchilar kerak", "oroqchilar kerak", "o'roqchi kerak",
    "paxta terish", "terimchilar kerak", "paxtakor kerak",
    "mardikor kerak", "chopiq bor", "yagana bor",
    "deganlar bo'lsa tel", "deganlar bolsa tel", "deganlar bo'lsa lichkaga", "deganlar bolsa lichkaga",
    "bo'lsa tel", "bolsa tel", "deganlar bo'lsa", "deganlar bolsa"
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
    "moshinamiz bor", "mashinamiz bor", "moshinbor", "moshin bor", "mashinabor", "mashinbor",
    "moshinabor", "moshinabor samarqandga", "moshinabor toshkenga",
    "yolovchi olamiz", "yo'lovchi olamiz", "kishi olamiz", "kishi olaman",
    "yolovchilar kerak", "yo'lovchilar kerak", "yolovchi kerak", "yo'lovchi kerak",
    "taksi buyurtma", "buyurtma qilish", "zakaz taksi", "taksi zakaz",
    "ischete nadejnoe taksi", "nadejnoe taksi", "ischete taksi",
    "taksi v samarkand", "taksi v tashkent", "taksi v buxaru",
    "1 kishi kerak", "2 kishi kerak", "3 kishi kerak", "4 kishi kerak",
    "1 ta odam kerak", "2 ta odam kerak", "bitta odam kerak", "ikkita odam kerak",
    "1 odam kerak", "2 odam kerak", "3 odam kerak", "4 odam kerak",
    "1 odam karak", "2 odam karak", "3 odam karak", "4 odam karak",
    "1 kishi karak", "2 kishi karak", "3 kishi karak", "4 kishi karak",
    "2odom karak", "2одом карак", "3одам карак", "2 одам карак", "3 одам карак",
    "odam kerak ketamiz", "odam kerak ketdik", "kishi kerak ketamiz", "kishi kerak ketdik", "odam garak",
    "1 odam kk", "2 odam kk", "3 odam kk", "4 odam kk",
    "1 odam k k", "2 odam k k", "3 odam k k", "4 odam k k",
    "1 kishi kk", "2 kishi kk", "3 kishi kk", "4 kishi kk",
    "odam kk", "kishi kk", "odam k k", "kishi k k",
    "xozir ketamiz", "hozir ketamiz", "tez ketamiz",
    "taksistman", "taksichiman",
    # Regional routes & ketamiz offers
    "gulistonga ketamiz", "gulistongo ketamiz", "gulistanga ketamiz", "gulstonga ketamiz",
    "gurlanga ketamiz", "gurlango ketamiz", "gurlandan gulistanga", "gurlandan gulistonga",
    "toshkentga ketamiz", "toshkengo ketamiz", "samarqandga ketamiz", "buxoroga ketamiz",
    "urganga ketamiz", "urganga", "gurlanga ketamis", "gulistonga ketams", "gulistonga ketamis",
    "toshkentga ketatovginlar borma", "toshkentga ketatovgonlar borma",
    "toshkentga ketatovginlar", "toshkentga ketatovgonlar",
    "toshkentga ketadiganlar bormi", "toshkentga ketadiganlar",
    "gurlanga ketatovginlar borma", "gurlanga ketatovgonlar borma",
    "ketatovginlar borma", "ketatovgonlar borma", "ketatovginlar", "ketatovgonlar",
    # Taxi routes and cheap taxi offers (+50)
    "taxsi toshkenga", "taksi toshkenga", "taxsi toshkentga", "taksi toshkentga",
    "taxsi samarqandga", "taksi samarqandga", "taxsi gulistonga", "taksi gulistonga",
    "taksi toshkent", "taksi samarqand", "taksi buxoro", "taksi farg'ona", "taksi andijon", "taksi namangan",
    "taxsi toshkent", "taxsi samarqand", "taxsi buxoro",
    "taksi tashkent", "taxsi tashkent", "taksi samarkand", "taxsi samarkand",
    "taksi buxara", "taxsi buxara",
    "luchshee taksi", "taksi do", "taxsi do",
    "viezd utrom", "viezd vecherom", "viezd v", "budu viezjat", "viezd",
    "viyezd utrom", "viyezd vecherom", "viyezd v", "budu viyezjat", "viyezd",
    "salon pustoy", "pustoy salon",
    "berem lyudey", "berem passajirov", "berem poputchikov", "berem posilki",
    "berem chelovek", "berem chel",
    "arzon taksi", "arzon taxsi", "taxsi arzon", "taksi arzon",
    "toshkenga arzon", "toshkentga arzon", "samarqandga arzon", "gulistonga arzon",
    "taksi po gorodu", "taxsi po gorodu", "zakaz v telegram",
    "svobodnie mesta", "mesta yest", "viezjaem", "beru poputchikov",
    "est mesta", "yest mesta", "mesta dlya", "ostalos mesta", "ostalos mesto",
    "svobodno mesta", "svobodno mesto", "mesta est",
    "mesta svobodno", "mesto svobodno", "svobodnix mesta", "svobodnix mest", "svobodnoe mesto",
    "est 2 svobodnix mesta", "est 3 svobodnix mesta", "est 1 svobodnoe mesto",
    "edem v tashkent", "edem v samarkand", "edem v buxaru", "edem v ferganu",
    "tashkent edem", "samarkand edem", "buxara edem",
    "edu v tashkent"
]

# High score signals: Commercial calls-to-action & direct contact solicitation (+40 each)
HIGH_CONTACT_PATTERNS = [
    "murojaat uchun", "murojat uchun", "murojaat qiling", "murojaat:",
    "aloqa uchun", "bog'lanish uchun",
    "zakaz uchun", "buyurtma uchun", "batafsil ma'lumot uchun",
    "batafsil ma'lumot uchun yozing", "ma'lumot uchun yozing", "batafsil yozing",
    "dm ga yozing", "dmga yozing", "dm ga", "dmga", "directga", "direktga",
    "za podrobnostyami v ls", "za podrobnostyami v lichku",
    "voprosi v ls", "voprosi v lichku", "vse voprosi v ls",
    "pisat v ls", "pisat v lichku",
    "zvonite pryamo seychas", "zvonite po telefonu", "zvonit po nomeru", "zvonite dlya zakaza",
    "zvonite nam", "zvonite", "qo'ng'iroq qiling", "qongiroq qiling", "tel qiling", "aloqaga chiqing",
    "24/7", "kun-u tun", "admin:", "zakaz:", "tel:", "telefon:", "nomer:"
]

# Medium score signals: Commercial & transit keywords (+15 to +25 each)
MEDIUM_COMMERCIAL_KEYWORDS = [
    "narx", "narxi", "som", "so'm", "dollar", "usd", "sum",
    "kafe", "restoran", "magazin", "dokon", "do'kon",
    "taksi", "taxsi", "taxi", "taksis", "taxsis", "taksist", "taxsist", "taksichi", "taxsichi",
    "mashina", "moshina", "avto", "telefon", "remont", "usta",
    "tovar", "mahsulot", "kartoshka", "go'sht", "gosht", "goshti", "go'shti", "meva",
    "odam", "joy", "pochta", "yuk", "ketsa", "borsa", "ketadi", "boradi",
    "ketamiz", "boramiz", "yuramiz", "kk",
    "dastabka", "dastabki", "dastavka", "dastafka",
    "qavun", "qovun", "tarvuz", "kadi",
    "ish bor", "uborka", "karak", "moshinbor", "moshinabor", "urganga", "ketams", "ketamis",
    "sholi", "yer bor", "o'roq", "oroq", "o'romon", "oromon", "paxta", "mardikor", "chopiq", "terimchi", "tel"
]

# Negative score signals: Inquiries, casual questions, recommendations (-30 to -45 each)
QUESTION_PATTERNS = [
    "kim", "kimda", "kimga", "kimdan", "kim boryapti", "kim bor", "kim ketyapti",
    "qayerda", "qayerga", "qayerdan", "qattay", "qatta",
    "qancha", "qanchadan", "necha", "nechchi", "nechidan",
    "bormi", "bormikin", "bormikan", "bomi", "bormi?",
    "bilasizmi", "bilasilarmi", "biladigan", "biladiganlar", "bilganlar",
    "aytvorilar", "aytvorin", "aytib yuboring", "maslahat bering",
    "qaysi", "qanaqa", "qanday", "kerak edi", "kerakmi", "qidiryapman",
    "kto", "gde", "kuda", "otkuda", "skolko", "pochem",
    "kakoy", "kakaya", "kakoe", "kakie", "kakom", "kakuyu",
    "kogda", "pochemu", "zachem", "kak",
    "podskajite", "posovetuyte", "porekomenduyte",
    "est li", "bivaet li", "mojno li", "znaet li"
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
    "taksi bor", "taxsi bor", "svobodnie mesta", "est mesta", "yest mesta", "mesta dlya", "viezjaem",
    "yuramiz", "qatnaymiz", "salon bosh", "salon bo'sh", "zapravkada turibmiz",
    "taksistman", "taksichiman", "zakazat", "v nalichii", "kupit nedorogo",
    "prodayu", "prodam", "onlayn zarabotok", "onlayn ishlash", "onlayn ish",
    "onlayn daromad", "kunlik daromad",
    "kurslarimizga qabul", "qabul boshlandi", "dokonimizga marhamat", "do'konimizga marhamat",
    "moshinabor", "yolovchilar kerak", "yo'lovchilar kerak", "zvonite nam",
    "sholi yer bor", "sholi bor", "o'roq o'rish", "o'romon", "oromon", "qo'l o'roq", "qol oroq", "o'roq o'romon",
    "ketatovginlar borma", "ketatovgonlar borma", "toshkentga ketatovginlar"
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
    "deganlar bo'lsa tel", "deganlar bolsa tel", "deganlar bo'lsa lichkaga", "deganlar bolsa lichkaga",
    "bo'lsa tel", "bolsa tel", "deganlar bo'lsa", "deganlar bolsa",
    "za podrobnostyami v ls", "za podrobnostyami v lichku",
    "voprosi v ls", "voprosi v lichku", "vse voprosi v ls",
    "pisat v ls", "pisat v lichku",
    "pishite v lichku", "pishite"
]

# First-person inquiry phrases (a user asking where/how THEY should write or apply)
FIRST_PERSON_INQUIRY_PATTERNS = [
    "qayerga yozay", "kimga yozay", "qayerga boray", "kimga murojaat",
    "qayerdan olay", "qayerdan olsam", "qayerdan topsam", "qanday qilib",
    "qayerga tolay", "qayerga to'lay", "qayerga yozsam", "qayerga murojaat qilay",
    "xochu zakazat", "xochu kupit", "ishu", "ishem",
    "nujno doexat", "nujno uexat", "nujen master",
    "nujno otremontirovat", "nujna mashina", "nujno taksi",
    "kto mojet zabrat", "kto mojet podvezti", "kto edet"
]

# Lost & found community announcements (should not be flagged as ads even with phone numbers)
LOST_AND_FOUND_PATTERNS = [
    "poteryalsya", "poteryalas", "poteryali", "poteryan", "poteryana", "poteryani",
    "uteryan", "uteryana", "uteryani", "propal", "propala", "propali",
    "nayden", "naydena", "naydeni", "nashli", "nashel",
    "kto videl", "kto nashel", "kto poteryal",
    "ostavili v", "ostavil v", "zabil v", "zabili v", "voznagrajdenie",
    "yoqolgan", "yo'qolgan", "yoqotib", "yo'qotib", "yoqotildi", "yo'qotildi",
    "yoqotilgan", "yo'qotilgan", "topgan odam", "topganga",
    "tushib qolibdi", "tushib qolgan",
    "topib olindi", "topib oldim", "topib olingan", "topgan odamga",
    "mukofot bor", "suyunchi bor", "suyunchisi bor",
    "unutib qoldiribman", "esdan chiqibdi", "qolib ketibdi"
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

