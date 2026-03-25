"""
Trend Spotter Agent — monitors Reddit and web for peptide/longevity niche spikes.

Scans:
- r/Peptides, r/longevity, r/Biohackers, r/nootropics top posts (last 24h)
- Web search for trending peptide topics
- Flags topics gaining traction that aren't in the current content calendar

Output saved to data/trend_alerts.md

Usage:
    from agents.trend_spotter_agent import run
    path = run()
"""
from typing import Optional, List
import json
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.llm import call_llm
from tools.activity_log import log

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
CALENDAR_FILE = REPO_ROOT / "data" / "content_calendar.json"
ALERTS_FILE = REPO_ROOT / "data" / "trend_alerts.md"

SUBREDDITS = [
    "Peptides",
    "longevity",
    "Biohackers",
    "nootropics",
    "antiaging",
]

SYSTEM_PROMPT = """You are a trend analyst for @peptidealpharesearch — a science-backed peptides and longevity Instagram account.

Given raw Reddit/web data, identify:
1. TRENDING TOPICS — peptide compounds, protocols, or longevity concepts gaining momentum RIGHT NOW
2. HOT QUESTIONS — questions the community is asking that we could answer
3. CONTENT GAPS — topics trending that we haven't covered yet (see calendar below)
4. URGENCY SIGNALS — anything time-sensitive (new study just published, controversy, viral post)

For each trend, score urgency 1-10 and suggest a content angle.

Format as a clean markdown report with clear sections. Be specific — name the compounds, subreddits, post titles."""


def fetch_reddit_hot(subreddit: str, limit: int = 10) -> List[dict]:
    """Fetch hot posts from a subreddit via the public JSON API."""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        headers = {"User-Agent": "peptidealpharesearch-bot/1.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        posts = resp.json()["data"]["children"]
        return [
            {
                "title": p["data"]["title"],
                "score": p["data"]["score"],
                "num_comments": p["data"]["num_comments"],
                "url": f"https://reddit.com{p['data']['permalink']}",
                "flair": p["data"].get("link_flair_text", ""),
            }
            for p in posts
        ]
    except Exception as e:
        print(f"  Warning: Reddit fetch failed for r/{subreddit}: {e}")
        return []


def load_calendar_titles() -> List[str]:
    if CALENDAR_FILE.exists():
        cal = json.loads(CALENDAR_FILE.read_text())
        return [i.get("title", "") for i in cal.get("ideas", [])]
    return []


def run() -> Path:
    """Scan Reddit for trending peptide topics and save an alert report."""
    log("trend_spotter", "running", "Scanning Reddit for trends")
    print("[Trend Spotter] Scanning Reddit communities...")

    all_posts = []
    for sub in SUBREDDITS:
        print(f"  Fetching r/{sub}...")
        posts = fetch_reddit_hot(sub, limit=10)
        for p in posts:
            p["subreddit"] = sub
        all_posts.extend(posts)

    if not all_posts:
        print("[Trend Spotter] Warning: No Reddit data fetched — possible network issue.")

    calendar_titles = load_calendar_titles()
    titles_str = "\n".join(f"- {t}" for t in calendar_titles) if calendar_titles else "None"

    reddit_summary = []
    for p in sorted(all_posts, key=lambda x: x["score"], reverse=True)[:30]:
        reddit_summary.append(
            f"r/{p['subreddit']} | Score:{p['score']} | Comments:{p['num_comments']} | {p['title']}"
        )

    user_prompt = f"""Analyse these trending Reddit posts from the peptide/longevity niche:

## Reddit Hot Posts (sorted by score)
{chr(10).join(reddit_summary) if reddit_summary else 'No data available'}

## Already in Content Calendar (avoid suggesting duplicates)
{titles_str}

## Today's Date
{datetime.now().strftime("%Y-%m-%d")}

Identify trends, hot questions, content gaps, and urgency signals. Score each trend 1-10."""

    print("  Analysing trends with LLM...")
    report = call_llm(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=2000)

    output = (
        f"# Trend Alert Report\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{report}\n\n"
        f"---\n"
        f"*Raw data: {len(all_posts)} posts scanned from {len(SUBREDDITS)} subreddits*\n"
    )

    ALERTS_FILE.write_text(output)
    log("trend_spotter", "done", f"Trend report saved: {ALERTS_FILE.name}")
    print(f"[Trend Spotter] Report saved to: {ALERTS_FILE}")
    return ALERTS_FILE


if __name__ == "__main__":
    path = run()
    print(f"\nTrend alert: {path}")
    print("\n" + path.read_text()[:1000])
