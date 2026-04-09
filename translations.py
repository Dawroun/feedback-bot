"""
Tillar lug'ati
==============
Barcha bot xabarlari 3 tilda: uz_lat (lotin), uz_cyr (kirill), ru (ruscha)
"""

TRANSLATIONS = {
    # ── Til tanlash ──────────────────────────────────────────────
    "choose_language": {
        "uz_lat": "Tilni tanlang / Выберите язык / Тилни танланг",
        "uz_cyr": "Tilni tanlang / Выберите язык / Тилни танланг",
        "ru": "Tilni tanlang / Выберите язык / Тилни танланг",
    },

    # ── Welcome ──────────────────────────────────────────────────
    "welcome": {
        "uz_lat": (
            "Assalomu alaykum, {name}! 👋\n\n"
            "<b>{center}</b> feedback botiga xush kelibsiz!\n\n"
            "Siz bu yerda o'quv markazi haqida fikr-mulohazangizni "
            "qoldirishingiz mumkin.\n\n"
            "📌 Ism ko'rinsinmi yoki anonim bo'lasizmi?"
        ),
        "uz_cyr": (
            "Ассалому алайкум, {name}! 👋\n\n"
            "<b>{center}</b> фидбек ботига хуш келибсиз!\n\n"
            "Сиз бу ерда ўқув маркази ҳақида фикр-мулоҳазангизни "
            "қолдиришингиз мумкин.\n\n"
            "📌 Исм кўринсинми ёки аноним бўласизми?"
        ),
        "ru": (
            "Здравствуйте, {name}! 👋\n\n"
            "Добро пожаловать в бот обратной связи <b>{center}</b>!\n\n"
            "Здесь вы можете оставить свой отзыв об учебном центре.\n\n"
            "📌 Показать ваше имя или остаться анонимным?"
        ),
    },

    # ── Anonim tanlash tugmalari ─────────────────────────────────
    "btn_show_name": {
        "uz_lat": "👤 Ismim ko'rinsin",
        "uz_cyr": "👤 Исмим кўринсин",
        "ru": "👤 Показать имя",
    },
    "btn_anonymous": {
        "uz_lat": "🕶 Anonim",
        "uz_cyr": "🕶 Аноним",
        "ru": "🕶 Анонимно",
    },

    # ── Anonim tanlangandan keyin ────────────────────────────────
    "anon_chosen": {
        "uz_lat": "Tanlandi: <b>{label}</b>\n\n📚 Endi qaysi kurs haqida fikr bildirasiz?",
        "uz_cyr": "Танланди: <b>{label}</b>\n\n📚 Энди қайси курс ҳақида фикр билдирасиз?",
        "ru": "Выбрано: <b>{label}</b>\n\n📚 О каком курсе хотите оставить отзыв?",
    },

    # ── Kurs tanlangandan keyin ──────────────────────────────────
    "course_chosen": {
        "uz_lat": (
            "📚 Kurs: <b>{course}</b>\n\n"
            "Endi fikringizni yuboring:\n"
            "🎤 <b>Ovozli habar</b> yoki ✏️ <b>Matn</b> yozing.\n\n"
            "💡 Bugun yana {remaining} ta feedback yuborishingiz mumkin."
        ),
        "uz_cyr": (
            "📚 Курс: <b>{course}</b>\n\n"
            "Энди фикрингизни юборинг:\n"
            "🎤 <b>Овозли хабар</b> ёки ✏️ <b>Матн</b> ёзинг.\n\n"
            "💡 Бугун яна {remaining} та фидбек юборишингиз мумкин."
        ),
        "ru": (
            "📚 Курс: <b>{course}</b>\n\n"
            "Отправьте ваш отзыв:\n"
            "🎤 <b>Голосовое сообщение</b> или ✏️ <b>Текст</b>.\n\n"
            "💡 Сегодня вы можете отправить ещё {remaining} отзывов."
        ),
    },
    "btn_general": {
        "uz_lat": "📋 Umumiy fikr",
        "uz_cyr": "📋 Умумий фикр",
        "ru": "📋 Общий отзыв",
    },

    # ── Feedback qabul qilindi ───────────────────────────────────
    "voice_received": {
        "uz_lat": "🎤 Ovozli habar qabul qilindi. Tahlil qilinmoqda...",
        "uz_cyr": "🎤 Овозли хабар қабул қилинди. Таҳлил қилинмоқда...",
        "ru": "🎤 Голосовое сообщение получено. Анализируем...",
    },
    "text_received": {
        "uz_lat": "📝 Fikringiz qabul qilindi. Tahlil qilinmoqda...",
        "uz_cyr": "📝 Фикрингиз қабул қилинди. Таҳлил қилинмоқда...",
        "ru": "📝 Ваш отзыв получен. Анализируем...",
    },
    "voice_unclear": {
        "uz_lat": "⚠️ Ovozli habar tushunarsiz chiqdi.\nIltimos, aniqroq gapiring yoki matn yozing.",
        "uz_cyr": "⚠️ Овозли хабар тушунарсиз чиқди.\nИлтимос, аниқроқ гапиринг ёки матн ёзинг.",
        "ru": "⚠️ Голосовое сообщение не удалось распознать.\nПожалуйста, говорите чётче или напишите текстом.",
    },
    "text_too_short": {
        "uz_lat": "✏️ Iltimos, batafsil yozing (kamida 5 belgi).",
        "uz_cyr": "✏️ Илтимос, батафсил ёзинг (камида 5 белги).",
        "ru": "✏️ Пожалуйста, напишите подробнее (минимум 5 символов).",
    },

    # ── Sentiment javoblari ──────────────────────────────────────
    "response_positive": {
        "uz_lat": (
            "✅ <b>Fikr-mulohazangiz qabul qilindi!</b>\n\n"
            "📚 Kurs: {course}\n\n"
            "Ishonchingiz uchun katta rahmat! 🙏\n"
            "Farzandingiz biz bilan ajoyib natijalarga erishadi. "
            "Sizning qo'llab-quvvatlashingiz biz uchun katta ilhom!\n\n"
            "💪 {center} jamoasi har doim eng yaxshisini beradi!"
        ),
        "uz_cyr": (
            "✅ <b>Фикр-мулоҳазангиз қабул қилинди!</b>\n\n"
            "📚 Курс: {course}\n\n"
            "Ишончингиз учун катта раҳмат! 🙏\n"
            "Фарзандингиз биз билан ажойиб натижаларга эришади. "
            "Сизнинг қўллаб-қувватлашингиз биз учун катта илҳом!\n\n"
            "💪 {center} жамоаси ҳар доим энг яхшисини беради!"
        ),
        "ru": (
            "✅ <b>Ваш отзыв принят!</b>\n\n"
            "📚 Курс: {course}\n\n"
            "Большое спасибо за доверие! 🙏\n"
            "Ваш ребёнок достигнет отличных результатов вместе с нами. "
            "Ваша поддержка — огромное вдохновение для нас!\n\n"
            "💪 Команда {center} всегда старается для вас!"
        ),
    },
    "response_negative": {
        "uz_lat": (
            "📝 <b>Fikr-mulohazangiz qabul qilindi!</b>\n\n"
            "📚 Kurs: {course}\n\n"
            "Bu holatdan juda afsusdamiz. 😔\n"
            "Siz aytgan fikrlarni albatta inobatga olamiz.\n"
            "Tez fursatda muammoni hal qilib, sizga qayta aloqaga chiqamiz.\n\n"
            "Sabr-toqatingiz uchun rahmat! 🙏"
        ),
        "uz_cyr": (
            "📝 <b>Фикр-мулоҳазангиз қабул қилинди!</b>\n\n"
            "📚 Курс: {course}\n\n"
            "Бу ҳолатдан жуда афсусдамиз. 😔\n"
            "Сиз айтган фикрларни албатта инобатга оламиз.\n"
            "Тез фурсатда муаммони ҳал қилиб, сизга қайта алоқага чиқамиз.\n\n"
            "Сабр-тоқатингиз учун раҳмат! 🙏"
        ),
        "ru": (
            "📝 <b>Ваш отзыв принят!</b>\n\n"
            "📚 Курс: {course}\n\n"
            "Нам очень жаль, что так получилось. 😔\n"
            "Мы обязательно учтём ваши замечания.\n"
            "В ближайшее время решим проблему и свяжемся с вами.\n\n"
            "Спасибо за терпение! 🙏"
        ),
    },
    "response_neutral": {
        "uz_lat": (
            "✅ <b>Fikr-mulohazangiz qabul qilindi!</b>\n\n"
            "📚 Kurs: {course}\n\n"
            "Fikringiz uchun minnatdormiz! 🙏\n"
            "Farzandingizning porloq kelajagi uchun birgalikda "
            "harakat qilamiz.\n\n"
            "💫 {center} — bilim va muvaffaqiyat maskani!"
        ),
        "uz_cyr": (
            "✅ <b>Фикр-мулоҳазангиз қабул қилинди!</b>\n\n"
            "📚 Курс: {course}\n\n"
            "Фикрингиз учун миннатдормиз! 🙏\n"
            "Фарзандингизнинг порлоқ келажаги учун биргаликда "
            "ҳаракат қиламиз.\n\n"
            "💫 {center} — билим ва муваффақият маскани!"
        ),
        "ru": (
            "✅ <b>Ваш отзыв принят!</b>\n\n"
            "📚 Курс: {course}\n\n"
            "Благодарим за ваше мнение! 🙏\n"
            "Мы вместе работаем ради светлого будущего "
            "вашего ребёнка.\n\n"
            "💫 {center} — территория знаний и успеха!"
        ),
    },

    # ── Tugma matnlari ───────────────────────────────────────────
    "btn_again": {
        "uz_lat": "📝 Yana feedback yozish",
        "uz_cyr": "📝 Яна фидбек ёзиш",
        "ru": "📝 Написать ещё отзыв",
    },

    # ── Follow-up (admin javobidan keyin) ────────────────────────
    "followup_message": {
        "uz_lat": (
            "📬 <b>Hurmatli ota-ona!</b>\n\n"
            "Siz yozgan fikr-mulohaza inobatga olindi:\n\n"
            "💬 <i>{reply}</i>\n\n"
            "Endi bu masaladan mamnunmisiz?"
        ),
        "uz_cyr": (
            "📬 <b>Ҳурматли ота-она!</b>\n\n"
            "Сиз ёзган фикр-мулоҳаза инобатга олинди:\n\n"
            "💬 <i>{reply}</i>\n\n"
            "Энди бу масаладан мамнунмисиз?"
        ),
        "ru": (
            "📬 <b>Уважаемый родитель!</b>\n\n"
            "Ваш отзыв был принят во внимание:\n\n"
            "💬 <i>{reply}</i>\n\n"
            "Вы довольны решением?"
        ),
    },
    "btn_satisfied": {
        "uz_lat": "✅ Ha, mamnunman",
        "uz_cyr": "✅ Ҳа, мамнунман",
        "ru": "✅ Да, доволен(а)",
    },
    "btn_unsatisfied": {
        "uz_lat": "❌ Yo'q",
        "uz_cyr": "❌ Йўқ",
        "ru": "❌ Нет",
    },
    "satisfied_response": {
        "uz_lat": (
            "✅ <b>Ajoyib!</b>\n\n"
            "Mamnunligingiz biz uchun eng katta mukofot!\n"
            "Biz doim siz va farzandingiz uchun ishlaymiz. 🙏\n\n"
            "💫 {center} — sizning ishonchli hamkoringiz!"
        ),
        "uz_cyr": (
            "✅ <b>Ажойиб!</b>\n\n"
            "Мамнунлигингиз биз учун энг катта мукофот!\n"
            "Биз доим сиз ва фарзандингиз учун ишлаймиз. 🙏\n\n"
            "💫 {center} — сизнинг ишончли ҳамкорингиз!"
        ),
        "ru": (
            "✅ <b>Отлично!</b>\n\n"
            "Ваша удовлетворённость — лучшая награда для нас!\n"
            "Мы всегда работаем для вас и вашего ребёнка. 🙏\n\n"
            "💫 {center} — ваш надёжный партнёр!"
        ),
    },
    "unsatisfied_response": {
        "uz_lat": (
            "😔 Tushundik, uzr so'raymiz.\n\n"
            "Iltimos, hozirgi muammoingiz haqida batafsil yozing.\n\n"
            "📌 Ism ko'rinsinmi yoki anonim bo'lasizmi?"
        ),
        "uz_cyr": (
            "😔 Тушундик, узр сўраймиз.\n\n"
            "Илтимос, ҳозирги муаммоингиз ҳақида батафсил ёзинг.\n\n"
            "📌 Исм кўринсинми ёки аноним бўласизми?"
        ),
        "ru": (
            "😔 Понимаем, приносим извинения.\n\n"
            "Пожалуйста, подробно опишите текущую проблему.\n\n"
            "📌 Показать ваше имя или остаться анонимным?"
        ),
    },

    # ── Moderatsiya ──────────────────────────────────────────────
    "banned": {
        "uz_lat": "⛔ Siz noto'g'ri xatti-harakat tufayli bloklangansiz.\nAdmin bilan bog'laning.",
        "uz_cyr": "⛔ Сиз нотўғри хатти-ҳаракат туфайли блокланган сиз.\nАдмин билан боғланинг.",
        "ru": "⛔ Вы заблокированы из-за нарушений.\nСвяжитесь с администратором.",
    },
    "rate_limit": {
        "uz_lat": "⏳ Bugungi limit tugadi (kuniga {max} ta).\nErtaga qayta urinib ko'ring.",
        "uz_cyr": "⏳ Бугунги лимит тугади (кунига {max} та).\nЭртага қайта уриниб кўринг.",
        "ru": "⏳ Дневной лимит исчерпан ({max} отзывов в день).\nПопробуйте завтра.",
    },
    "toxic_warning": {
        "uz_lat": (
            "⚠️ <b>Ogohlantirish!</b>\n\n"
            "Xabaringizda noto'g'ri so'zlar aniqlandi.\n"
            "Iltimos, hurmatli munosabatda bo'ling.\n\n"
            "🔴 Ogohlantirish: {wc}/{max}\n"
            "Yana {remaining} marta ogohlantirish — blok."
        ),
        "uz_cyr": (
            "⚠️ <b>Огоҳлантириш!</b>\n\n"
            "Хабарингизда нотўғри сўзлар аниқланди.\n"
            "Илтимос, ҳурматли муносабатда бўлинг.\n\n"
            "🔴 Огоҳлантириш: {wc}/{max}\n"
            "Яна {remaining} марта огоҳлантириш — блок."
        ),
        "ru": (
            "⚠️ <b>Предупреждение!</b>\n\n"
            "В вашем сообщении обнаружена ненормативная лексика.\n"
            "Пожалуйста, соблюдайте уважительный тон.\n\n"
            "🔴 Предупреждение: {wc}/{max}\n"
            "Ещё {remaining} предупреждений — блокировка."
        ),
    },
    "toxic_banned": {
        "uz_lat": "⛔ Siz {max} marta ogohlantirildingiz.\nHisobingiz bloklandi. Admin bilan bog'laning.",
        "uz_cyr": "⛔ Сиз {max} марта огоҳлантирилдингиз.\nҲисобингиз блокланди. Админ билан боғланинг.",
        "ru": "⛔ Вы получили {max} предупреждений.\nВаш аккаунт заблокирован. Свяжитесь с администратором.",
    },

    # ── Catch-all ────────────────────────────────────────────────
    "catch_all": {
        "uz_lat": "Feedback qoldirish uchun /start bosing 👇",
        "uz_cyr": "Фидбек қолдириш учун /start босинг 👇",
        "ru": "Чтобы оставить отзыв, нажмите /start 👇",
    },
    "btn_write_feedback": {
        "uz_lat": "📝 Feedback yozish",
        "uz_cyr": "📝 Фидбек ёзиш",
        "ru": "📝 Написать отзыв",
    },

    # ── Xatolar ──────────────────────────────────────────────────
    "voice_error": {
        "uz_lat": "⚠️ Xatolik yuz berdi. Iltimos, matn shaklida yozing.",
        "uz_cyr": "⚠️ Хатолик юз берди. Илтимос, матн шаклида ёзинг.",
        "ru": "⚠️ Произошла ошибка. Пожалуйста, напишите текстом.",
    },
    "text_error": {
        "uz_lat": "⚠️ Xatolik yuz berdi. Keyinroq qayta urinib ko'ring.",
        "uz_cyr": "⚠️ Хатолик юз берди. Кейинроқ қайта уриниб кўринг.",
        "ru": "⚠️ Произошла ошибка. Попробуйте позже.",
    },
}


# STT til kodlari
STT_LANGUAGES = {
    "uz_lat": "uz-UZ",
    "uz_cyr": "uz-UZ",
    "ru": "ru-RU",
}


def t(key: str, lang: str = "uz_lat", **kwargs) -> str:
    """
    Tarjimani olish.
    
    Masalan: t("welcome", "ru", name="Ali", center="Ilmhub")
    """
    msg = TRANSLATIONS.get(key, {}).get(lang)
    if not msg:
        # Fallback: lotin o'zbek
        msg = TRANSLATIONS.get(key, {}).get("uz_lat", f"[{key}]")
    
    if kwargs:
        try:
            msg = msg.format(**kwargs)
        except (KeyError, IndexError):
            pass
    
    return msg
