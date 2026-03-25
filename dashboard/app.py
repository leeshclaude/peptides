"""
Flask dashboard for @peptidealpharesearch multi-agent content pipeline.
Serves live status, content calendar, activity log, and quick stats.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template

app = Flask(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

RESEARCH_BRIEFS_DIR = DATA_DIR / "research_briefs"
CONTENT_CALENDAR_FILE = DATA_DIR / "content_calendar.json"
CONTENT_PACKAGES_DIR = DATA_DIR / "content_packages"
ENGAGEMENT_QUEUE_FILE = DATA_DIR / "engagement_queue.md"
ACTIVITY_LOG_FILE = DATA_DIR / "activity_log.jsonl"


def _mtime_to_iso(path: Path):
    """Return ISO string of a file's mtime, or None if file doesn't exist."""
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime).isoformat()
    except (FileNotFoundError, OSError):
        return None


def _latest_mtime_in_dir(directory: Path):
    """Return the ISO mtime of the most-recently-modified file in a directory."""
    try:
        files = list(directory.glob("*.md")) + list(directory.glob("*.json"))
        if not files:
            return None
        latest = max(files, key=lambda f: f.stat().st_mtime)
        return _mtime_to_iso(latest)
    except (FileNotFoundError, OSError):
        return None


def _count_packages():
    try:
        return len(list(CONTENT_PACKAGES_DIR.glob("*.json")))
    except (FileNotFoundError, OSError):
        return 0


def _load_calendar():
    try:
        with open(CONTENT_CALENDAR_FILE) as f:
            data = json.load(f)
        return data.get("ideas", []), data.get("last_updated")
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return [], None


def _load_activity_log(n=20):
    """Return the last n log entries (newest first)."""
    if not ACTIVITY_LOG_FILE.exists():
        return []
    try:
        lines = ACTIVITY_LOG_FILE.read_text().splitlines()
        entries = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return list(reversed(entries[-n:]))
    except OSError:
        return []


def _brief_age(last_updated_iso):
    """Return a human-readable age string from an ISO timestamp."""
    if not last_updated_iso:
        return "Unknown"
    try:
        ts = datetime.fromisoformat(last_updated_iso)
        now = datetime.now()
        delta = now - ts
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{delta.days}d ago"
    except (ValueError, TypeError):
        return "Unknown"


def _agent_status(last_run_iso):
    """Infer a simple idle/done status from whether last_run is set."""
    if not last_run_iso:
        return "idle"
    return "done"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    ideas, calendar_updated = _load_calendar()

    # Agent last-run times
    research_last_run = _latest_mtime_in_dir(RESEARCH_BRIEFS_DIR)
    engagement_last_run = _mtime_to_iso(ENGAGEMENT_QUEUE_FILE)

    # Ideation = calendar last updated
    ideation_last_run = calendar_updated

    # Content agent = latest content package
    content_last_run = _latest_mtime_in_dir(CONTENT_PACKAGES_DIR)

    # Stats
    status_counts = {"pending": 0, "approved": 0, "content_ready": 0, "posted": 0}
    for idea in ideas:
        s = idea.get("status", "pending")
        if s in status_counts:
            status_counts[s] += 1

    packages_count = _count_packages()

    agents = [
        {
            "id": "research",
            "name": "Research",
            "icon": "🔬",
            "description": "Fetches PubMed abstracts and builds daily research briefs",
            "last_run": research_last_run,
            "last_run_age": _brief_age(research_last_run),
            "status": _agent_status(research_last_run),
        },
        {
            "id": "ideation",
            "name": "Ideation",
            "icon": "💡",
            "description": "Scores research briefs and generates ranked content ideas",
            "last_run": ideation_last_run,
            "last_run_age": _brief_age(ideation_last_run),
            "status": _agent_status(ideation_last_run),
        },
        {
            "id": "content",
            "name": "Content",
            "icon": "🎨",
            "description": "Writes slide copy and generates Canva carousel designs",
            "last_run": content_last_run,
            "last_run_age": _brief_age(content_last_run),
            "status": _agent_status(content_last_run),
        },
        {
            "id": "engagement",
            "name": "Engagement",
            "icon": "💬",
            "description": "Drafts comments for competitor posts to grow organic reach",
            "last_run": engagement_last_run,
            "last_run_age": _brief_age(engagement_last_run),
            "status": _agent_status(engagement_last_run),
        },
    ]

    calendar_rows = []
    for idea in ideas:
        calendar_rows.append(
            {
                "rank": idea.get("rank", ""),
                "title": idea.get("title", ""),
                "status": idea.get("status", "pending"),
                "score": idea.get("priority_score", ""),
                "post_day": idea.get("recommended_post_day", ""),
            }
        )

    activity_log = _load_activity_log(20)

    # Brief age = age of most recent research brief
    brief_age_str = _brief_age(research_last_run)

    return jsonify(
        {
            "agents": agents,
            "calendar": calendar_rows,
            "activity_log": activity_log,
            "stats": {
                "brief_age": brief_age_str,
                "pending": status_counts["pending"],
                "approved": status_counts["approved"],
                "content_ready": status_counts["content_ready"],
                "posted": status_counts["posted"],
                "packages": packages_count,
            },
        }
    )


if __name__ == "__main__":
    app.run(port=5555, debug=False)
