"""
Web Dashboard
=============
Flask + Chart.js bilan feedback natijalarini ko'rsatish.
Bot bilan bir vaqtda ishga tushadi.
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from database import Database
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
db = Database("feedbacks.db")

CENTER_NAME = os.getenv("CENTER_NAME", "O'quv Markazi")
COURSES = [c.strip() for c in os.getenv("COURSES", "Umumiy").split(",")]


@app.route("/")
def index():
    stats = db.get_stats()
    course_stats = db.get_course_stats()
    daily = db.get_daily_counts(days=30)
    recent = db.get_recent_feedbacks(limit=30)

    return render_template(
        "dashboard.html",
        center_name=CENTER_NAME,
        courses=COURSES,
        stats=stats,
        course_stats=course_stats,
        daily=json.dumps(daily),
        recent=recent,
    )


@app.route("/api/stats")
def api_stats():
    course = request.args.get("course")
    days = request.args.get("days", type=int)
    stats = db.get_stats(course=course, days=days)
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
    daily = db.get_daily_counts(days=days)
    return jsonify(daily)


@app.route("/api/courses")
def api_courses():
    return jsonify(db.get_course_stats())


if __name__ == "__main__":
    db.create_tables()
    app.run(host="0.0.0.0", port=5050, debug=False)
