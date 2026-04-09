"""
Database moduli (SQLite)
========================
Feedbacklar, foydalanuvchilar, ogohlantirishlar, blokirovkalar.
"""

import sqlite3
import csv
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "feedbacks.db"):
        self.db_path = db_path
        self.create_tables()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ══════════════════════════════════════════════════════════════
    #  JADVALLAR
    # ══════════════════════════════════════════════════════════════

    def create_tables(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen TEXT DEFAULT (datetime('now')),
                    is_banned INTEGER DEFAULT 0,
                    ban_reason TEXT,
                    ban_until TEXT
                );

                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    is_anonymous INTEGER DEFAULT 0,
                    course TEXT,
                    text TEXT NOT NULL,
                    sentiment TEXT DEFAULT 'neutral',
                    ai_summary TEXT,
                    topics TEXT,
                    urgency TEXT DEFAULT 'low',
                    source_type TEXT DEFAULT 'text',
                    is_toxic INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reason TEXT,
                    feedback_text TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_feedbacks_user
                    ON feedbacks(user_id);
                CREATE INDEX IF NOT EXISTS idx_feedbacks_sentiment
                    ON feedbacks(sentiment);
                CREATE INDEX IF NOT EXISTS idx_feedbacks_course
                    ON feedbacks(course);
                CREATE INDEX IF NOT EXISTS idx_feedbacks_created
                    ON feedbacks(created_at);
            """)

    # ══════════════════════════════════════════════════════════════
    #  FOYDALANUVCHILAR
    # ══════════════════════════════════════════════════════════════

    def upsert_user(self, user_id: int, username: str = None,
                    first_name: str = None, last_name: str = None):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(excluded.username, username),
                    first_name = COALESCE(excluded.first_name, first_name),
                    last_name = COALESCE(excluded.last_name, last_name)
            """, (user_id, username, first_name, last_name))

    def is_banned(self, user_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT is_banned, ban_until FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            if not row:
                return False
            if row['is_banned']:
                if row['ban_until']:
                    if datetime.fromisoformat(row['ban_until']) < datetime.now():
                        conn.execute(
                            "UPDATE users SET is_banned=0, ban_until=NULL WHERE user_id=?",
                            (user_id,)
                        )
                        return False
                return True
            return False

    def ban_user(self, user_id: int, reason: str, days: int = None):
        ban_until = None
        if days:
            ban_until = (datetime.now() + timedelta(days=days)).isoformat()
        with self._conn() as conn:
            conn.execute("""
                UPDATE users SET is_banned=1, ban_reason=?, ban_until=?
                WHERE user_id=?
            """, (reason, ban_until, user_id))

    def unban_user(self, user_id: int):
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET is_banned=0, ban_reason=NULL, ban_until=NULL WHERE user_id=?",
                (user_id,)
            )

    def get_user_info(self, user_id: int) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    # ══════════════════════════════════════════════════════════════
    #  OGOHLANTIRISHLAR
    # ══════════════════════════════════════════════════════════════

    def add_warning(self, user_id: int, reason: str, feedback_text: str) -> int:
        """Ogohlantirish qo'shish, jami sonni qaytarish"""
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO warnings (user_id, reason, feedback_text) VALUES (?, ?, ?)",
                (user_id, reason, feedback_text)
            )
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM warnings WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return row['cnt']

    def get_warning_count(self, user_id: int) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM warnings WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return row['cnt']

    def reset_warnings(self, user_id: int):
        """Foydalanuvchining barcha ogohlantirishlarini o'chirish"""
        with self._conn() as conn:
            conn.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))
            conn.execute(
                "UPDATE users SET is_banned=0, ban_reason=NULL, ban_until=NULL WHERE user_id=?",
                (user_id,)
            )

    # ══════════════════════════════════════════════════════════════
    #  FEEDBACKLAR
    # ══════════════════════════════════════════════════════════════

    def save_feedback(self, user_id: int, text: str, is_anonymous: bool = False,
                      course: str = None, sentiment: str = "neutral",
                      ai_summary: str = None, topics: str = None,
                      urgency: str = "low", source_type: str = "text",
                      is_toxic: bool = False) -> int:
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO feedbacks
                    (user_id, is_anonymous, course, text, sentiment,
                     ai_summary, topics, urgency, source_type, is_toxic)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, int(is_anonymous), course, text, sentiment,
                  ai_summary, topics, urgency, source_type, int(is_toxic)))
            return cursor.lastrowid

    def get_today_feedback_count(self, user_id: int) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        with self._conn() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as cnt FROM feedbacks
                WHERE user_id = ? AND date(created_at) = ?
            """, (user_id, today)).fetchone()
            return row['cnt']

    def get_feedback_by_id(self, feedback_id: int) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT f.*, u.username, u.first_name, u.last_name "
                "FROM feedbacks f JOIN users u ON f.user_id = u.user_id "
                "WHERE f.id = ?", (feedback_id,)
            ).fetchone()
            return dict(row) if row else None

    # ══════════════════════════════════════════════════════════════
    #  STATISTIKA
    # ══════════════════════════════════════════════════════════════

    def get_stats(self, course: str = None, days: int = None) -> dict:
        with self._conn() as conn:
            where = "WHERE is_toxic = 0"
            params = []

            if course:
                where += " AND course = ?"
                params.append(course)
            if days:
                date_from = (datetime.now() - timedelta(days=days)).isoformat()
                where += " AND created_at >= ?"
                params.append(date_from)

            total = conn.execute(
                f"SELECT COUNT(*) as c FROM feedbacks {where}", params
            ).fetchone()['c']

            sentiments = {}
            for s in ('positive', 'negative', 'neutral'):
                row = conn.execute(
                    f"SELECT COUNT(*) as c FROM feedbacks {where} AND sentiment=?",
                    params + [s]
                ).fetchone()
                sentiments[s] = row['c']

            voice = conn.execute(
                f"SELECT COUNT(*) as c FROM feedbacks {where} AND source_type='voice'",
                params
            ).fetchone()['c']

            text = conn.execute(
                f"SELECT COUNT(*) as c FROM feedbacks {where} AND source_type='text'",
                params
            ).fetchone()['c']

            return {
                'total': total,
                'positive': sentiments['positive'],
                'negative': sentiments['negative'],
                'neutral': sentiments['neutral'],
                'voice_count': voice,
                'text_count': text,
            }

    def get_course_stats(self) -> list:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT course,
                       COUNT(*) as total,
                       SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative,
                       SUM(CASE WHEN sentiment='neutral' THEN 1 ELSE 0 END) as neutral
                FROM feedbacks
                WHERE is_toxic = 0 AND course IS NOT NULL
                GROUP BY course
                ORDER BY total DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def get_recent_feedbacks(self, limit: int = 50, course: str = None,
                             sentiment: str = None) -> list:
        with self._conn() as conn:
            where = "WHERE f.is_toxic = 0"
            params = []

            if course:
                where += " AND f.course = ?"
                params.append(course)
            if sentiment:
                where += " AND f.sentiment = ?"
                params.append(sentiment)

            params.append(limit)
            rows = conn.execute(f"""
                SELECT f.*, u.username, u.first_name, u.last_name
                FROM feedbacks f
                JOIN users u ON f.user_id = u.user_id
                {where}
                ORDER BY f.created_at DESC
                LIMIT ?
            """, params).fetchall()
            return [dict(r) for r in rows]

    def get_daily_counts(self, days: int = 30) -> list:
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT date(created_at) as day,
                       COUNT(*) as total,
                       SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative
                FROM feedbacks
                WHERE is_toxic = 0 AND date(created_at) >= ?
                GROUP BY date(created_at)
                ORDER BY day
            """, (date_from,)).fetchall()
            return [dict(r) for r in rows]

    def get_feedbacks_since(self, hours: int = 24) -> list:
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT f.*, u.first_name, u.username
                FROM feedbacks f JOIN users u ON f.user_id = u.user_id
                WHERE f.is_toxic = 0 AND f.created_at >= ?
                ORDER BY f.created_at DESC
            """, (since,)).fetchall()
            return [dict(r) for r in rows]

    # ══════════════════════════════════════════════════════════════
    #  EXPORT
    # ══════════════════════════════════════════════════════════════

    def export_csv(self, filepath: str) -> Optional[str]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT f.id, f.created_at, f.course, f.sentiment, f.text,
                       f.ai_summary, f.source_type, f.is_anonymous,
                       CASE WHEN f.is_anonymous = 1 THEN 'Anonim'
                            ELSE u.first_name END as sender
                FROM feedbacks f
                JOIN users u ON f.user_id = u.user_id
                WHERE f.is_toxic = 0
                ORDER BY f.created_at DESC
            """).fetchall()

            if not rows:
                return None

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ID', 'Sana', 'Kurs', 'Sentiment', 'Feedback',
                    'AI Xulosa', 'Turi', 'Anonim', 'Yuboruvchi'
                ])
                for row in rows:
                    writer.writerow([dict(row)[k] for k in dict(row)])

            return filepath
