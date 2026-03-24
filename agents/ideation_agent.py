"""
Ideation Agent — synthesizes research briefs into ranked carousel ideas.

Reads latest brief from data/research_briefs/
Outputs ranked ideas + timing to data/content_calendar.json
"""
from typing import Optional, List
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
BRIEFS_DIR = REPO_ROOT / "data" / "research_briefs"
CALENDAR_FILE = REPO_ROOT / "data" / "content_calendar.json"
BRAND_FILE = REPO_ROOT / "data" / "brand_guidelines.md"
PROMPT_FILE = REPO_ROOT / "prompts" / "ideation_agent.md"


def load_system_prompt() -> str:
    return PROMPT_FILE.read_text()


def load_brand_guidelines() -> str:
    return BRAND_FILE.read_text()


def get_latest_brief() -> tuple[Path, str]:
    """Find and return the most recent research brief."""
    brief_files = sorted(BRIEFS_DIR.glob("*.md"), reverse=True)
    if not brief_files:
        raise FileNotFoundError(
            f"No research briefs found in {BRIEFS_DIR}. Run the research agent first."
        )
    latest = brief_files[0]
    return latest, latest.read_text()


def load_existing_calendar() -> dict:
    """Load existing content calendar (to avoid duplicate ideas)."""
    if CALENDAR_FILE.exists():
        return json.loads(CALENDAR_FILE.read_text())
    return {"ideas": []}


def extract_existing_titles(calendar: dict) -> List[str]:
    return [idea.get("title", "") for idea in calendar.get("ideas", [])]


def run(brief_path: Optional[Path] = None) -> Path:
    """
    Run the ideation agent from the latest (or specified) research brief.
    Returns path to updated content_calendar.json.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("[Ideation Agent] Loading research brief...")

    if brief_path is None:
        brief_path, brief_content = get_latest_brief()
    else:
        brief_content = brief_path.read_text()

    print(f"  Using brief: {brief_path.name}")

    brand_guidelines = load_brand_guidelines()
    system_prompt = load_system_prompt()
    existing_calendar = load_existing_calendar()
    existing_titles = extract_existing_titles(existing_calendar)

    existing_titles_str = (
        "\n".join(f"- {t}" for t in existing_titles)
        if existing_titles
        else "None yet"
    )

    print("  Generating content ideas...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""Generate 7 ranked carousel ideas based on this research brief.

## Research Brief
{brief_content}

## Brand Guidelines (summary)
{brand_guidelines[:2000]}

## Already in Calendar (avoid duplicates)
{existing_titles_str}

## Requirements
- Return ONLY a valid JSON array of idea objects (no markdown wrapper, no explanation)
- Each idea must follow the exact schema in your system prompt
- Rank by priority_score (highest first)
- Include recommended_post_day and recommended_post_time_est for each idea
- Make hooks punchy, specific, and data-driven
- Today's date: {datetime.now().strftime("%Y-%m-%d")}""",
            }
        ],
    )

    raw_response = response.content[0].text.strip()

    # Strip markdown code blocks if Claude wrapped it
    if raw_response.startswith("```"):
        lines = raw_response.split("\n")
        raw_response = "\n".join(lines[1:-1])

    try:
        new_ideas = json.loads(raw_response)
    except json.JSONDecodeError as e:
        print(f"[Ideation Agent] JSON parse error: {e}")
        print("Raw response snippet:", raw_response[:300])
        raise

    # Update calendar
    calendar = load_existing_calendar()
    calendar["last_updated"] = datetime.now().isoformat()
    calendar["generated_from_brief"] = brief_path.name

    # Add status field to each new idea
    for idea in new_ideas:
        idea["status"] = "pending"           # pending | approved | created | posted
        idea["created_at"] = datetime.now().isoformat()
        idea["brief_source"] = brief_path.name

    # Prepend new ideas (most recent first)
    calendar["ideas"] = new_ideas + calendar.get("ideas", [])

    CALENDAR_FILE.write_text(json.dumps(calendar, indent=2))
    print(f"[Ideation Agent] Added {len(new_ideas)} ideas to {CALENDAR_FILE}")

    # Print summary
    print("\n── Content Ideas Generated ──────────────────────────")
    for idea in new_ideas:
        print(
            f"  #{idea['rank']} [{idea['priority_score']:.1f}] {idea['title']}"
            f" — {idea['recommended_post_day']} {idea['recommended_post_time_est']}"
        )

    return CALENDAR_FILE


if __name__ == "__main__":
    result_path = run()
    print(f"\nDone. Calendar updated: {result_path}")
