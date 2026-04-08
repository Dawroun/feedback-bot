"""
Moderatsiya moduli
==================
So'kinish filtri, rate limiting, ogohlantirish tizimi.
"""

import re
import logging
from datetime import datetime
from database import Database

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
#  SO'KINISH / HAQORAT SO'ZLARI (o'zbek + rus + ingliz)
#  Bu ro'yxatni kerak bo'lsa kengaytirish mumkin
# ══════════════════════════════════════════════════════════════════════

TOXIC_PATTERNS_UZ = [
    r'\baxmoq\b', r'\beshak\b', r'\bit\b', r'\bharom\b',
    r'\bjinni\b', r'\btentak\b', r'\bsho\'rva\b', r'\bnodon\b',
    r'\bqo\'tir\b', r'\bbeso\'naqay\b', r'\bqo\'qir\b',
    r'\bkal\b', r'\bsig\'ir\b', r'\bcho\'chqa\b',
]

TOXIC_PATTERNS_RU = [
    r'\bблять?\b', r'\bсука\b', r'\bхуй\b', r'\bпизд',
    r'\bебат?\b', r'\bнахуй\b', r'\bпидор\b', r'\bмудак\b',
    r'\bдебил\b', r'\bидиот\b', r'\bтупой?\b', r'\bдурак\b',
    r'\bблин\b', r'\bчёрт\b', r'\bгавно\b',
]

TOXIC_PATTERNS_EN = [
    r'\bfuck\b', r'\bshit\b', r'\bbitch\b', r'\basshole\b',
    r'\bdamn\b', r'\bstupid\b', r'\bidiot\b', r'\bdumb\b',
]

ALL_TOXIC_PATTERNS = TOXIC_PATTERNS_UZ + TOXIC_PATTERNS_RU + TOXIC_PATTERNS_EN


def check_toxicity_local(text: str) -> dict:
    """
    Lokal so'kinish tekshiruvi (regex asosida).
    
    Returns:
        {
            "is_toxic": bool,
            "confidence": float (0-1),
            "matched_words": list,
            "severity": "low" | "medium" | "high"
        }
    """
    text_lower = text.lower().strip()
    matched = []

    for pattern in ALL_TOXIC_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matched.append(pattern.replace(r'\b', '').replace('\\', ''))

    if not matched:
        return {
            "is_toxic": False,
            "confidence": 0.0,
            "matched_words": [],
            "severity": "none",
        }

    # Severity: ko'p so'z topilsa = yuqori
    if len(matched) >= 3:
        severity = "high"
        confidence = 0.95
    elif len(matched) >= 2:
        severity = "medium"
        confidence = 0.8
    else:
        severity = "low"
        confidence = 0.6

    return {
        "is_toxic": True,
        "confidence": confidence,
        "matched_words": matched,
        "severity": severity,
    }


async def check_toxicity_ai(text: str, groq_api_key: str) -> dict:
    """
    AI yordamida so'kinish/haqorat tekshiruvi (Groq API).
    Lokal tekshiruv bilmagan nozik haqoratlarni ham ushlaydi.
    """
    import httpx

    if not groq_api_key:
        return check_toxicity_local(text)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "max_tokens": 100,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Sen tekst moderatori san. Foydalanuvchi xabarini tekshir.\n"
                                "Agar so'kinish, haqorat, tahdid, noto'g'ri so'zlar bo'lsa "
                                "FAQAT bitta so'z javob ber: TOXIC\n"
                                "Agar xabar normal bo'lsa FAQAT bitta so'z: CLEAN\n"
                                "Boshqa hech narsa yozma."
                            ),
                        },
                        {"role": "user", "content": text},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            result = data["choices"][0]["message"]["content"].strip().upper()

            if "TOXIC" in result:
                return {
                    "is_toxic": True,
                    "confidence": 0.85,
                    "matched_words": ["AI tomonidan aniqlandi"],
                    "severity": "medium",
                }
            return {
                "is_toxic": False,
                "confidence": 0.85,
                "matched_words": [],
                "severity": "none",
            }

    except Exception as e:
        logger.error(f"AI toxicity check xatosi: {e}")
        # Fallback: lokal tekshiruv
        return check_toxicity_local(text)


class ModerationSystem:
    """
    To'liq moderatsiya tizimi:
    - So'kinish filtri (lokal + AI)
    - Rate limiting
    - Ogohlantirish / ban tizimi
    """

    def __init__(self, db: Database, max_daily: int = 5, max_warnings: int = 3):
        self.db = db
        self.max_daily = max_daily
        self.max_warnings = max_warnings

    def check_rate_limit(self, user_id: int) -> bool:
        """Kunlik limit tekshiruvi. True = ruxsat, False = limit oshgan"""
        count = self.db.get_today_feedback_count(user_id)
        return count < self.max_daily

    def get_remaining_today(self, user_id: int) -> int:
        """Bugun qancha feedback qoldirish mumkin"""
        count = self.db.get_today_feedback_count(user_id)
        return max(0, self.max_daily - count)

    async def process_moderation(self, user_id: int, text: str,
                                  groq_api_key: str = None) -> dict:
        """
        To'liq moderatsiya jarayoni.
        
        Returns:
            {
                "allowed": bool,          # Feedback bazaga tushsinmi
                "reason": str,            # Rad etilsa sabab
                "warning_count": int,     # Jami ogohlantirishlar
                "is_banned": bool,        # Ban qilindimi
                "toxicity": dict,         # Toxicity natijasi
            }
        """
        # 1. Ban tekshiruvi
        if self.db.is_banned(user_id):
            return {
                "allowed": False,
                "reason": "banned",
                "warning_count": self.db.get_warning_count(user_id),
                "is_banned": True,
                "toxicity": None,
            }

        # 2. Rate limit tekshiruvi
        if not self.check_rate_limit(user_id):
            return {
                "allowed": False,
                "reason": "rate_limit",
                "warning_count": self.db.get_warning_count(user_id),
                "is_banned": False,
                "toxicity": None,
            }

        # 3. So'kinish tekshiruvi (avval lokal, keyin AI)
        toxicity = check_toxicity_local(text)

        if not toxicity['is_toxic'] and groq_api_key:
            toxicity = await check_toxicity_ai(text, groq_api_key)

        # 4. Toxic bo'lsa — ogohlantirish / ban
        if toxicity['is_toxic']:
            warning_count = self.db.add_warning(
                user_id,
                reason=f"Toxic content: {toxicity['severity']}",
                feedback_text=text[:200],
            )

            is_banned = False
            if warning_count >= self.max_warnings:
                self.db.ban_user(user_id, "Ko'p marta so'kinish", days=None)
                is_banned = True

            return {
                "allowed": False,
                "reason": "toxic",
                "warning_count": warning_count,
                "is_banned": is_banned,
                "toxicity": toxicity,
            }

        # 5. Hammasi yaxshi
        return {
            "allowed": True,
            "reason": None,
            "warning_count": self.db.get_warning_count(user_id),
            "is_banned": False,
            "toxicity": toxicity,
        }
