"""
Flask dashboard for @peptidealpharesearch multi-agent content pipeline.
Serves live status, org chart data, content calendar, and activity log.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template

app = Flask(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

RESEARCH_BRIEFS_DIR  = DATA_DIR / "research_briefs"
CONTENT_CALENDAR_FILE = DATA_DIR / "content_calendar.json"
CONTENT_PACKAGES_DIR = DATA_DIR / "content_packages"
ENGAGEMENT_QUEUE_FILE = DATA_DIR / "engagement_queue.md"
TREND_ALERTS_FILE    = DATA_DIR / "trend_alerts.md"
REPLY_QUEUE_FILE     = DATA_DIR / "reply_queue.md"
CAPTIONS_DIR         = DATA_DIR / "captions"
REPURPOSED_DIR       = DATA_DIR / "repurposed"
ANALYTICS_DIR        = DATA_DIR / "analytics"
ACTIVITY_LOG_FILE    = DATA_DIR / "activity_log.jsonl"


def _mtime_to_iso(path: Path):
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    except (FileNotFoundError, OSError):
        return None


def _latest_mtime_in_dir(directory: Path):
    try:
        files = list(directory.glob("*"))
        if not files:
            return None
        latest = max(files, key=lambda f: f.stat().st_mtime)
        return _mtime_to_iso(latest)
    except (FileNotFoundError, OSError):
        return None


def _brief_age(last_updated_iso):
    if not last_updated_iso:
        return None
    try:
        ts = datetime.fromisoformat(last_updated_iso)
        delta = datetime.now() - ts
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{delta.days}d ago"
    except (ValueError, TypeError):
        return None


def _load_activity_log(n=50):
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


def _agent_live_status(agent_id: str, all_log_entries: list) -> dict:
    """
    Derive live status from activity log.
    - If the most recent entry for this agent is 'running' and within 10 min → running
    - If most recent is 'done' → done
    - If most recent is 'error' → error
    - Otherwise → idle
    Returns dict with status and current_task.
    """
    agent_entries = [e for e in reversed(all_log_entries) if e.get("agent") == agent_id]
    if not agent_entries:
        return {"status": "idle", "current_task": None, "last_ts": None}

    latest = agent_entries[0]
    status = latest.get("status", "idle")
    message = latest.get("message", "")
    ts = latest.get("ts")

    # If status is running, check it's not stale (> 10 min old)
    if status == "running" and ts:
        try:
            age_s = (datetime.now() - datetime.fromisoformat(ts)).total_seconds()
            if age_s > 600:
                status = "idle"
        except Exception:
            pass

    return {
        "status": status,
        "current_task": message if status in ("running", "done", "error") else None,
        "last_ts": ts,
    }


def _load_calendar():
    try:
        with open(CONTENT_CALENDAR_FILE) as f:
            data = json.load(f)
        return data.get("ideas", []), data.get("last_updated")
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return [], None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    ideas, calendar_updated = _load_calendar()
    all_log = _load_activity_log(100)

    # ── Last-run timestamps ────────────────────────────────────────────────────
    last_run = {
        "research":          _latest_mtime_in_dir(RESEARCH_BRIEFS_DIR),
        "ideation":          calendar_updated,
        "content":           _latest_mtime_in_dir(CONTENT_PACKAGES_DIR),
        "engagement":        _mtime_to_iso(ENGAGEMENT_QUEUE_FILE),
        "hook_tester":       None,  # derived from calendar hook_variants
        "caption":           _latest_mtime_in_dir(CAPTIONS_DIR),
        "repurpose":         _latest_mtime_in_dir(REPURPOSED_DIR),
        "trend_spotter":     _mtime_to_iso(TREND_ALERTS_FILE),
        "community_manager": _mtime_to_iso(REPLY_QUEUE_FILE),
        "analytics":         _latest_mtime_in_dir(ANALYTICS_DIR),
    }

    # Hook tester: check if any idea in calendar has hook_variants
    for idea in ideas:
        if idea.get("hook_variants"):
            ts = idea.get("hooks_generated_at") or idea.get("created_at")
            if ts and (last_run["hook_tester"] is None or ts > last_run["hook_tester"]):
                last_run["hook_tester"] = ts

    # ── Agent definitions (10 agents across 4 tiers) ──────────────────────────
    agent_defs = [
        # Tier 1: Intelligence
        {
            "id": "research", "name": "Research",
            "icon": "🔬", "tier": "intelligence",
            "description": "Fetches PubMed studies + competitor intel",
            "telegram": "/research",
        },
        {
            "id": "trend_spotter", "name": "Trend Spotter",
            "icon": "📈", "tier": "intelligence",
            "description": "Scans Reddit for niche spikes in real-time",
            "telegram": "/trends",
        },
        {
            "id": "analytics", "name": "Analytics",
            "icon": "📊", "tier": "intelligence",
            "description": "Tracks post performance + feeds back to ideation",
            "telegram": "/analytics",
        },
        # Tier 2: Strategy
        {
            "id": "ideation", "name": "Ideation",
            "icon": "💡", "tier": "strategy",
            "description": "Synthesises research → ranked carousel ideas",
            "telegram": "/ideation",
        },
        # Tier 3: Content
        {
            "id": "hook_tester", "name": "Hook Tester",
            "icon": "🎣", "tier": "content",
            "description": "Generates 5 hook variants per idea",
            "telegram": "/hooks",
        },
        {
            "id": "caption", "name": "Caption",
            "icon": "✍️", "tier": "content",
            "description": "Writes caption + 30 hashtags + disclaimer",
            "telegram": "/caption",
        },
        {
            "id": "content", "name": "Content / Canva",
            "icon": "🎨", "tier": "content",
            "description": "Populates Canva template with slide copy",
            "telegram": "Claude Code",
        },
        {
            "id": "repurpose", "name": "Repurpose",
            "icon": "♻️", "tier": "content",
            "description": "Converts carousel → Twitter + LinkedIn + Reel",
            "telegram": "/repurpose",
        },
        # Tier 4: Community
        {
            "id": "engagement", "name": "Engagement",
            "icon": "💬", "tier": "community",
            "description": "Drafts outbound comments on competitor posts",
            "telegram": "/engagement",
        },
        {
            "id": "community_manager", "name": "Community Mgr",
            "icon": "🤝", "tier": "community",
            "description": "Drafts replies to your own inbound comments",
            "telegram": "/replies",
        },
    ]

    agents = []
    for d in agent_defs:
        live = _agent_live_status(d["id"], all_log)
        lr = last_run.get(d["id"])
        agents.append({
            **d,
            "status":       live["status"],
            "current_task": live["current_task"],
            "last_run":     lr,
            "last_run_age": _brief_age(lr) or "Never run",
            "last_ts":      live["last_ts"],
        })

    # ── Stats ──────────────────────────────────────────────────────────────────
    status_counts = {"pending": 0, "approved": 0, "content_ready": 0, "posted": 0}
    for idea in ideas:
        s = idea.get("status", "pending")
        if s in status_counts:
            status_counts[s] += 1

    packages_count = 0
    try:
        packages_count = len(list(CONTENT_PACKAGES_DIR.glob("*.json")))
    except (FileNotFoundError, OSError):
        pass

    # ── Calendar rows ──────────────────────────────────────────────────────────
    calendar_rows = [
        {
            "rank":     idea.get("rank", ""),
            "title":    idea.get("title", ""),
            "status":   idea.get("status", "pending"),
            "score":    idea.get("priority_score", ""),
            "post_day": idea.get("recommended_post_day", ""),
        }
        for idea in ideas
    ]

    # ── Recent activity (for display) ─────────────────────────────────────────
    activity_log = _load_activity_log(30)

    return jsonify({
        "agents":       agents,
        "calendar":     calendar_rows,
        "activity_log": activity_log,
        "stats": {
            "brief_age":     _brief_age(last_run["research"]) or "None",
            "pending":       status_counts["pending"],
            "approved":      status_counts["approved"],
            "content_ready": status_counts["content_ready"],
            "posted":        status_counts["posted"],
            "packages":      packages_count,
            "active_agents": sum(1 for a in agents if a["status"] == "running"),
        },
    })


if __name__ == "__main__":
    app.run(port=5555, debug=False)
