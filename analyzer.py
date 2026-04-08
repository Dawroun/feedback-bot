"""
AI Feedback Tahlil moduli
=========================
Groq API (bepul) yordamida feedbacklarni tahlil qiladi:
- Sentiment (positive / negative / neutral)
- Xulosa (summary)
- Mavzular (topics)
- Kunlik / haftalik hisobot generatsiya
"""

import json
import logging
import httpx

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Sen o'quv markazi uchun ota-onalardan kelgan feedbacklarni 
tahlil qiluvchi AI yordamchisan.

Vazifang:
1. Feedbackning sentimentini aniqla (positive, negative, neutral)
2. Qisqa xulosa yoz (1-2 gap, o'zbek tilida)
3. Asosiy mavzularni aniqla
4. Muhimlik darajasini belgilab ber

FAQAT quyidagi JSON formatda javob ber, boshqa hech narsa yozma:

{"sentiment":"positive|negative|neutral","summary":"Qisqa xulosa o'zbek tilida","topics":"mavzu1, mavzu2","urgency":"low|medium|high"}

Qoidalar:
- Shikoyat, norozilik, muammo → "negative"
- Maqtov, minnatdorchilik → "positive"
- Oddiy savol yoki neytral → "neutral"
- urgency "high": jiddiy muammolar (bolaning xavfsizligi, zo'ravonlik, kamsitish)
- urgency "medium": ta'lim sifati, o'qituvchi bilan muammo
- urgency "low": umumiy fikr, taklif
- Har doim o'zbek tilida javob ber"""


async def analyze_feedback(text: str, groq_api_key: str) -> dict:
    """
    Feedbackni AI yordamida tahlil qilish.
    
    Returns:
        {"sentiment", "summary", "topics", "urgency"}
    """
    if not groq_api_key:
        return _simple_analysis(text)

    try:
        return await _groq_analyze(text, groq_api_key)
    except Exception as e:
        logger.error(f"Groq API xatosi: {e}")
        return _simple_analysis(text)


async def _groq_analyze(text: str, api_key: str) -> dict:
    """Groq API orqali tahlil (bepul, tez)"""
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "max_tokens": 300,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": ANALYSIS_PROMPT},
                    {"role": "user", "content": f'Feedback: "{text}"'},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # JSON parse (ba'zan markdown block ichida keladi)
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]

        result = json.loads(content)

        if result.get("sentiment") not in ("positive", "negative", "neutral"):
            result["sentiment"] = "neutral"
        if result.get("urgency") not in ("low", "medium", "high"):
            result["urgency"] = "low"

        return result


def _simple_analysis(text: str) -> dict:
    """API bo'lmaganda oddiy keyword-based tahlil (fallback)"""
    text_lower = text.lower()

    negative_words = [
        "yomon", "muammo", "shikoyat", "norozi", "buzilgan",
        "ishlamayapti", "past", "sifatsiz", "kech", "qo'pol",
        "tushunmaydi", "e'tiborsiz", "xafa", "qoniqmadim",
        "urish", "kamsitish", "dahshat", "noto'g'ri", "achchiq",
    ]
    positive_words = [
        "yaxshi", "ajoyib", "zo'r", "rahmat", "mamnun",
        "qoniqaman", "a'lo", "chiroyli", "professional",
        "mehribon", "toza", "tartibli", "barakalla",
        "minnatdor", "quvonaman", "yoqadi",
    ]

    neg = sum(1 for w in negative_words if w in text_lower)
    pos = sum(1 for w in positive_words if w in text_lower)

    sentiment = "negative" if neg > pos else "positive" if pos > neg else "neutral"

    return {
        "sentiment": sentiment,
        "summary": text[:150] + ("..." if len(text) > 150 else ""),
        "topics": "avtomatik aniqlanmadi",
        "urgency": "medium" if sentiment == "negative" else "low",
    }


async def generate_daily_report(feedbacks: list, groq_api_key: str) -> str:
    """Kunlik umumiy hisobot generatsiya qilish"""
    if not feedbacks:
        return "📭 Bugun feedback kelmadi."

    if not groq_api_key:
        # Oddiy statistik hisobot
        pos = sum(1 for f in feedbacks if f['sentiment'] == 'positive')
        neg = sum(1 for f in feedbacks if f['sentiment'] == 'negative')
        neu = sum(1 for f in feedbacks if f['sentiment'] == 'neutral')
        return (
            f"📊 Kunlik hisobot\n"
            f"Jami: {len(feedbacks)} ta feedback\n"
            f"✅ Ijobiy: {pos} | ⚠️ Salbiy: {neg} | ➖ Neytral: {neu}"
        )

    fb_text = "\n".join(
        f"- [{f['sentiment']}] [{f.get('course','?')}] {f['text'][:150]}"
        for f in feedbacks[:30]  # Max 30 ta (token limit)
    )

    prompt = f"""Bugun kelgan {len(feedbacks)} ta ota-ona feedbackini tahlil qil.

FEEDBACKLAR:
{fb_text}

O'zbek tilida qisqa hisobot yoz:
1. UMUMIY BAHO (1 gap)
2. ASOSIY MUAMMOLAR (agar bor bo'lsa)
3. IJOBIY TOMONLAR
4. TAVSIYALAR (1-2 ta, aniq)
5. MUHIM (zudlik bilan hal qilish kerak bo'lgan narsa, agar bor bo'lsa)

Qisqa va aniq yoz, ortiqcha gap bo'lmasin."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "max_tokens": 1000,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Daily report xatosi: {e}")
        return f"Hisobot generatsiya qilishda xatolik: {e}"
