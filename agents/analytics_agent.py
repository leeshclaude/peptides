"""
Analytics Agent — tracks post performance and feeds signals back into ideation.

Since Instagram API access is restricted, this agent accepts MANUAL metric input
and generates performance insights + ideation recommendations.

Input: data/analytics/posts.json (manually maintained)
Output: data/analytics/report_YYYY-MM-DD.md + performance signals appended to briefs

Post entry format:
{
  "date": "2026-03-20",
  "title": "Peptide for Hair Strength",
  "format": "carousel",
  "reach": 1200,
  "likes": 145,
  "saves": 89,
  "shares": 12,
  "comments": 23,
  "follows_from_post": 8,
  "hashtag_set": ["#BPC157", ...],
  "post_time": "18:00",
  "post_day": "Wednesday",
  "hook": "This peptide increased hair tensile strength by 44%"
}

Usage:
    from agents.analytics_agent import run
    path = run()

    # Or log a new post result:
    from agents.analytics_agent import log_post
    log_post({...})
"""
from typing import Optional, List
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.llm import call_llm
from tools.activity_log import log

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
ANALYTICS_DIR = REPO_ROOT / "data" / "analytics"
POSTS_FILE = ANALYTICS_DIR / "posts.json"
CALENDAR_FILE = REPO_ROOT / "data" / "content_calendar.json"

SYSTEM_PROMPT = """You are the performance analyst for @peptidealpharesearch — a science-backed peptides and longevity Instagram account.

Analyse post performance data and produce:

1. TOP PERFORMERS — which posts/formats/topics drove the most saves, shares, follows
2. UNDERPERFORMERS — what didn't work and why (hypothesis)
3. TIMING INSIGHTS — best days/times based on the data
4. FORMAT INSIGHTS — carousels vs reels vs single images
5. HOOK ANALYSIS — which hook styles drove the most engagement (saves/reach ratio)
6. CONTENT RECOMMENDATIONS — specific topics to prioritise next based on what's resonating
7. HASHTAG PERFORMANCE — which tag sets are working

Be data-driven and specific. Reference actual post titles and metrics.
Format as a clean markdown report. Include a Recommendations section at the end with 3-5 actionable next steps."""


def load_posts() -> List[dict]:
    if POSTS_FILE.exists():
        return json.loads(POSTS_FILE.read_text())
    return []


def log_post(post_data: dict) -> None:
    """Add a new post result to the analytics database."""
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    posts = load_posts()

    post_data.setdefault("logged_at", datetime.now().isoformat())
    posts.append(post_data)

    POSTS_FILE.write_text(json.dumps(posts, indent=2))
    log("analytics", "post_logged", post_data.get("title", "unknown"))
    print(f"[Analytics] Post logged: {post_data.get('title', 'unknown')}")


def calculate_engagement_rates(posts: List[dict]) -> List[dict]:
    """Add calculated metrics to each post."""
    enriched = []
    for p in posts:
        p = dict(p)
        reach = p.get("reach", 0) or 1
        p["save_rate"] = round((p.get("saves", 0) / reach) * 100, 2)
        p["engagement_rate"] = round(
            ((p.get("likes", 0) + p.get("saves", 0) + p.get("comments", 0) + p.get("shares", 0)) / reach) * 100, 2
        )
        p["share_rate"] = round((p.get("shares", 0) / reach) * 100, 2)
        enriched.append(p)
    return enriched


def run() -> Path:
    """Generate a performance analysis report from all logged post data."""
    log("analytics", "running", "Generating performance report")
    print("[Analytics Agent] Generating performance report...")

    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    posts = load_posts()

    if not posts:
        print("[Analytics] No post data found. Creating sample posts file...")
        sample = [
            {
                "date": "2026-03-01",
                "title": "Example Post — Add Your Real Data",
                "format": "carousel",
                "reach": 0,
                "likes": 0,
                "saves": 0,
                "shares": 0,
                "comments": 0,
                "follows_from_post": 0,
                "hashtag_set": [],
                "post_time": "18:00",
                "post_day": "Wednesday",
                "hook": "Your slide 1 hook here",
            }
        ]
        POSTS_FILE.write_text(json.dumps(sample, indent=2))
        report_content = (
            "# Analytics Report\n"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            "## No Data Yet\n\n"
            "No post performance data found.\n\n"
            "**To start tracking:**\n"
            "1. Open `data/analytics/posts.json`\n"
            "2. Replace the sample entry with your real post data\n"
            "3. After each post, manually add the metrics from Instagram Insights\n"
            "4. Run `/analytics` again to generate your first report\n\n"
            "**Metrics to track per post:**\n"
            "- reach, likes, saves, shares, comments, follows_from_post\n"
            "- post_time, post_day, hook text, hashtag_set\n"
        )
        date_str = datetime.now().strftime("%Y-%m-%d")
        report_path = ANALYTICS_DIR / f"report_{date_str}.md"
        report_path.write_text(report_content)
        log("analytics", "done", "Empty report — no data yet")
        return report_path

    enriched_posts = calculate_engagement_rates(posts)

    # Sort by engagement rate for summary
    top_posts = sorted(enriched_posts, key=lambda x: x["engagement_rate"], reverse=True)[:5]

    posts_summary = json.dumps(enriched_posts, indent=2)

    user_prompt = f"""Analyse this Instagram post performance data for @peptidealpharesearch:

## Post Data ({len(posts)} posts)
{posts_summary[:4000]}

## Top 5 by Engagement Rate
{json.dumps(top_posts, indent=2)[:1500]}

Today's date: {datetime.now().strftime("%Y-%m-%d")}

Generate a full performance analysis report with actionable recommendations."""

    print("  Analysing performance with LLM...")
    report_text = call_llm(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=2500)

    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = ANALYTICS_DIR / f"report_{date_str}.md"
    report_path.write_text(
        f"# Analytics Report\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Posts analysed: {len(posts)}\n\n"
        f"{report_text}\n"
    )

    log("analytics", "done", f"Report saved: {report_path.name}")
    print(f"[Analytics Agent] Report saved to: {report_path}")
    return report_path


if __name__ == "__main__":
    path = run()
    print(f"\nAnalytics report: {path}")
    print("\n" + path.read_text()[:600])
