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
#  SO'KINISH / HAQORAT SO'ZLARI (faqat aniq so'kinishlar)
#  False positive bo'lmasligi uchun faqat haqiqiy so'kinishlar
# ══════════════════════════════════════════════════════════════════════

TOXIC_PATTERNS_UZ = [
    r'\baxmoq\b', r'\beshak\b', r'\bharom\b', r'\bharomzoda\b',
    r'\bjinni\b', r'\btentak\b', r'\bnodon\b',
    r'\bkal\b', r'\bsig\'ir\b', r'\bcho\'chqa\b',
    r'\blanja\b', r'\bfohisha\b',
]

TOXIC_PATTERNS_RU = [
    r'\bбля[дт]ь?\b', r'\bсука\b', r'\bхуй', r'\bпизд',
    r'\bеб[аи]', r'\bнахуй\b', r'\bпидор', r'\bмудак\b',
    r'\bдерьмо\b', r'\bгавно\b',
]

TOXIC_PATTERNS_EN = [
    r'\bfuck\b', r'\bshit\b', r'\bbitch\b', r'\basshole\b',
]

ALL_TOXIC_PATTERNS = TOXIC_PATTERNS_UZ + TOXIC_PATTERNS_RU + TOXIC_PATTERNS_EN


def check_toxicity(text: str) -> dict:
    """
    So'kinish tekshiruvi (faqat lokal regex).
    Groq AI o'zbek tilini yaxshi tushunmagani uchun faqat lokal filtr ishlatiladi.
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

    if len(matched) >= 3:
        severity = "high"
    elif len(matched) >= 2:
        severity = "medium"
    else:
        severity = "low"

    return {
        "is_toxic": True,
        "confidence": 0.8,
        "matched_words": matched,
        "severity": severity,
    }


class ModerationSystem:
    """
    Moderatsiya tizimi:
    - So'kinish filtri (lokal regex)
    - Rate limiting
    - Ogohlantirish / ban tizimi
    """

    def __init__(self, db: Database, max_daily: int = 5, max_warnings: int = 3):
        self.db = db
        self.max_daily = max_daily
        self.max_warnings = max_warnings

    def check_rate_limit(self, user_id: int) -> bool:
        count = self.db.get_today_feedback_count(user_id)
        return count < self.max_daily

    def get_remaining_today(self, user_id: int) -> int:
        count = self.db.get_today_feedback_count(user_id)
        return max(0, self.max_daily - count)

    async def process_moderation(self, user_id: int, text: str,
                                  groq_api_key: str = None) -> dict:
        # 1. Ban tekshiruvi
        if self.db.is_banned(user_id):
            return {
                "allowed": False,
                "reason": "banned",
                "warning_count": self.db.get_warning_count(user_id),
                "is_banned": True,
                "toxicity": None,
            }

        # 2. Rate limit
        if not self.check_rate_limit(user_id):
            return {
                "allowed": False,
                "reason": "rate_limit",
                "warning_count": self.db.get_warning_count(user_id),
                "is_banned": False,
                "toxicity": None,
            }

        # 3. So'kinish tekshiruvi (faqat lokal — AI ishonchsiz)
        toxicity = check_toxicity(text)

        # 4. Toxic bo'lsa — ogohlantirish / ban
        if toxicity['is_toxic']:
            warning_count = self.db.add_warning(
                user_id,
                reason=f"Toxic: {', '.join(toxicity['matched_words'])}",
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
