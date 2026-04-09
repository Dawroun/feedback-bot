"""
O'quv Markazi Feedback Bot (v3 — ko'p tilli)
"""

import os, logging, asyncio
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from speech_to_text import transcribe_voice
from analyzer import analyze_feedback, generate_daily_report
from database import Database
from moderation import ModerationSystem
from translations import t, STT_LANGUAGES

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

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
    raise ValueError("BOT_TOKEN kerak!")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)
db = Database("feedbacks.db")
moderator = ModerationSystem(db, max_daily=MAX_DAILY, max_warnings=MAX_WARNINGS)
VOICE_DIR = Path("voices")
VOICE_DIR.mkdir(exist_ok=True)


class FeedbackFlow(StatesGroup):
    choosing_language = State()
    choosing_anonymous = State()
    choosing_course = State()
    waiting_feedback = State()


# ── Keyboards ────────────────────────────────────────────────────────

def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'zbekcha", callback_data="lang_uz_lat")],
        [InlineKeyboardButton(text="\u040e\u0437\u0431\u0435\u043a\u0447\u0430", callback_data="lang_uz_cyr")],
        [InlineKeyboardButton(text="\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a", callback_data="lang_ru")],
    ])

def anonymous_keyboard(lang):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_show_name", lang), callback_data="anon_no"),
        InlineKeyboardButton(text=t("btn_anonymous", lang), callback_data="anon_yes"),
    ]])

def course_keyboard(lang):
    buttons = []
    row = []
    for i, course in enumerate(COURSES):
        row.append(InlineKeyboardButton(text=course, callback_data=f"course_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text=t("btn_general", lang), callback_data="course_general")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def again_keyboard(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_again", lang), callback_data="again")]
    ])

def satisfaction_keyboard(fid, lang):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_satisfied", lang), callback_data=f"satisfied_{fid}"),
        InlineKeyboardButton(text=t("btn_unsatisfied", lang), callback_data=f"unsatisfied_{fid}"),
    ]])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4ca Statistika", callback_data="admin_stats"),
         InlineKeyboardButton(text="\U0001f4cb Hisobot", callback_data="admin_report")],
        [InlineKeyboardButton(text="\U0001f4e5 Export CSV", callback_data="admin_export"),
         InlineKeyboardButton(text="\U0001f310 Dashboard", callback_data="admin_dashboard")],
    ])


# ── /start ───────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    db.upsert_user(message.from_user.id, message.from_user.username,
                   message.from_user.first_name, message.from_user.last_name)
    await state.clear()
    if db.is_banned(message.from_user.id):
        await message.answer(t("banned", "uz_lat"))
        return
    await message.answer(
        "\U0001f310 Tilni tanlang / \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a / \u0422\u0438\u043b\u043d\u0438 \u0442\u0430\u043d\u043b\u0430\u043d\u0433",
        reply_markup=language_keyboard(),
    )
    await state.set_state(FeedbackFlow.choosing_language)


@router.callback_query(F.data.startswith("lang_"))
async def on_language_choice(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.replace("lang_", "")
    await state.update_data(lang=lang)
    user = callback.from_user
    if db.is_banned(user.id):
        await callback.message.edit_text(t("banned", lang))
        return
    await callback.message.edit_text(
        t("welcome", lang, name=user.first_name, center=CENTER_NAME),
        parse_mode=ParseMode.HTML,
        reply_markup=anonymous_keyboard(lang),
    )
    await state.set_state(FeedbackFlow.choosing_anonymous)
    await callback.answer()


@router.callback_query(F.data.startswith("anon_"))
async def on_anonymous_choice(callback: CallbackQuery, state: FSMContext):
    is_anon = callback.data == "anon_yes"
    data = await state.get_data()
    lang = data.get("lang", "uz_lat")
    await state.update_data(is_anonymous=is_anon)
    label = t("btn_anonymous", lang) if is_anon else f"\U0001f464 {callback.from_user.first_name}"
    await callback.message.edit_text(
        t("anon_chosen", lang, label=label),
        parse_mode=ParseMode.HTML,
        reply_markup=course_keyboard(lang),
    )
    await state.set_state(FeedbackFlow.choosing_course)
    await callback.answer()


@router.callback_query(F.data.startswith("course_"))
async def on_course_choice(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz_lat")
    cdata = callback.data
    if cdata == "course_general":
        course = "Umumiy"
    else:
        idx = int(cdata.split("_")[1])
        course = COURSES[idx] if idx < len(COURSES) else "Umumiy"
    await state.update_data(course=course)
    remaining = moderator.get_remaining_today(callback.from_user.id)
    await callback.message.edit_text(
        t("course_chosen", lang, course=course, remaining=remaining),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(FeedbackFlow.waiting_feedback)
    await callback.answer()


# ── Voice feedback ───────────────────────────────────────────────────

@router.message(FeedbackFlow.waiting_feedback, F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    user = message.from_user
    fsm = await state.get_data()
    lang = fsm.get("lang", "uz_lat")
    is_anon = fsm.get("is_anonymous", False)
    course = fsm.get("course", "Umumiy")

    msg = await message.answer(t("voice_received", lang))
    ogg_path = VOICE_DIR / f"{user.id}_{message.message_id}.ogg"

    try:
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, ogg_path)
        stt_lang = STT_LANGUAGES.get(lang, "uz-UZ")
        text = await transcribe_voice(str(ogg_path), language=stt_lang)
        if not text:
            await msg.edit_text(t("voice_unclear", lang))
            return

        mod = await moderator.process_moderation(user.id, text, GROQ_API_KEY)
        if not mod['allowed']:
            await _handle_mod_block(msg, mod, state, lang)
            return

        analysis = await analyze_feedback(text, GROQ_API_KEY)
        fb_id = db.save_feedback(
            user_id=user.id, text=text, is_anonymous=is_anon,
            course=course, sentiment=analysis['sentiment'],
            ai_summary=analysis.get('summary', ''),
            topics=analysis.get('topics', ''),
            urgency=analysis.get('urgency', 'low'),
            source_type="voice",
        )

        resp_key = f"response_{analysis['sentiment']}"
        await msg.edit_text(
            t(resp_key, lang, course=course, center=CENTER_NAME),
            parse_mode=ParseMode.HTML,
            reply_markup=again_keyboard(lang),
        )

        if analysis.get('sentiment') == 'negative' or analysis.get('urgency') == 'high':
            db.create_followup(fb_id, user.id)
            db.save_followup_lang(fb_id, lang)
            await _notify_admins(user, text, analysis, course, is_anon, fb_id)
    except Exception as e:
        logger.error(f"Voice error: {e}")
        await msg.edit_text(t("voice_error", lang))
    finally:
        if ogg_path.exists():
            ogg_path.unlink(missing_ok=True)
        await state.clear()


# ── Text feedback ────────────────────────────────────────────────────

@router.message(FeedbackFlow.waiting_feedback, F.text)
async def handle_text(message: types.Message, state: FSMContext):
    user = message.from_user
    text = message.text.strip()
    fsm = await state.get_data()
    lang = fsm.get("lang", "uz_lat")
    is_anon = fsm.get("is_anonymous", False)
    course = fsm.get("course", "Umumiy")

    if len(text) < 5:
        await message.answer(t("text_too_short", lang))
        return

    msg = await message.answer(t("text_received", lang))
    try:
        mod = await moderator.process_moderation(user.id, text, GROQ_API_KEY)
        if not mod['allowed']:
            await _handle_mod_block(msg, mod, state, lang)
            return

        analysis = await analyze_feedback(text, GROQ_API_KEY)
        fb_id = db.save_feedback(
            user_id=user.id, text=text, is_anonymous=is_anon,
            course=course, sentiment=analysis['sentiment'],
            ai_summary=analysis.get('summary', ''),
            topics=analysis.get('topics', ''),
            urgency=analysis.get('urgency', 'low'),
            source_type="text",
        )

        resp_key = f"response_{analysis['sentiment']}"
        await msg.edit_text(
            t(resp_key, lang, course=course, center=CENTER_NAME),
            parse_mode=ParseMode.HTML,
            reply_markup=again_keyboard(lang),
        )

        if analysis.get('sentiment') == 'negative' or analysis.get('urgency') == 'high':
            db.create_followup(fb_id, user.id)
            db.save_followup_lang(fb_id, lang)
            await _notify_admins(user, text, analysis, course, is_anon, fb_id)
    except Exception as e:
        logger.error(f"Text error: {e}")
        await msg.edit_text(t("text_error", lang))
    finally:
        await state.clear()


# ── Moderation block ─────────────────────────────────────────────────

async def _handle_mod_block(msg, mod, state, lang):
    reason = mod['reason']
    if reason == "banned":
        await msg.edit_text(t("banned", lang))
    elif reason == "rate_limit":
        await msg.edit_text(t("rate_limit", lang, max=MAX_DAILY))
    elif reason == "toxic":
        wc = mod['warning_count']
        rem = MAX_WARNINGS - wc
        if mod['is_banned']:
            await msg.edit_text(t("toxic_banned", lang, max=MAX_WARNINGS))
        else:
            await msg.edit_text(t("toxic_warning", lang, wc=wc, max=MAX_WARNINGS, remaining=rem), parse_mode=ParseMode.HTML)
    await state.clear()


# ── Admin notification ───────────────────────────────────────────────

async def _notify_admins(user, text, analysis, course, is_anon, fb_id):
    sender = "Anonim" if is_anon else f"{user.first_name} (@{user.username or '?'})"
    emoji = "\U0001f6a8" if analysis.get('urgency') == 'high' else "\u26a0\ufe0f"
    alert = (
        f"{emoji} <b>YANGI SALBIY FEEDBACK #{fb_id}</b>\n"
        f"\U0001f464 Kimdan: {sender}\n"
        f"\U0001f4da Kurs: {course}\n"
        f"\U0001f4dd Matn: {text[:300]}\n"
        f"\U0001f916 Xulosa: {analysis.get('summary', '-')}\n"
        f"\U0001f525 Muhimlik: {analysis.get('urgency', 'low')}\n"
        f"\U0001f4c5 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"\U0001f4de <b>BU OTA-ONAGA QAYTA ALOQAGA CHIQISH SHART!</b>\n"
        f"<code>/reply {fb_id} Javob matni</code>\n"
    )
    if is_anon:
        alert += f"\n\U0001f50d Kimligini bilish: /unmask {fb_id}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, alert, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Admin {admin_id}: {e}")


# ── Admin commands ───────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("\U0001f527 <b>Admin panel</b>", parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    stats = db.get_stats()
    cs = db.get_course_stats()
    txt = (f"\U0001f4ca <b>Statistika</b>\nJami: <b>{stats['total']}</b>\n"
           f"\u2705 Ijobiy: <b>{stats['positive']}</b>\n\u26a0\ufe0f Salbiy: <b>{stats['negative']}</b>\n"
           f"\u2796 Neytral: <b>{stats['neutral']}</b>\n\U0001f3a4 Ovozli: <b>{stats['voice_count']}</b>\n\u270f\ufe0f Matnli: <b>{stats['text_count']}</b>\n")
    if cs:
        txt += "\n\U0001f4da <b>Kurslar:</b>\n"
        for c in cs:
            txt += f"  \u2022 {c['course']}: {c['total']} (\u2705{c['positive']} \u26a0\ufe0f{c['negative']})\n"
    await message.answer(txt, parse_mode=ParseMode.HTML)

@router.message(Command("unmask"))
async def cmd_unmask(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Foydalanish: /unmask <id>")
        return
    fb = db.get_feedback_by_id(int(parts[1]))
    if not fb:
        await message.answer("\u274c Topilmadi.")
        return
    ui = db.get_user_info(fb['user_id'])
    uname = ui.get('username') or "yo'q"
    banned = "Ha" if ui.get('is_banned') else "Yo'q"
    await message.answer(
        f"\U0001f50d <b>#{parts[1]}</b>\nID: <code>{fb['user_id']}</code>\n"
        f"Ism: {ui.get('first_name','?')}\nUsername: @{uname}\nBan: {banned}\n\n{fb['text'][:500]}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f6ab 1kun ban", callback_data=f"ban_{fb['user_id']}_1"),
             InlineKeyboardButton(text="\U0001f6ab Doimiy", callback_data=f"ban_{fb['user_id']}_0")],
            [InlineKeyboardButton(text="\u2705 Unban", callback_data=f"unban_{fb['user_id']}")]
        ]),
    )

@router.callback_query(F.data.startswith("ban_"))
async def on_ban(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    p = cb.data.split("_"); uid = int(p[1]); d = int(p[2])
    db.ban_user(uid, "Admin ban", days=d if d > 0 else None)
    await cb.answer(f"Bloklandi! {'Doimiy' if d==0 else f'{d} kunga'}")

@router.callback_query(F.data.startswith("unban_"))
async def on_unban(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    db.unban_user(int(cb.data.split("_")[1]))
    await cb.answer("Blokdan chiqarildi!")

@router.message(Command("resetwarnings"))
async def cmd_reset(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) < 2: await message.answer("/resetwarnings <user_id>"); return
    db.reset_warnings(int(parts[1]))
    await message.answer(f"\u2705 Tozalandi.")

@router.message(Command("reply"))
async def cmd_reply(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("/reply <id> <javob>")
        return
    fb_id = int(parts[1])
    reply_text = parts[2].strip()
    fb = db.get_feedback_by_id(fb_id)
    if not fb: await message.answer("\u274c Topilmadi."); return
    fu = db.get_followup_by_feedback(fb_id)
    if not fu: await message.answer("\u274c Follow-up yo'q."); return
    db.set_followup_reply(fb_id, reply_text)
    parent_lang = db.get_followup_lang(fb_id) or "uz_lat"
    try:
        await bot.send_message(
            fu['parent_user_id'],
            t("followup_message", parent_lang, reply=reply_text),
            parse_mode=ParseMode.HTML,
            reply_markup=satisfaction_keyboard(fu['id'], parent_lang),
        )
        await message.answer(f"\u2705 #{fb_id} egasiga yuborildi!")
    except Exception as e:
        await message.answer(f"\u26a0\ufe0f {e}")

@router.message(Command("report"))
async def cmd_report(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    await message.answer("\U0001f4ca Tayyorlanmoqda...")
    fbs = db.get_feedbacks_since(hours=24)
    r = await generate_daily_report(fbs, GROQ_API_KEY)
    await message.answer(f"\U0001f4cb <b>Hisobot</b>\n\n{r}", parse_mode=ParseMode.HTML)

@router.message(Command("export"))
async def cmd_export(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    fp = db.export_csv("export.csv")
    if fp and os.path.exists(fp):
        await message.answer_document(FSInputFile(fp, filename="feedbacks.csv"))
    else:
        await message.answer("Ma'lumot yo'q.")

@router.callback_query(F.data == "admin_stats")
async def a_stats(cb: CallbackQuery):
    cb.message.from_user = cb.from_user; await cmd_stats(cb.message); await cb.answer()
@router.callback_query(F.data == "admin_report")
async def a_report(cb: CallbackQuery):
    cb.message.from_user = cb.from_user; await cmd_report(cb.message); await cb.answer()
@router.callback_query(F.data == "admin_export")
async def a_export(cb: CallbackQuery):
    cb.message.from_user = cb.from_user; await cmd_export(cb.message); await cb.answer()
@router.callback_query(F.data == "admin_dashboard")
async def a_dash(cb: CallbackQuery):
    await cb.answer("Dashboard: server_ip:5050", show_alert=True)


# ── Satisfaction ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("satisfied_"))
async def on_satisfied(cb: CallbackQuery):
    fid = int(cb.data.split("_")[1])
    db.set_followup_satisfied(fid, True)
    lang = db.get_followup_lang_by_id(fid) or "uz_lat"
    await cb.message.edit_text(t("satisfied_response", lang, center=CENTER_NAME), parse_mode=ParseMode.HTML)
    await cb.answer()
    for a in ADMIN_IDS:
        try: await bot.send_message(a, f"\u2705 Follow-up #{fid}: <b>MAMNUN</b>", parse_mode=ParseMode.HTML)
        except: pass

@router.callback_query(F.data.startswith("unsatisfied_"))
async def on_unsatisfied(cb: CallbackQuery, state: FSMContext):
    fid = int(cb.data.split("_")[1])
    db.set_followup_satisfied(fid, False)
    lang = db.get_followup_lang_by_id(fid) or "uz_lat"
    await cb.message.edit_text(t("unsatisfied_response", lang), reply_markup=anonymous_keyboard(lang))
    await state.set_state(FeedbackFlow.choosing_anonymous)
    await state.update_data(lang=lang)
    await cb.answer()
    for a in ADMIN_IDS:
        try: await bot.send_message(a, f"\u26a0\ufe0f Follow-up #{fid}: <b>MAMNUN EMAS</b>", parse_mode=ParseMode.HTML)
        except: pass


# ── Again + Catch-all ────────────────────────────────────────────────

@router.callback_query(F.data == "again")
async def on_again(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    db.upsert_user(cb.from_user.id, cb.from_user.username, cb.from_user.first_name, cb.from_user.last_name)
    if db.is_banned(cb.from_user.id):
        await cb.message.edit_text("\u26d4 Bloklangansiz.")
        return
    await cb.message.edit_text(
        "\U0001f310 Tilni tanlang / \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a / \u0422\u0438\u043b\u043d\u0438 \u0442\u0430\u043d\u043b\u0430\u043d\u0433",
        reply_markup=language_keyboard(),
    )
    await state.set_state(FeedbackFlow.choosing_language)
    await cb.answer()

@router.message(F.text & ~F.text.startswith("/"))
async def catch_text(message: types.Message):
    await message.answer("Feedback uchun /start bosing",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f4dd Feedback", callback_data="again")]]))

@router.message(F.voice)
async def catch_voice(message: types.Message):
    await message.answer("Avval /start bosing",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f4dd Feedback", callback_data="again")]]))


# ── Scheduler + Main ─────────────────────────────────────────────────

async def daily_report_scheduler():
    while True:
        now = datetime.now()
        target = now.replace(hour=REPORT_HOUR, minute=REPORT_MINUTE, second=0)
        if now >= target:
            target = target.replace(day=target.day + 1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            fbs = db.get_feedbacks_since(hours=24)
            r = await generate_daily_report(fbs, GROQ_API_KEY)
            for a in ADMIN_IDS:
                try: await bot.send_message(a, f"\U0001f4cb <b>Hisobot - {datetime.now().strftime('%Y-%m-%d')}</b>\n\n{r}", parse_mode=ParseMode.HTML)
                except: pass
        except Exception as e:
            logger.error(f"Report error: {e}")

async def main():
    db.create_tables()
    logger.info(f"\U0001f680 {CENTER_NAME} Bot ishga tushdi! Tillar: uz_lat, uz_cyr, ru")
    asyncio.create_task(daily_report_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
