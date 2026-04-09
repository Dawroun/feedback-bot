"""
Database moduli — PostgreSQL (Supabase)
=======================================
Barcha ma'lumotlar tashqi PostgreSQL bazada saqlanadi.
Deploy qilsangiz ham ma'lumotlar o'chib ketmaydi!
"""

import os
import csv
import logging
from typing import Optional
from datetime import datetime, timedelta
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")


class Database:
    def __init__(self, db_path: str = None):
        """db_path ignored — PostgreSQL DATABASE_URL ishlatiladi"""
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL sozlamasi kerak! Render env ga qo'shing.")

    @contextmanager
    def _conn(self):
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_tables(self):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    ban_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS feedbacks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    text TEXT NOT NULL,
                    is_anonymous BOOLEAN DEFAULT FALSE,
                    course TEXT,
                    sentiment TEXT DEFAULT 'neutral',
                    ai_summary TEXT,
                    topics TEXT,
                    urgency TEXT DEFAULT 'low',
                    source_type TEXT DEFAULT 'text',
                    is_toxic BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS warnings (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    reason TEXT,
                    feedback_text TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS followups (
                    id SERIAL PRIMARY KEY,
                    feedback_id INTEGER NOT NULL REFERENCES feedbacks(id),
                    parent_user_id BIGINT NOT NULL REFERENCES users(user_id),
                    admin_reply TEXT,
                    parent_satisfied BOOLEAN,
                    lang TEXT DEFAULT 'uz_lat',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    replied_at TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_feedbacks_user ON feedbacks(user_id);
                CREATE INDEX IF NOT EXISTS idx_feedbacks_sentiment ON feedbacks(sentiment);
                CREATE INDEX IF NOT EXISTS idx_feedbacks_course ON feedbacks(course);
                CREATE INDEX IF NOT EXISTS idx_feedbacks_created ON feedbacks(created_at);
            """)
        logger.info("PostgreSQL jadvallar tayyor!")

    # ══════════════════════════════════════════════════════════════
    #  FOYDALANUVCHILAR
    # ══════════════════════════════════════════════════════════════

    def upsert_user(self, user_id: int, username: str = None,
                    first_name: str = None, last_name: str = None):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    updated_at = NOW()
            """, (user_id, username, first_name, last_name))

    def get_user_info(self, user_id: int) -> dict:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else {}

    def is_banned(self, user_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT is_banned, ban_until FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return False
            if row['is_banned']:
                if row['ban_until']:
                    if row['ban_until'] < datetime.now():
                        cur.execute(
                            "UPDATE users SET is_banned=FALSE, ban_until=NULL WHERE user_id=%s",
                            (user_id,)
                        )
                        return False
                return True
            return False

    def ban_user(self, user_id: int, reason: str, days: int = None):
        ban_until = None
        if days:
            ban_until = datetime.now() + timedelta(days=days)
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE users SET is_banned=TRUE, ban_reason=%s, ban_until=%s
                WHERE user_id=%s
            """, (reason, ban_until, user_id))

    def unban_user(self, user_id: int):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET is_banned=FALSE, ban_reason=NULL, ban_until=NULL WHERE user_id=%s",
                (user_id,)
            )

    # ══════════════════════════════════════════════════════════════
    #  OGOHLANTIRISHLAR
    # ══════════════════════════════════════════════════════════════

    def add_warning(self, user_id: int, reason: str, feedback_text: str) -> int:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO warnings (user_id, reason, feedback_text) VALUES (%s, %s, %s)",
                (user_id, reason, feedback_text)
            )
            cur.execute("SELECT COUNT(*) as cnt FROM warnings WHERE user_id = %s", (user_id,))
            return cur.fetchone()['cnt']

    def get_warning_count(self, user_id: int) -> int:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM warnings WHERE user_id = %s", (user_id,))
            return cur.fetchone()['cnt']

    def reset_warnings(self, user_id: int):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM warnings WHERE user_id = %s", (user_id,))
            cur.execute(
                "UPDATE users SET is_banned=FALSE, ban_reason=NULL, ban_until=NULL WHERE user_id=%s",
                (user_id,)
            )

    # ══════════════════════════════════════════════════════════════
    #  FEEDBACK SAQLASH
    # ══════════════════════════════════════════════════════════════

    def save_feedback(self, user_id: int, text: str, is_anonymous: bool,
                      course: str, sentiment: str, ai_summary: str = '',
                      topics: str = '', urgency: str = 'low',
                      source_type: str = 'text') -> int:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO feedbacks
                    (user_id, text, is_anonymous, course, sentiment,
                     ai_summary, topics, urgency, source_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, text, is_anonymous, course, sentiment,
                  ai_summary, topics, urgency, source_type))
            return cur.fetchone()['id']

    def get_feedback_by_id(self, fb_id: int) -> Optional[dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM feedbacks WHERE id = %s", (fb_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_today_feedback_count(self, user_id: int) -> int:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) as cnt FROM feedbacks
                WHERE user_id = %s AND created_at >= CURRENT_DATE
            """, (user_id,))
            return cur.fetchone()['cnt']

    # ══════════════════════════════════════════════════════════════
    #  STATISTIKA
    # ══════════════════════════════════════════════════════════════

    def get_stats(self) -> dict:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE sentiment='positive') as positive,
                    COUNT(*) FILTER (WHERE sentiment='negative') as negative,
                    COUNT(*) FILTER (WHERE sentiment='neutral') as neutral,
                    COUNT(*) FILTER (WHERE source_type='voice') as voice_count,
                    COUNT(*) FILTER (WHERE source_type='text') as text_count
                FROM feedbacks WHERE is_toxic = FALSE
            """)
            row = cur.fetchone()
            return dict(row) if row else {
                'total': 0, 'positive': 0, 'negative': 0,
                'neutral': 0, 'voice_count': 0, 'text_count': 0
            }

    def get_course_stats(self) -> list:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT course,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE sentiment='positive') as positive,
                    COUNT(*) FILTER (WHERE sentiment='negative') as negative
                FROM feedbacks WHERE is_toxic = FALSE
                GROUP BY course ORDER BY total DESC
            """)
            return [dict(r) for r in cur.fetchall()]

    def get_daily_stats(self, days: int = 30) -> list:
        date_from = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DATE(created_at) as day, COUNT(*) as count,
                    COUNT(*) FILTER (WHERE sentiment='positive') as positive,
                    COUNT(*) FILTER (WHERE sentiment='negative') as negative
                FROM feedbacks WHERE is_toxic = FALSE AND created_at >= %s
                GROUP BY DATE(created_at) ORDER BY day
            """, (date_from,))
            return [dict(r) for r in cur.fetchall()]

    def get_feedbacks_since(self, hours: int = 24) -> list:
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT f.*, u.first_name, u.username
                FROM feedbacks f JOIN users u ON f.user_id = u.user_id
                WHERE f.is_toxic = FALSE AND f.created_at >= %s
                ORDER BY f.created_at DESC
            """, (since,))
            return [dict(r) for r in cur.fetchall()]

    def get_recent_feedbacks(self, limit: int = 30, course: str = None,
                             sentiment: str = None) -> list:
        with self._conn() as conn:
            cur = conn.cursor()
            query = """
                SELECT f.*, u.first_name, u.username
                FROM feedbacks f JOIN users u ON f.user_id = u.user_id
                WHERE f.is_toxic = FALSE
            """
            params = []
            if course:
                query += " AND f.course = %s"
                params.append(course)
            if sentiment:
                query += " AND f.sentiment = %s"
                params.append(sentiment)
            query += " ORDER BY f.created_at DESC LIMIT %s"
            params.append(limit)
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    # ══════════════════════════════════════════════════════════════
    #  FOLLOW-UP
    # ══════════════════════════════════════════════════════════════

    def create_followup(self, feedback_id: int, parent_user_id: int) -> int:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO followups (feedback_id, parent_user_id) VALUES (%s, %s) RETURNING id",
                (feedback_id, parent_user_id)
            )
            return cur.fetchone()['id']

    def get_followup_by_feedback(self, feedback_id: int) -> Optional[dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM followups WHERE feedback_id = %s", (feedback_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_pending_followup(self, parent_user_id: int) -> Optional[dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT fo.*, f.text as original_feedback, f.course
                FROM followups fo JOIN feedbacks f ON fo.feedback_id = f.id
                WHERE fo.parent_user_id = %s AND fo.status = 'pending'
                ORDER BY fo.created_at DESC LIMIT 1
            """, (parent_user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def set_followup_reply(self, feedback_id: int, admin_reply: str):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE followups SET admin_reply=%s, status='replied', replied_at=NOW() WHERE feedback_id=%s",
                (admin_reply, feedback_id)
            )

    def set_followup_satisfied(self, followup_id: int, satisfied: bool):
        status = "satisfied" if satisfied else "unsatisfied"
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE followups SET parent_satisfied=%s, status=%s WHERE id=%s",
                (satisfied, status, followup_id)
            )

    def save_followup_lang(self, feedback_id: int, lang: str):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE followups SET lang=%s WHERE feedback_id=%s", (lang, feedback_id))

    def get_followup_lang(self, feedback_id: int) -> Optional[str]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT lang FROM followups WHERE feedback_id=%s", (feedback_id,))
            row = cur.fetchone()
            return row['lang'] if row else None

    def get_followup_lang_by_id(self, followup_id: int) -> Optional[str]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT lang FROM followups WHERE id=%s", (followup_id,))
            row = cur.fetchone()
            return row['lang'] if row else None

    # ══════════════════════════════════════════════════════════════
    #  EXPORT
    # ══════════════════════════════════════════════════════════════

    def export_csv(self, filepath: str) -> Optional[str]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT f.id, f.created_at, f.course, f.sentiment, f.text,
                       f.ai_summary, f.source_type, f.is_anonymous,
                       CASE WHEN f.is_anonymous THEN 'Anonim'
                            ELSE u.first_name END as sender
                FROM feedbacks f
                JOIN users u ON f.user_id = u.user_id
                WHERE f.is_toxic = FALSE
                ORDER BY f.created_at DESC
            """)
            rows = cur.fetchall()

            if not rows:
                return None

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ID', 'Sana', 'Kurs', 'Sentiment', 'Fikr-mulohaza',
                    'AI Xulosa', 'Turi', 'Anonim', 'Yuboruvchi'
                ])
                for row in rows:
                    writer.writerow([row[k] for k in row])

            return filepath
