"""
O'quv Markazi Feedback Bot
===========================
Ota-onalardan ovozli/matnli feedback yig'ish,
AI tahlil, moderatsiya, admin hisobot.
"""

import os
import logging
import asyncio
from datetime import datetime, time
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from speech_to_text import transcribe_voice
from analyzer import analyze_feedback, generate_daily_report
from database import Database
from moderation import ModerationSystem

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CENTER_NAME = os.getenv("CENTER_NAME", "O'quv Markazi")
COURSES = [c.strip() for c in os.getenv("COURSES", "Umumiy").split(",")]
MAX_DAILY = int(os.getenv("MAX_DAILY_FEEDBACKS", "5"))
MAX_WARNINGS = int(os.getenv("MAX_WARNINGS", "3"))
REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "20"))
REPORT_MINUTE = int(os.getenv("DAILY_REPORT_MINUTE", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN sozlamasi kerak! .env faylni tekshiring.")

# ── Bot & DB ─────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

db = Database("feedbacks.db")
moderator = ModerationSystem(db, max_daily=MAX_DAILY, max_warnings=MAX_WARNINGS)

VOICE_DIR = Path("voices")
VOICE_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════
#  FSM STATES (feedback jarayoni)
# ══════════════════════════════════════════════════════════════════════

class FeedbackFlow(StatesGroup):
    choosing_anonymous = State()
    choosing_course = State()
    waiting_feedback = State()


# ══════════════════════════════════════════════════════════════════════
#  KEYBOARD BUILDERS
# ══════════════════════════════════════════════════════════════════════

def anonymous_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Ismim ko'rinsin", callback_data="anon_no"),
            InlineKeyboardButton(text="🕶 Anonim", callback_data="anon_yes"),
        ]
    ])


def course_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, course in enumerate(COURSES):
        row.append(InlineKeyboardButton(text=course, callback_data=f"course_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📋 Umumiy fikr", callback_data="course_general")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="📋 Hisobot", callback_data="admin_report"),
        ],
        [
            InlineKeyboardButton(text="📥 Export CSV", callback_data="admin_export"),
            InlineKeyboardButton(text="🌐 Dashboard", callback_data="admin_dashboard"),
        ],
    ])


# ══════════════════════════════════════════════════════════════════════
#  /start — ASOSIY BOSHLASH
# ══════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user
    db.upsert_user(user.id, user.username, user.first_name, user.last_name)

    # Ban tekshiruvi
    if db.is_banned(user.id):
        await message.answer(
            "⛔ Siz noto'g'ri xatti-harakat tufayli bloklangansiz.\n"
            "Agar bu xato deb hisoblasangiz, admin bilan bog'laning."
        )
        return

    welcome = (
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        f"<b>{CENTER_NAME}</b> feedback botiga xush kelibsiz!\n\n"
        "Siz bu yerda o'quv markazi haqida fikr-mulohazangizni "
        "qoldirishingiz mumkin.\n\n"
        "📌 Ism ko'rinsinmi yoki anonim bo'lasizmi?"
    )
    await message.answer(welcome, parse_mode=ParseMode.HTML,
                         reply_markup=anonymous_keyboard())
    await state.set_state(FeedbackFlow.choosing_anonymous)


# ══════════════════════════════════════════════════════════════════════
#  QADAM 1: Anonim yoki ismli
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("anon_"))
async def on_anonymous_choice(callback: CallbackQuery, state: FSMContext):
    is_anon = callback.data == "anon_yes"
    await state.update_data(is_anonymous=is_anon)

    label = "🕶 Anonim" if is_anon else f"👤 {callback.from_user.first_name}"
    await callback.message.edit_text(
        f"Tanlandi: <b>{label}</b>\n\n"
        "📚 Endi qaysi kurs haqida fikr bildirasiz?",
        parse_mode=ParseMode.HTML,
        reply_markup=course_keyboard(),
    )
    await state.set_state(FeedbackFlow.choosing_course)
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════
#  QADAM 2: Kurs tanlash
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("course_"))
async def on_course_choice(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "course_general":
        course = "Umumiy"
    else:
        idx = int(data.split("_")[1])
        course = COURSES[idx] if idx < len(COURSES) else "Umumiy"

    await state.update_data(course=course)

    remaining = moderator.get_remaining_today(callback.from_user.id)

    await callback.message.edit_text(
        f"📚 Kurs: <b>{course}</b>\n\n"
        "Endi fikringizni yuboring:\n"
        "🎤 <b>Ovozli habar</b> yoki ✏️ <b>Matn</b> yozing.\n\n"
        f"💡 Bugun yana {remaining} ta feedback yuborishingiz mumkin.",
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(FeedbackFlow.waiting_feedback)
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════
#  QADAM 3: OVOZLI FEEDBACK
# ══════════════════════════════════════════════════════════════════════

@router.message(FeedbackFlow.waiting_feedback, F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    user = message.from_user
    fsm_data = await state.get_data()
    is_anonymous = fsm_data.get("is_anonymous", False)
    course = fsm_data.get("course", "Umumiy")

    processing_msg = await message.answer("🎤 Ovozli habar qabul qilindi. Tahlil qilinmoqda...")

    ogg_path = VOICE_DIR / f"{user.id}_{message.message_id}.ogg"

    try:
        # 1. Faylni yuklash
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, ogg_path)

        # 2. STT
        text = await transcribe_voice(str(ogg_path))
        if not text:
            await processing_msg.edit_text(
                "⚠️ Ovozli habar tushunarsiz chiqdi.\n"
                "Iltimos, aniqroq gapiring yoki matn yozing."
            )
            return

        # 3. Moderatsiya
        mod_result = await moderator.process_moderation(user.id, text, GROQ_API_KEY)
        if not mod_result['allowed']:
            await _handle_moderation_block(processing_msg, mod_result, state)
            return

        # 4. AI tahlil
        analysis = await analyze_feedback(text, GROQ_API_KEY)

        # 5. Bazaga saqlash
        fb_id = db.save_feedback(
            user_id=user.id, text=text, is_anonymous=is_anonymous,
            course=course, sentiment=analysis['sentiment'],
            ai_summary=analysis.get('summary', ''),
            topics=analysis.get('topics', ''),
            urgency=analysis.get('urgency', 'low'),
            source_type="voice",
        )

        await processing_msg.edit_text(
            "✅ Fikr-mulohazangiz qabul qilindi!\n"
            "Rahmat, sizning fikringiz biz uchun juda muhim! 🙏\n\n"
            "Yana feedback qoldirmoqchimisiz? /start bosing."
        )

        # 6. Admin ogohlantirish
        if analysis.get('sentiment') == 'negative' or analysis.get('urgency') == 'high':
            await _notify_admins(user, text, analysis, course, is_anonymous, fb_id)

    except Exception as e:
        logger.error(f"Voice error: {e}")
        await processing_msg.edit_text(
            "⚠️ Xatolik yuz berdi. Iltimos, matn shaklida yozing."
        )
    finally:
        if ogg_path.exists():
            ogg_path.unlink(missing_ok=True)
        await state.clear()


# ══════════════════════════════════════════════════════════════════════
#  QADAM 3: MATNLI FEEDBACK
# ══════════════════════════════════════════════════════════════════════

@router.message(FeedbackFlow.waiting_feedback, F.text)
async def handle_text_feedback(message: types.Message, state: FSMContext):
    user = message.from_user
    text = message.text.strip()
    fsm_data = await state.get_data()
    is_anonymous = fsm_data.get("is_anonymous", False)
    course = fsm_data.get("course", "Umumiy")

    if len(text) < 5:
        await message.answer("✏️ Iltimos, batafsil yozing (kamida 5 belgi).")
        return

    processing_msg = await message.answer("📝 Fikringiz qabul qilindi. Tahlil qilinmoqda...")

    try:
        # 1. Moderatsiya
        mod_result = await moderator.process_moderation(user.id, text, GROQ_API_KEY)
        if not mod_result['allowed']:
            await _handle_moderation_block(processing_msg, mod_result, state)
            return

        # 2. AI tahlil
        analysis = await analyze_feedback(text, GROQ_API_KEY)

        # 3. Bazaga saqlash
        fb_id = db.save_feedback(
            user_id=user.id, text=text, is_anonymous=is_anonymous,
            course=course, sentiment=analysis['sentiment'],
            ai_summary=analysis.get('summary', ''),
            topics=analysis.get('topics', ''),
            urgency=analysis.get('urgency', 'low'),
            source_type="text",
        )

        await processing_msg.edit_text(
            "✅ Fikr-mulohazangiz qabul qilindi!\n"
            "Rahmat! 🙏\n\n"
            "Yana feedback qoldirmoqchimisiz? /start bosing."
        )

        if analysis.get('sentiment') == 'negative' or analysis.get('urgency') == 'high':
            await _notify_admins(user, text, analysis, course, is_anonymous, fb_id)

    except Exception as e:
        logger.error(f"Text error: {e}")
        await processing_msg.edit_text("⚠️ Xatolik yuz berdi. Keyinroq qayta urinib ko'ring.")
    finally:
        await state.clear()


# ══════════════════════════════════════════════════════════════════════
#  MODERATSIYA BLOKLASH XABARLARI
# ══════════════════════════════════════════════════════════════════════

async def _handle_moderation_block(msg: types.Message, mod_result: dict,
                                    state: FSMContext):
    reason = mod_result['reason']

    if reason == "banned":
        await msg.edit_text(
            "⛔ Siz noto'g'ri xatti-harakat tufayli bloklangansiz.\n"
            "Admin bilan bog'laning."
        )
    elif reason == "rate_limit":
        await msg.edit_text(
            f"⏳ Bugungi limit tugadi (kuniga {MAX_DAILY} ta).\n"
            "Ertaga qayta urinib ko'ring."
        )
    elif reason == "toxic":
        wc = mod_result['warning_count']
        remaining = MAX_WARNINGS - wc

        if mod_result['is_banned']:
            await msg.edit_text(
                f"⛔ Siz {MAX_WARNINGS} marta ogohlantirildingiz.\n"
                "Hisobingiz bloklandi. Admin bilan bog'laning."
            )
        else:
            await msg.edit_text(
                "⚠️ <b>Ogohlantirish!</b>\n\n"
                "Xabaringizda noto'g'ri so'zlar aniqlandi.\n"
                "Iltimos, hurmatli munosabatda bo'ling.\n\n"
                f"🔴 Ogohlantirish: {wc}/{MAX_WARNINGS}\n"
                f"Yana {remaining} marta ogohlantirish — blok.",
                parse_mode=ParseMode.HTML,
            )

    await state.clear()


# ══════════════════════════════════════════════════════════════════════
#  ADMINLARGA XABAR YUBORISH
# ══════════════════════════════════════════════════════════════════════

async def _notify_admins(user, text, analysis, course, is_anonymous, fb_id):
    sender = "Anonim" if is_anonymous else f"{user.first_name} (@{user.username or '?'})"
    emoji = "🚨" if analysis.get('urgency') == 'high' else "⚠️"

    alert = (
        f"{emoji} <b>YANGI SALBIY FEEDBACK #{fb_id}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Kimdan: {sender}\n"
        f"📚 Kurs: {course}\n"
        f"📝 Matn: {text[:300]}\n"
        f"🤖 Xulosa: {analysis.get('summary', '-')}\n"
        f"🏷 Mavzular: {analysis.get('topics', '-')}\n"
        f"🔥 Muhimlik: {analysis.get('urgency', 'low')}\n"
        f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    )

    if is_anonymous:
        alert += f"\n🔍 Ochish uchun: /unmask {fb_id}"

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, alert, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Admin {admin_id} ga xabar yuborilmadi: {e}")


# ══════════════════════════════════════════════════════════════════════
#  ADMIN BUYRUQLARI
# ══════════════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Faqat adminlar uchun.")
        return
    await message.answer(
        "🔧 <b>Admin panel</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_keyboard(),
    )


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Faqat adminlar uchun.")
        return

    stats = db.get_stats()
    course_stats = db.get_course_stats()

    text = (
        "📊 <b>Umumiy Statistika</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Jami: <b>{stats['total']}</b>\n"
        f"✅ Ijobiy: <b>{stats['positive']}</b>\n"
        f"⚠️ Salbiy: <b>{stats['negative']}</b>\n"
        f"➖ Neytral: <b>{stats['neutral']}</b>\n"
        f"🎤 Ovozli: <b>{stats['voice_count']}</b>\n"
        f"✏️ Matnli: <b>{stats['text_count']}</b>\n"
    )

    if stats['total'] > 0:
        pos_pct = stats['positive'] / stats['total'] * 100
        neg_pct = stats['negative'] / stats['total'] * 100
        text += f"\n📈 Ijobiy: {pos_pct:.0f}% | 📉 Salbiy: {neg_pct:.0f}%\n"

    if course_stats:
        text += "\n📚 <b>Kurslar bo'yicha:</b>\n"
        for cs in course_stats:
            text += f"  • {cs['course']}: {cs['total']} ta (✅{cs['positive']} ⚠️{cs['negative']})\n"

    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("unmask"))
async def cmd_unmask(message: types.Message):
    """Anonim feedbackning haqiqiy egasini ko'rsatish"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Faqat adminlar uchun.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Foydalanish: /unmask <feedback_id>\nMasalan: /unmask 45")
        return

    try:
        fb_id = int(parts[1])
    except ValueError:
        await message.answer("⚠️ Noto'g'ri ID. Raqam kiriting.")
        return

    fb = db.get_feedback_by_id(fb_id)
    if not fb:
        await message.answer(f"❌ #{fb_id} raqamli feedback topilmadi.")
        return

    user_info = db.get_user_info(fb['user_id'])
    warnings = db.get_warning_count(fb['user_id'])

    text = (
        f"🔍 <b>Feedback #{fb_id} — Foydalanuvchi ma'lumotlari</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Telegram ID: <code>{fb['user_id']}</code>\n"
        f"👤 Ism: {user_info.get('first_name', '?')} {user_info.get('last_name') or ''}\n"
        f"📱 Username: @{user_info.get('username') or 'yo\'q'}\n"
        f"⚠️ Ogohlantirishlar: {warnings}\n"
        f"🚫 Bloklangan: {'Ha' if user_info.get('is_banned') else 'Yo\\'q'}\n"
        f"\n📝 Feedback: {fb['text'][:500]}\n"
        f"📅 Sana: {fb['created_at']}\n"
    )

    # Ban tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚫 1 kunga ban",
                callback_data=f"ban_{fb['user_id']}_1"
            ),
            InlineKeyboardButton(
                text="🚫 Doimiy ban",
                callback_data=f"ban_{fb['user_id']}_0"
            ),
        ],
        [
            InlineKeyboardButton(
                text="✅ Unban",
                callback_data=f"unban_{fb['user_id']}"
            ),
        ]
    ])

    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(F.data.startswith("ban_"))
async def on_ban(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Faqat adminlar uchun.", show_alert=True)
        return

    parts = callback.data.split("_")
    user_id = int(parts[1])
    days = int(parts[2])

    if days == 0:
        db.ban_user(user_id, "Admin tomonidan doimiy ban")
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ Foydalanuvchi {user_id} doimiy bloklandi.",
            parse_mode=ParseMode.HTML,
        )
    else:
        db.ban_user(user_id, f"Admin tomonidan {days} kunga ban", days=days)
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ Foydalanuvchi {user_id} {days} kunga bloklandi.",
            parse_mode=ParseMode.HTML,
        )
    await callback.answer("Bloklandi!")


@router.callback_query(F.data.startswith("unban_"))
async def on_unban(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Faqat adminlar uchun.", show_alert=True)
        return

    user_id = int(callback.data.split("_")[1])
    db.unban_user(user_id)
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ Foydalanuvchi {user_id} blokdan chiqarildi.",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Blokdan chiqarildi!")


@router.message(Command("report"))
async def cmd_report(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Faqat adminlar uchun.")
        return

    await message.answer("📊 Hisobot tayyorlanmoqda...")
    feedbacks = db.get_feedbacks_since(hours=24)
    report = await generate_daily_report(feedbacks, GROQ_API_KEY)
    await message.answer(f"📋 <b>Kunlik Hisobot</b>\n\n{report}", parse_mode=ParseMode.HTML)


@router.message(Command("export"))
async def cmd_export(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Faqat adminlar uchun.")
        return

    filepath = db.export_csv("export_feedbacks.csv")
    if filepath and os.path.exists(filepath):
        doc = FSInputFile(filepath, filename="feedbacks_report.csv")
        await message.answer_document(doc, caption="📎 Barcha feedbacklar CSV formatida")
    else:
        await message.answer("📭 Export qilish uchun ma'lumot yo'q.")


# Admin callback handlers
@router.callback_query(F.data == "admin_stats")
async def admin_stats_cb(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    # Trigger /stats
    fake_msg = callback.message
    fake_msg.from_user = callback.from_user
    await cmd_stats(fake_msg)
    await callback.answer()


@router.callback_query(F.data == "admin_report")
async def admin_report_cb(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    fake_msg = callback.message
    fake_msg.from_user = callback.from_user
    await cmd_report(fake_msg)
    await callback.answer()


@router.callback_query(F.data == "admin_export")
async def admin_export_cb(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    fake_msg = callback.message
    fake_msg.from_user = callback.from_user
    await cmd_export(fake_msg)
    await callback.answer()


@router.callback_query(F.data == "admin_dashboard")
async def admin_dashboard_cb(callback: CallbackQuery):
    await callback.answer(
        "🌐 Dashboard: serveringiz IP manzili:5050\n"
        "Masalan: http://localhost:5050",
        show_alert=True,
    )


# ══════════════════════════════════════════════════════════════════════
#  KUNLIK HISOBOT (SCHEDULER)
# ══════════════════════════════════════════════════════════════════════

async def daily_report_scheduler():
    """Har kuni belgilangan vaqtda adminga hisobot yuborish"""
    while True:
        now = datetime.now()
        target = now.replace(hour=REPORT_HOUR, minute=REPORT_MINUTE, second=0)
        if now >= target:
            target = target.replace(day=target.day + 1)

        wait_seconds = (target - now).total_seconds()
        logger.info(f"Keyingi hisobot: {target} ({wait_seconds:.0f} soniya)")
        await asyncio.sleep(wait_seconds)

        try:
            feedbacks = db.get_feedbacks_since(hours=24)
            report = await generate_daily_report(feedbacks, GROQ_API_KEY)
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"📋 <b>Kunlik Hisobot — {datetime.now().strftime('%Y-%m-%d')}</b>\n\n{report}",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception as e:
                    logger.error(f"Report to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Daily report error: {e}")


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

async def main():
    db.create_tables()
    logger.info(f"🚀 {CENTER_NAME} Feedback Bot ishga tushdi!")
    logger.info(f"📋 Adminlar: {ADMIN_IDS}")
    logger.info(f"📚 Kurslar: {COURSES}")
    logger.info(f"⏰ Kunlik hisobot: {REPORT_HOUR}:{REPORT_MINUTE:02d}")

    # Kunlik hisobot scheduler'ni ishga tushirish
    asyncio.create_task(daily_report_scheduler())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
