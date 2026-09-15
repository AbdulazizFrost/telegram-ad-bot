"""
Centralized Uzbekistan Locations Registry.
Covers all 14 administrative divisions:
12 Regions (Viloyatlar) + Tashkent City + Republic of Karakalpakstan.
Includes all districts (tumans), major cities, towns, and their colloquial / Russian / dialect variants.
"""

from typing import Dict, List, Set

# Master dictionary: Standard Name -> List of aliases/stems (in normalized Latin)
# All entries must be lowercase, normalized Latin characters.
UZBEKISTAN_LOCATIONS: Dict[str, List[str]] = {
    # --- Toshkent Shahri (Tashkent City) & Districts ---
    "toshkent": [
        "toshkent", "toshkeng", "tosh", "tashkent", "tash",
        "yunusobod", "yunusabad", "chilonzor", "chilanzar", "chilonzar",
        "mirzo ulugbek", "mirzo ulug'bek", "yakkasaroy", "yakkasaray",
        "shayxontohur", "shayhantohur", "shayxontoxur", "olmazor", "almazar",
        "sergeli", "sergili", "bektemir", "yashnobod", "yashnabad",
        "uchtepa", "mirobod", "mirabad", "yangihayot", "yangihayot"
    ],
    # --- Toshkent Viloyati ---
    "chirchiq": ["chirchiq", "chirchik", "chircik"],
    "angren": ["angren"],
    "olmaliq": ["olmaliq", "olmalik", "almalyk", "almalik"],
    "bekobod": ["bekobod", "bekabad", "begovat"],
    "yangiyol": ["yangiyol", "yangiyo'l", "yangiyul"],
    "ohangaron": ["ohangaron", "axangaran", "ahangaran"],
    "nurafshon": ["nurafshon", "nurafshan", "toytepa", "to'ytepa"],
    "bostonliq": ["bostonliq", "bo'stonliq", "bostanlyk", "gazalkent", "g'azalkent", "chimyon", "chorvoq", "charvak"],
    "zangiota": ["zangiota", "zangiata", "eshonguzar"],
    "qibray": ["qibray", "kibray"],
    "parkent": ["parkent"],
    "piskent": ["piskent"],
    "chinoz": ["chinoz", "chinaz"],
    "ortachirchiq": ["ortachirchiq", "o'rtachirchiq", "srednechirchik"],
    "yuqorichirchiq": ["yuqorichirchiq", "verxnechirchik"],
    "quyichirchiq": ["quyichirchiq", "niznechirchik", "dostobod"],
    "boka": ["boka", "bo'ka", "buka"],

    # --- Samarqand Viloyati ---
    "samarqand": ["samarqand", "samarkand", "samar"],
    "kattaqorgon": ["kattaqorgon", "kattaqo'rg'on", "kattakurgan"],
    "urgut": ["urgut"],
    "oqdaryo": ["oqdaryo", "akdarya", "loish"],
    "bulungur": ["bulungur", "bulung'ur"],
    "jomboy": ["jomboy", "jambay"],
    "ishtixon": ["ishtixon", "ishtixtan"],
    "payariq": ["payariq", "payarik", "chelalek"],
    "pastdargom": ["pastdargom", "pastdarg'om", "juma"],
    "paxtachi": ["paxtachi", "ziyodin"],
    "toyloq": ["toyloq", "toyloq"],
    "qoshrabot": ["qoshrabot", "qo'shrabot", "kushrabat"],
    "narpay": ["narpay", "oqtosh", "oqtosh"],

    # --- Buxoro Viloyati ---
    "buxoro": ["buxoro", "buxara", "bukhara"],
    "kogon": ["kogon", "kagan"],
    "gijduvon": ["gijduvon", "g'ijduvon", "gijduvan"],
    "vobkent": ["vobkent", "vabkent"],
    "jondor": ["jondor"],
    "qorakol": ["qorakol", "qorako'l", "karakul"],
    "qorovulbozor": ["qorovulbozor", "karaulbazar"],
    "olot": ["olot", "alat"],
    "peshku": ["peshku"],
    "romitan": ["romitan"],
    "shofirkon": ["shofirkon", "shafirkan"],

    # --- Xorazm Viloyati ---
    "urganch": ["urganch", "urgench", "urganj"],
    "xiva": ["xiva", "khiva"],
    "gurlan": ["gurlan", "gurlon"],
    "xonqa": ["xonqa", "xanqa", "xanka"],
    "shovot": ["shovot", "shavat"],
    "bogot": ["bogot", "bog'ot", "bagat"],
    "hazorasp": ["hazorasp", "xazorasp", "hazarasp"],
    "yangibozor": ["yangibozor", "yangibazar"],
    "qoshkopir": ["qoshkopir", "qo'shko'pir", "koshkupir"],
    "yangiariq": ["yangiariq", "yangiariq"],
    "tuproqqala": ["tuproqqala", "tuproqqal'a", "pitnak"],

    # --- Andijon Viloyati ---
    "andijon": ["andijon", "andijan"],
    "asaka": ["asaka", "assaka"],
    "xonobod": ["xonobod", "xanabad"],
    "shahrixon": ["shahrixon", "shaxrixon", "shaxrixan", "shaxrihon"],
    "baliqchi": ["baliqchi", "balikchi"],
    "boz": ["boz", "bo'z", "bostan", "bo'ston"],
    "buloqboshi": ["buloqboshi", "bulakbashi"],
    "izboskan": ["izboskan", "poytug", "poytug'"],
    "jalaquduq": ["jalaquduq", "jalolquduq"],
    "marhamat": ["marhamat", "marxamat"],
    "oltinkol": ["oltinkol", "oltinko'l"],
    "paxtaobod": ["paxtaobod", "paxtaabad"],
    "qorgontepa": ["qorgontepa", "qo'rg'ontepa", "kurgantepa"],
    "ulugnor": ["ulugnor", "ulug'nor"],
    "xojaobod": ["xojaobod", "xo'jaobod", "xodjaabad"],

    # --- Farg'ona Viloyati ---
    "fargona": ["fargona", "farg'ona", "fergana", "farg"],
    "qoqon": ["qoqon", "qo'qon", "kokand", "kokan"],
    "margilon": ["margilon", "marg'ilon", "margelan"],
    "quvasoy": ["quvasoy", "kuvasay"],
    "rishton": ["rishton", "rishtan"],
    "oltiariq": ["oltiariq", "altiariq"],
    "bagdod": ["bagdod", "bag'dod", "bagdad"],
    "beshariq": ["beshariq", "besharik"],
    "buvayda": ["buvayda"],
    "dangara": ["dangara", "dang'ara"],
    "uchkoprik": ["uchkoprik", "uchko'prik"],
    "toshloq": ["toshloq", "toshloq"],
    "quva": ["quva", "kuva"],
    "sox": ["sox", "so'x"],
    "yozyovon": ["yozyovon", "yazyavan"],

    # --- Namangan Viloyati ---
    "namangan": ["namangan", "namangon"],
    "chust": ["chust"],
    "kosonsoy": ["kosonsoy", "kasansay"],
    "pop": ["pop"],
    "toraqorgon": ["toraqorgon", "to'raqo'rg'on", "turakurgan"],
    "uchqorgon": ["uchqorgon", "uchqo'rg'on", "uchkurgan"],
    "uychi": ["uychi"],
    "chortoq": ["chortoq", "chartak"],
    "yangiqorgon": ["yangiqorgon", "yangiqo'rg'on"],
    "mingbuloq": ["mingbuloq"],
    "norin": ["norin", "narin", "haqqulobod"],

    # --- Qashqadaryo Viloyati ---
    "qarshi": ["qarshi", "karshi"],
    "shahrisabz": ["shahrisabz", "shaxrisabz", "shaxrisabz"],
    "kitob": ["kitob", "kitab"],
    "koson": ["koson", "kasan"],
    "guzor": ["guzor", "g'uzor"],
    "dehqonobod": ["dehqonobod", "dexqonobod"],
    "qamashi": ["qamashi"],
    "kasbi": ["kasbi", "muglon"],
    "mirishkor": ["mirishkor"],
    "muborak": ["muborak", "mubarek"],
    "nishon": ["nishon", "talimarjon"],
    "chiroqchi": ["chiroqchi"],
    "yakkabog": ["yakkabog", "yakkabog'"],
    "kokdala": ["kokdala", "ko'kdala"],

    # --- Surxondaryo Viloyati ---
    "termiz": ["termiz", "termez"],
    "denov": ["denov", "denau"],
    "boysun": ["boysun", "baysun"],
    "sherobod": ["sherobod", "shirabad"],
    "shorchi": ["shorchi", "sho'rchi"],
    "qumqorgon": ["qumqorgon", "qumqo'rg'on", "kumkurgan"],
    "jarqorgon": ["jarqorgon", "jarqo'rg'on"],
    "angor": ["angor"],
    "bandixon": ["bandixon"],
    "muzrabot": ["muzrabot"],
    "oltinsoy": ["oltinsoy"],
    "sariosiyo": ["sariosiyo"],
    "uzun": ["uzun"],
    "qiziriq": ["qiziriq"],

    # --- Jizzax Viloyati ---
    "jizzax": ["jizzax", "djizak", "jizax"],
    "zomin": ["zomin", "zaamin"],
    "dostlik": ["dostlik", "do'stlik"],
    "zarbdor": ["zarbdor"],
    "zafarobod": ["zafarobod"],
    "mirzachol": ["mirzachol", "mirzacho'l", "gagarin"],
    "paxtakor": ["paxtakor"],
    "baxmal": ["baxmal", "usmat"],
    "forish": ["forish", "bogdon"],
    "gallaorol": ["gallaorol", "g'allaorol"],
    "yangiobod": ["yangiobod"],
    "arnasoy": ["arnasoy"],

    # --- Sirdaryo Viloyati ---
    "guliston": ["guliston", "gulston", "gulistan", "goliston"],
    "shirin": ["shirin"],
    "yangiyer": ["yangiyer"],
    "boyovut": ["boyovut"],
    "mirzaobod": ["mirzaobod"],
    "oqoltin": ["oqoltin"],
    "sardoba": ["sardoba"],
    "sayxunobod": ["sayxunobod"],
    "xovos": ["xovos", "xavas"],
    "sirdaryo": ["sirdaryo", "sirdarya"],

    # --- Navoiy Viloyati ---
    "navoiy": ["navoiy", "navoi", "navoy"],
    "zarafshon": ["zarafshon", "zarafshan"],
    "karmana": ["karmana"],
    "qiziltepa": ["qiziltepa"],
    "konimex": ["konimex", "kanimeh"],
    "nurota": ["nurota", "nurata"],
    "tomdi": ["tomdi"],
    "uchquduq": ["uchquduq", "uchkuduk"],
    "xatirchi": ["xatirchi", "yangirabod"],

    # --- Qoraqalpog'iston Respublikasi ---
    "nukus": ["nukus", "no'kis"],
    "beruniy": ["beruniy", "biruni"],
    "tortkol": ["tortkol", "to'rtko'l", "turtkul"],
    "qongirot": ["qongirot", "qo'ng'irot", "kungrad"],
    "xojayli": ["xojayli", "xo'jayli", "xodjeyli"],
    "chimboy": ["chimboy"],
    "moynoq": ["moynoq", "mo'ynoq", "muynak"],
    "amudaryo": ["amudaryo", "mangit", "mang'it"],
    "taxtakopir": ["taxtakopir", "taxtako'pir"],
    "shumanay": ["shumanay"],
    "qanlikol": ["qanlikol", "qanliko'l"],
    "qoraozak": ["qoraozak", "qorao'zak"],
    "bozatov": ["bozatov", "bo'zatov"],
    "kegeyli": ["kegeyli"],
    "taxiatosh": ["taxiatosh"],
    "ellikqala": ["ellikqala", "ellikqal'a", "bostan"]
}

# Inverted index: alias/stem -> canonical location key
LOCATION_LOOKUP: Dict[str, str] = {}
ALL_LOCATION_STEMS: Set[str] = set()

for canon, aliases in UZBEKISTAN_LOCATIONS.items():
    LOCATION_LOOKUP[canon] = canon
    ALL_LOCATION_STEMS.add(canon)
    for a in aliases:
        LOCATION_LOOKUP[a] = canon
        ALL_LOCATION_STEMS.add(a)

# Common Uzbek/Russian affixes for route extraction
AFFIXES = {
    # Destination suffixes (Dative): "...ga", "...go", "...ka", "...ko", "...ge", "...a"
    "destination": ["gacha", "gacho", "kacha", "kocha", "ga", "go", "ka", "ko", "ge", "a"],
    # Origin suffixes (Ablative): "...dan", "...don", "...din"
    "origin": ["dan", "don", "din"],
    # Locative suffixes: "...da", "...de"
    "locative": ["da", "de"]
}
