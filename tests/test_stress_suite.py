import pytest
from app.services.moderation_filter.classifier import classify_text

MASSIVE_TEST_CASES = [
    # =========================================================================
    # 1. ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ (РУССКИЙ ЯЗЫК) -> Expected: False
    # =========================================================================
    (1, "RU", "Обычный пользователь", "Привет всем! Как дела?", False, "Короткое приветствие"),
    (2, "RU", "Обычный пользователь", "Спасибо большое за помощь, очень выручили!", False, "Благодарность"),
    (3, "RU", "Обычный пользователь", "Кто знает, со скольки завтра работает базар?", False, "Вопрос о времени работы базара"),
    (4, "RU", "Обычный пользователь", "Мы вчера ходили в парк с детьми, погода была отличная ☀️", False, "Бытовое сообщение с эмодзи"),
    (5, "RU", "Обычный пользователь", "Встречаемся на Чиланзаре возле дома 15 в 18:30", False, "Адрес и время встречи"),
    (6, "RU", "Обычный пользователь", "Автобус номер 28 сейчас проехал мимо", False, "Номер автобуса"),
    (7, "RU", "Обычный пользователь", "Картошка на базаре уже по 7000 сум за килограмм, ужас как подорожала", False, "Обсуждение цен на базаре"),
    (8, "RU", "Обычный пользователь", "Потерял паспорт на имя Смирнова А.В., нашедшего прошу вернуть по номеру: +998901234567 за вознаграждение", False, "Потерянные документы с телефоном"),
    (9, "RU", "Обычный пользователь", "Потерялся кот рыжий в районе Юнусабад 4, если кто видел, позвоните: 998931112233", False, "Потерянное животное с телефоном"),
    (10, "RU", "Обычный пользователь", "Кто знает номер Салима ака из махалли?", False, "Поиск контакта человека"),
    (11, "RU", "Обычный пользователь", "Кафе возле нашего дома совсем испортилось, шашлык пересоленный и холодный", False, "Отзыв о заведении"),
    (12, "RU", "Обычный пользователь", "Да, я полностью согласен с вами, так и надо сделать", False, "Ответ собеседнику"),
    (13, "RU", "Обычный пользователь", "Ребята, кто забыл зонтик в офисе на 3 этаже?", False, "Забытая вещь"),
    (14, "RU", "Обычный пользователь", "Подскажите плиз, где в районе сквера нормальная аптека круглосуточная?", False, "Сленг/вопрос про аптеку"),
    (15, "RU", "Обычный пользователь", "Я купил телефон за 200 долларов в кредит, теперь выплачиваю", False, "Личная покупка, упоминание цены"),

    # =========================================================================
    # 1. ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ (УЗБЕКСКИЙ ЯЗЫК - LATIN) -> Expected: False
    # =========================================================================
    (16, "UZ", "Oddiy foydalanuvchi", "Assalomu alaykum hammaga! Xayrli tong!", False, "Salomlashish"),
    (17, "UZ", "Oddiy foydalanuvchi", "Rahmat katta, yordam berganingiz uchun minnatdorman!", False, "Minnatdorchilik"),
    (18, "UZ", "Oddiy foydalanuvchi", "Ertaga soat 9 da maktabda yig'ilish bo'larkan, hamma kelsin", False, "Maktab majlisi xabari"),
    (19, "UZ", "Oddiy foydalanuvchi", "Amir Temur ko'chasida probka juda katta, boshqa yo'ldan yuringlar", False, "Yo'ldagi tirbandlik"),
    (20, "UZ", "Oddiy foydalanuvchi", "Bozorda go'sht 95 000 so'm bo'libdi, narxlar oshib ketibdi", False, "Go'sht narxini muhokama qilish"),
    (21, "UZ", "Oddiy foydalanuvchi", "Hujjatlarim tushib qolibdi Chilonzorda, topgan odamga mukofot bor, tel: +998909876543", False, "Hujjat yo'qolishi telefon bilan"),
    (22, "UZ", "Oddiy foydalanuvchi", "Ertaga havo qanday bo'ladi, yomg'ir yog'maydimi?", False, "Ob-havo savoli"),
    (23, "UZ", "Oddiy foydalanuvchi", "O'g'lim 5-maktabda o'qiydi, 3-sinf", False, "Oddiy raqamlar"),
    (24, "UZ", "Oddiy foydalanuvchi", "Ha to'g'ri aytdingiz, men ham ko'rdim o'sha voqeani", False, "Suhbatdoshga javob"),
    (25, "UZ", "Oddiy foydalanuvchi", "Kechagi osh juda mazali bo'libdi, oshxona zo'r ekan", False, "Oddiy taassurot"),
    (26, "UZ", "Oddiy foydalanuvchi", "Kimda Anvarjonning nomeri bor? Bir narsa so'ramoqchi edim", False, "Tanishning nomerini so'rash"),
    (27, "UZ", "Oddiy foydalanuvchi", "Mashinamni garajga qo'ydim, uydaman", False, "Oddiy gap"),
    (28, "UZ", "Oddiy foydalanuvchi", "Qo'shnilar, soat 23:00 dan keyin shovqin qilmanglar iltimos!", False, "Iltimos / ogohlantirish"),
    (29, "UZ", "Oddiy foydalanuvchi", "Bolalar maydonchasida kalit qolib ketibdi, kim yo'qotdi?", False, "Topilgan buyum"),
    (30, "UZ", "Oddiy foydalanuvchi", "Telefonimni batareyasi tez o'tirib qolyapti, nima qilsa bo'ladi?", False, "Maslahat so'rash"),

    # =========================================================================
    # 2. ОБЫЧНЫЙ КЛИЕНТ (РУССКИЙ ЯЗЫК) -> Expected: False
    # =========================================================================
    (31, "RU", "Клиент ищет услугу", "Кто сегодня едет в Гулистан? Мне нужно доехать", False, "Пассажир ищет машину в Гулистан"),
    (32, "RU", "Клиент ищет услугу", "Мне нужно доехать до Ташкента вечером, кто-нибудь едет?", False, "Пассажир ищет попутку до Ташкента"),
    (33, "RU", "Клиент ищет услугу", "Кто может забрать меня вечером с вокзала?", False, "Пассажир просит забрать с вокзала"),
    (34, "RU", "Клиент ищет услугу", "Есть кто-нибудь, кто едет завтра утром в Самарканд?", False, "Поиск попутки на утро"),
    (35, "RU", "Клиент ищет услугу", "Нужна машина на 5 человек до Бухары, сколько будет стоить?", False, "Запрос машины на семью"),
    (36, "RU", "Клиент ищет услугу", "Кто едет из Бухары в Самарканд сегодня после обеда?", False, "Поиск попутного транспорта"),
    (37, "RU", "Клиент ищет услугу", "Ищу хорошего сантехника, кран на кухне течет", False, "Поиск мастера по сантехнике"),
    (38, "RU", "Клиент ищет услугу", "Подскажите хорошего электрика в нашем районе", False, "Поиск электрика"),
    (39, "RU", "Клиент ищет услугу", "Где можно недорого отремонтировать ноутбук?", False, "Поиск ремонта ноутбука"),
    (40, "RU", "Клиент ищет услугу", "Нужна химчистка ковра, кто может посоветовать нормальную фирму?", False, "Поиск химчистки ковра"),
    (41, "RU", "Клиент ищет услугу", "Хочу заказать пиццу на дом, какая доставка быстрее всех привозит?", False, "Клиент выбирает доставку пиццы"),
    (42, "RU", "Клиент ищет услугу", "Ищу репетитора по математике для ребенка 7 класс", False, "Поиск репетитора"),
    (43, "RU", "Клиент ищет услугу", "Кто знает хорошую швею, нужно укоротить брюки?", False, "Поиск швеи"),

    # =========================================================================
    # 2. ОБЫЧНЫЙ КЛИЕНТ (УЗБЕКСКИЙ ЯЗЫК) -> Expected: False
    # =========================================================================
    (44, "UZ", "Mijoz xizmat qidirmoqda", "Bugun Toshkentga kim boryapti? 2 kishiga joy kerak", False, "2 kishiga taksi qidirish"),
    (45, "UZ", "Mijoz xizmat qidirmoqda", "Toshkentdan Samarqandga borishim kerak, kim olib ketadi?", False, "Toshkent-Samarqand yo'lovchi"),
    (46, "UZ", "Mijoz xizmat qidirmoqda", "Kim kechga Buxoroga ketyapti? Kichkina sumka berib yubormoqchi edim", False, "Pochta berib yuborish iltimosi"),
    (47, "UZ", "Mijoz xizmat qidirmoqda", "Ertaga ertalab soat 6 da Andijonga mashina bormi?", False, "Ertalabki mashinani so'rash"),
    (48, "UZ", "Mijoz xizmat qidirmoqda", "Menga konditsioner o'rnatadigan yaxshi usta kerak, kimni bilasizlar?", False, "Konditsioner ustasini qidirish"),
    (49, "UZ", "Mijoz xizmat qidirmoqda", "Kir yuvish mashinam suv chiqarmayapti, kim tuzatadi?", False, "Kir mashina ustasini qidirish"),
    (50, "UZ", "Mijoz xizmat qidirmoqda", "Ingliz tili repetitori qidiryapman, yaxshi o'qituvchi bormi?", False, "Repetitor qidirish"),
    (51, "UZ", "Mijoz xizmat qidirmoqda", "Uyga tozalovchi ayol kerak edi haftada 2 kun, nomer bormi?", False, "Tozalovchi qidirish"),
    (52, "UZ", "Mijoz xizmat qidirmoqda", "Moshinam yo'lda o'chib qoldi, evakuator kerak, kimda nomer bor?", False, "Evakuator qidirish"),
    (53, "UZ", "Mijoz xizmat qidirmoqda", "Menga to'yga 150 ta taklifnoma kerak, qayerda arzon tayyorlaydi?", False, "Taklifnoma qidirish"),
    (54, "UZ", "Mijoz xizmat qidirmoqda", "Chilonzordan 2 xonali kvartira ijaraga olmoqchiman, kimda bor?", False, "Ijara qidirish"),

    # =========================================================================
    # 3. ТАКСИСТ (ИНФОРМАЦИЯ VS ОБЫЧНЫЙ ТАКСИСТ) -> Expected: True
    # =========================================================================
    (55, "RU", "Таксист объявление", "Еду завтра в Ташкент, есть 2 свободных места", True, "Водитель: еду завтра, есть 2 места"),
    (56, "RU", "Таксист объявление", "Буду выезжать в 8 утра из Самарканда в Ташкент, машина Cobalt", True, "Водитель: выезжаю в 8 утра"),
    (57, "RU", "Таксист объявление", "Из Бухары в Ташкент, выезд утром, салон пустой, звоните", True, "Водитель: салон пустой"),
    (58, "RU", "Таксист объявление", "Такси до Самарканда, берем людей и посылки", True, "Такси: берем людей и посылки"),
    (59, "RU", "Таксист объявление", "Есть место в машине до Намангана, выезжаем через час", True, "Водитель: есть место в машине"),
    (60, "RU", "Таксист объявление", "Такси Ташкент Бухара сегодня вечером, выезд в 19:00", True, "Такси Ташкент Бухара"),
    (61, "UZ", "Taksist e'loni", "Toshkent Samarqand mashina bor, 2 ta joy bor yuramiz", True, "Mashina bor 2 ta joy bor"),
    (62, "UZ", "Taksist e'loni", "Bugun kechga Farg'onaga pochta va odam olamiz, salon bo'sh", True, "Pochta va odam olamiz"),
    (63, "UZ", "Taksist e'loni", "Zapravkadamiz, 1 kishi bo'lsa Toshkentga yuramiz hoziroq", True, "Zapravkadamiz 1 kishi"),
    (64, "UZ", "Taksist e'loni", "Buxoro Toshkent har kuni qatnaymiz, qulay avtomashina", True, "Har kuni qatnaymiz"),
    (65, "UZ", "Taksist e'loni", "Toshkentga 1 kishi kerak ketamiz darhol", True, "1 kishi kerak ketamiz"),
    (66, "UZ", "Taksist e'loni", "Xorazmdan Toshkentga bitta joy bor, ketdik", True, "Bitta joy bor ketdik"),

    # =========================================================================
    # 4. ТАКСИСТ РЕКЛАМИРУЕТ СЕБЯ (ПРЯМАЯ, АГРЕССИВНАЯ, МЯГКАЯ, МАСКИРОВКА)
    # Expected: True
    # =========================================================================
    (67, "RU", "Такси реклама", "Такси Бухара — Ташкент, звоните в любое время: +998901234567", True, "Прямая реклама такси с телефоном"),
    (68, "RU", "Такси реклама", "Возьму пассажиров до Ферганы, комфортная иномарка, кондиционер, багаж", True, "Возьму пассажиров комфорт"),
    (69, "RU", "Такси реклама", "Заказывайте такси по городу и межгород, недорого и быстро!", True, "Заказывайте такси"),
    (70, "RU", "Такси реклама", "ЛУЧШЕЕ ТАКСИ БУХАРА ТАШКЕНТ! ЗВОНИТЕ ПРЯМО СЕЙЧАС ДЕШЕВО!", True, "Агрессивная реклама капсом"),
    (71, "RU", "Такси реклама", "САМЫЕ НИЗКИЕ ЦЕНЫ НА ТАКСИ В САМАРКАНД! ЗВОНИТЕ: 998931112233", True, "Агрессивная реклама цены"),
    (72, "RU", "Такси реклама", "Если кому-нибудь понадобится поездка в Ташкент, могу отвезти, пишите в личку", True, "Мягкая реклама с ЛС"),
    (73, "RU", "Такси реклама", "Завтра еду в Ташкент по делам, если кому нужно доехать — пишите в лс, возьму недорого", True, "Мягкая реклама попутчиков"),
    (74, "RU", "Такси реклама", "Такси в ташкен беру 4 человек", True, "Короткое объявление водителя"),
    (75, "RU", "Такси реклама", "🔥 ТАШКЕНТ — ЕДЕМ! Есть места для 4 человек. За подробностями в ЛС.", True, "Эмодзи + места + ЛС"),
    (76, "UZ", "Takso reklama", "ENG ARZON TAXSI TOSHKENTGA! 24/7 XIZMATINGIZDA TEL: 998901234567", True, "Agressiv uzbek taksi reklama"),
    (77, "UZ", "Takso reklama", "Ertaga Toshkentga boraman, kimga moshina kerak bo'lsa olib ketishim mumkin lichkaga yozing", True, "Yumshoq taksi taklifi lichkaga"),
    (78, "UZ", "Takso reklama", "Gulistonga taxsi kim ketsa lichgaga yozsin 2 ta joy bor", True, "Dialekt + lichkaga taklif"),

    # =========================================================================
    # 5. БИЗНЕС РЕКЛАМА (МАГАЗИНЫ, УСЛУГИ, ОБЩЕПИТ, РЕМОНТ, КУРСЫ И Т.Д.)
    # Expected: True
    # =========================================================================
    (79, "RU", "Бизнес реклама", "Новое поступление женской одежды из Турции! Цены от 150 000 сум. Заказывайте: t.me/modatashkent", True, "Магазин одежды ссылка"),
    (80, "RU", "Бизнес реклама", "Ресторан 'Самарканд' приглашает на вкусные шашлыки! Доставка бесплатно: +998901112233", True, "Ресторан телефон"),
    (81, "RU", "Бизнес реклама", "Кафе открылось! Вкусные бургеры и лаваш со скидкой 20% в честь открытия!", True, "Кафе открытие скидка"),
    (82, "RU", "Бизнес реклама", "Качественная мойка и полировка авто в Ташкенте! Химчистка салона недорого.", True, "Автомойка полировка"),
    (83, "RU", "Бизнес реклама", "Ремонт квартир и офисов под ключ. Опытные мастера, гарантия качества. Звоните: 998905554433", True, "Ремонт квартир"),
    (84, "RU", "Бизнес реклама", "Оригинальные iPhone 15 Pro Max в наличии! Гарантия 1 год, доставка по всему Узбекистану.", True, "Магазин телефонов"),
    (85, "RU", "Бизнес реклама", "Быстрая доставка суши и пиццы по городу 24/7. Заказ по телефону: 998712001122", True, "Доставка еды 24/7"),
    (86, "RU", "Бизнес реклама", "Салон красоты приглашает на маникюр и педикюр! Скидка 30% на первое посещение.", True, "Салон красоты скидка"),
    (87, "RU", "Бизнес реклама", "Уютная гостиница в Бухаре, чистые номера, завтрак включен. Бронируйте по телефону", True, "Гостиница бронь"),
    (88, "RU", "Бизнес реклама", "Учебный центр объявляет набор на курсы английского и IT! Запись по телефону: 998901234567", True, "Учебный центр запись"),
    (89, "RU", "Бизнес реклама", "Строительная компания построит дом вашей мечты! Проект в подарок при заказе.", True, "Строительство домов"),
    (90, "RU", "Бизнес реклама", "Домашние торты и пирожные на заказ к вашему празднику! Пишите в лс для заказа.", True, "Торты на заказ ЛС"),
    (91, "RU", "Бизнес реклама", "Подписывайтесь на наш канал со скидками и распродажами: @skidki_tashkent", True, "Подписка на канал"),
    (92, "UZ", "Biznes reklama", "Yangi kiyimlar do'koni ochildi! Barcha tovarlarga 30% chegirma, shoshiling!", True, "Kiyim dokon ochilishi"),
    (93, "UZ", "Biznes reklama", "Kafemizga xush kelibsiz! Mazali lavash va fastfud, yetkazib berish bepul: 998901112233", True, "Kafe dostavka"),
    (94, "UZ", "Biznes reklama", "Avtomobillarni polirovka qilish va ximchistka xizmati mavjud, sifat kafolati bilan", True, "Avto ximchistka"),
    (95, "UZ", "Biznes reklama", "Uy sharoitida pishirilgan tort va shirinliklarga buyurtma olamiz! Murojaat uchun lichkaga yozing", True, "Tort buyurtma lichka"),
    (96, "UZ", "Biznes reklama", "O'quv markazimizda yangi guruhlarga qabul boshlandi! Matematika va ingliz tili, tel: 998901234567", True, "Oquv markaz telefon"),
    (97, "UZ", "Biznes reklama", "Kanalimizga ulaning va eng arzon tovarlarni sotib oling: @arzon_savdo", True, "Kanalga ulanish username"),
    (98, "UZ", "Biznes reklama", "Kompyuter va noutbuklarni tez va sifatli tamirlaymiz, usta xizmati", True, "Kompyuter tamirlash usta"),

    # =========================================================================
    # 6. СКРЫТАЯ / ЗАМАСКИРОВАННАЯ РЕКЛАМА И ОБХОД ФИЛЬТРА -> Expected: True
    # =========================================================================
    (99, "RU", "Обход фильтра", "т а к с и Ташкент Самарканд 2 места свободно", True, "Разрядка букв пробелами"),
    (100, "RU", "Обход фильтра", "Т.А.К.С.И. в Ташкент выезжаем", True, "Точки между буквами"),
    (101, "RU", "Обход фильтра", "Кто хочет заказать недорогую одежду — пишите в личку", True, "Риторический вопрос + заказ одежды"),
    (102, "RU", "Обход фильтра", "Той учун таклифнома сайт яратамиз! Нархи 100 000 сумдан бошланади. Пишите в ЛС", True, "Сайт-пригласительное с ценой и ЛС"),
    (103, "RU", "Обход фильтра", "Тел для заказа: 9️⃣0️⃣-1️⃣2️⃣3️⃣-4️⃣5️⃣-6️⃣7️⃣ доставка бесплатная", True, "Эмодзи-цифры в номере"),
    (104, "RU", "Обход фильтра", "Заходите на наш сайт: https:// arzon-bozor . uz / скидки", True, "Разорванная ссылка"),
    (105, "RU", "Обход фильтра", "Продаю айфон 14 про, цена в лс, подробности в лс", True, "Цена и подробности в ЛС"),
    (106, "RU", "Обход фильтра", "Такси\nТашкент\nБухара\n2 места есть\nВыезжаем", True, "Многострочное объявление"),
    (107, "UZ", "Filtrni aylanib otish", "s o t i l a d i yangi iphone narxi arzon", True, "Harflar orasida probel"),
    (108, "UZ", "Filtrni aylanib otish", "t-a-k-s-i Toshkentga yuramiz 2 ta joy", True, "Harflar orasida defis"),
    (109, "UZ", "Filtrni aylanib otish", "Narxini lichkada aytaman yozvorila", True, "Narxini lichkada yashirish"),
    (110, "UZ", "Filtrni aylanib otish", "To'yga zamonaviy taklifnoma-sayt kerakmi? DM ga yozing", True, "Savol niqobi ostida xizmat"),
    (111, "UZ", "Filtrni aylanib otish", "Kanalimizga kiring t . me / arzon_dokon", True, "Buzilgan havola"),
    (112, "UZ", "Filtrni aylanib otish", "Gurlan osh ga ishchi garak ayliqni galishamiz", True, "Xorazm shevasi vakansiya"),

    # =========================================================================
    # 7. РУССКО-УЗБЕКСКИЙ МИКС (СМЕШАННЫЙ ЯЗЫК)
    # =========================================================================
    (113, "MIX", "Обычный пользователь", "Salom hammaga, как дела у всех?", False, "Обычное приветствие микс"),
    (114, "MIX", "Обычный пользователь", "Bozorda go'sht narxi сколько сейчас стоит?", False, "Обычный вопрос о цене мяса микс"),
    (115, "MIX", "Клиент ищет услугу", "Kim Tashkentga ketadi завтра утром? 2 кишига жой керак", False, "Пассажир ищет попутку микс"),
    (116, "MIX", "Клиент ищет услугу", "Bugun кечқурун кто едет в Самарканд? Бitta сумкам бор эди", False, "Пассажир передает сумку микс"),
    (117, "MIX", "Таксист реклама", "Toshkentga taxi bor, кому нужно пишите в лс", True, "Таксист микс с ЛС"),
    (118, "MIX", "Таксист реклама", "Кимга машина kerak bo'lsa lichkaga yozsin, Ташкентга юрамиз", True, "Таксист микс юрамиз"),
    (119, "MIX", "Бизнес реклама", "Yangi kiyimlar keldi, кто хочет заказать пишите: @shop_uz", True, "Бизнес микс с каналом"),
    (120, "MIX", "Бизнес реклама", "O'quv markazimizda скидки 50% boshlandi, успейте записаться: 998901112233", True, "Курсы со скидкой и телефоном микс"),

    # =========================================================================
    # 8. РАЗНЫЕ ВАРИАНТЫ ТЕЛЕФОНОВ, ССЫЛОК И USERNAME
    # =========================================================================
    (121, "RU", "Реклама с телефоном", "Такси Ташкент Самарканд: +998 90 123 45 67", True, "Телефон с международным кодом"),
    (122, "RU", "Реклама с телефоном", "Такси: 90 123 45 67 выезжаем", True, "Телефон без кода страны с пробелами"),
    (123, "RU", "Реклама с телефоном", "Taksi mashina bor: (90) 123-45-67", True, "Телефон со скобками и дефисом"),
    (124, "RU", "Реклама с телефоном", "Mashina bor: 90.123.45.67 joy bor", True, "Телефон с точками"),
    (125, "RU", "Реклама с сылкой", "Купить дешевые товары здесь: https://t.me/super_magazin", True, "Ссылка t.me на магазин"),
    (126, "RU", "Реклама со ссылкой", "Наш сайт с одеждой: www.arzonshop.uz доставка бесплатно", True, "Сайт без https"),
    (127, "RU", "Реклама со ссылкой", "Подписывайтесь на инстаграм: instagram.com/my_restaurant", True, "Ссылка на инстаграм"),
    (128, "RU", "Обычный с username", "Привет @nodirbek, ты сегодня придешь на футбол?", False, "Обычное обращение к другу по @username"),
    (129, "RU", "Обычный с телефоном", "Ребята, вот номер справочной вокзала: 1005, если кому надо расписание", False, "Короткий справочный номер"),

    # =========================================================================
    # 9. ЭКСТРЕМАЛЬНЫЕ И СТРЕСС-ТЕСТЫ (КОРОТКИЕ, ДЛИННЫЕ, ПОВТОРЫ, СИМВОЛЫ)
    # =========================================================================
    (130, "RU", "Экстремальный тест", "Привет", False, "Одно обычное слово"),
    (131, "RU", "Экстремальный тест", "???", False, "Только знаки вопроса"),
    (132, "RU", "Экстремальный тест", "🔥🔥🔥", False, "Только эмодзи"),
    (133, "RU", "Экстремальный тест", "Ок", False, "Две буквы"),
    (134, "RU", "Экстремальный тест", "Сот", False, "Обрубок слова"),
    (135, "UZ", "Ekstremal test", "Ha", False, "Bitta so'z ha"),
    (136, "UZ", "Ekstremal test", "Rahmat", False, "Bitta so'z rahmat"),
    (137, "UZ", "Ekstremal test", "Sotiladi", True, "Bitta so'z sotiladi (tijoriy signal)"),
    (138, "UZ", "Ekstremal test", "Yuramiz", True, "Bitta so'z yuramiz (taksi signali)"),
    (139, "UZ", "Ekstremal test", "Joy bor", True, "Ikkita so'z joy bor (taksi signali)"),
    (140, "RU", "Экстремальный тест", "Беру 4 человек", True, "Короткое объявление таксиста беру 4 человек"),
    (141, "RU", "Экстремальный тест", "Есть места", True, "Короткое объявление есть места"),

    # =========================================================================
    # 10. FALSE POSITIVE ПРОВЕРКА (СЛОЖНЫЕ БЫТОВЫЕ СООБЩЕНИЯ) -> Expected: False
    # =========================================================================
    (142, "RU", "False Positive Check", "Кто знает, где продается нормальный хлеб в нашем районе?", False, "Вопрос со словом 'продается'"),
    (143, "RU", "False Positive Check", "Вчера в магазине на углу была акция, масло продавали со скидкой", False, "Обсуждение вчерашней акции"),
    (144, "RU", "False Positive Check", "Сколько стоит проезд в автобусе в этом году?", False, "Вопрос о стоимости проезда"),
    (145, "RU", "False Positive Check", "Мне кажется, эта машина сломалась и никуда не едет", False, "Бытовой разговор со словами машина/едет"),
    (146, "RU", "False Positive Check", "Я оставил телефон дома и не мог никому позвонить", False, "Слово телефон в обычном контексте"),
    (147, "UZ", "False Positive Check", "Bugun qaysi do'konda chegirma borligini bilasizmi?", False, "Savolda chegirma so'zi"),
    (148, "UZ", "False Positive Check", "Usta nomeri kerak edi, muzlatgichim buzilib qoldi", False, "Savolda usta va nomer so'zlari"),
    (149, "UZ", "False Positive Check", "Toshkentga poezd biletlari narxi necha pul bo'libdi?", False, "Poezd bileti narxi savoli"),
    (150, "UZ", "False Positive Check", "Bugun barcha mahsulotlarga chegirmada dedimi aksiya muddati cheklangan dedi", False, "O'zbekcha eshitgan gapini so'rash"),
    (151, "UZ", "False Positive Check", "Ingliz tili kurslariga qabul boshlandi dedi Batafsil ma'lumotni uchun qayerga yozay yozing.", False, "Kursga qayerga yozilishni so'rash"),
    (152, "UZ", "False Positive Check", "Taqsi toshkentga 4 odam miz", False, "Yo'lovchilar guruhi taksi qidirmoqda"),
    (153, "RU", "False Positive Check", "такси в ташкен 4 чел", False, "Пассажиры на русском ищут такси на 4 человек"),
]

@pytest.mark.parametrize("case_id,lang,persona,text,expected,desc", MASSIVE_TEST_CASES)
def test_massive_stress_case(case_id, lang, persona, text, expected, desc):
    res = classify_text(text)
    assert res.is_ad == expected, (
        f"Case #{case_id} failed [{lang} | {persona}]: expected={expected}, "
        f"got={res.is_ad} (score={res.score}, reason='{res.reason}'). Text: '{text}'"
    )
