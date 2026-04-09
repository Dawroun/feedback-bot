"""
Web Dashboard
=============
Flask + Chart.js bilan feedback natijalarini ko'rsatish.
Bot bilan bir vaqtda ishga tushadi.
"""

import os
import json
from datetime import datetime, date
from flask import Flask, render_template, jsonify, request
from database import Database
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# PostgreSQL datetime/date ni JSON ga o'girish
class CustomJSONProvider(app.json_provider_class):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

app.json_provider_class = CustomJSONProvider
app.json = CustomJSONProvider(app)

db = Database("feedbacks.db")

CENTER_NAME = os.getenv("CENTER_NAME", "O'quv Markazi")
COURSES = [c.strip() for c in os.getenv("COURSES", "Umumiy").split(",")]


def _serialize(obj):
    """date/datetime objektlarni string ga o'girish"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


@app.route("/")
def index():
    stats = db.get_stats()
    course_stats = db.get_course_stats()
    daily = db.get_daily_stats(days=30)
    recent = db.get_recent_feedbacks(limit=30)

    return render_template(
        "dashboard.html",
        center_name=CENTER_NAME,
        courses=COURSES,
        stats=stats,
        course_stats=course_stats,
        daily=json.dumps(daily, default=_serialize),
        recent=recent,
    )


@app.route("/api/stats")
def api_stats():
    stats = db.get_stats()
    return jsonify(stats)


@app.route("/api/feedbacks")
def api_feedbacks():
    course = request.args.get("course")
    sentiment = request.args.get("sentiment")
    limit = request.args.get("limit", 50, type=int)
    feedbacks = db.get_recent_feedbacks(limit=limit, course=course, sentiment=sentiment)

    # Anonim feedbacklardan ism yashirish
    for fb in feedbacks:
        if fb.get("is_anonymous"):
            fb["username"] = None
            fb["first_name"] = "Anonim"
            fb["last_name"] = None

    return jsonify(feedbacks)


@app.route("/api/daily")
def api_daily():
    days = request.args.get("days", 30, type=int)
    daily = db.get_daily_stats(days=days)
    return jsonify(daily)


@app.route("/api/courses")
def api_courses():
    return jsonify(db.get_course_stats())


if __name__ == "__main__":
    db.create_tables()
    app.run(host="0.0.0.0", port=5050, debug=False)
