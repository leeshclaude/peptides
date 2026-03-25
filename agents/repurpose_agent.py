"""
Repurpose Agent — converts an approved carousel into 3 platform formats.

Given an approved idea (and optionally its content package), produces:
1. Twitter/X thread (8-10 tweets, numbered, hook + insights + CTA)
2. LinkedIn post (professional tone, 200-300 words, 5 hashtags)
3. Reel script (30-60 sec, hook → 3 key points → CTA, with B-roll suggestions)

Output saved to data/repurposed/YYYY-MM-DD-rank-N/

Usage:
    from agents.repurpose_agent import run
    output_dir = run(rank=1)
"""
from typing import Optional
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
CALENDAR_FILE = REPO_ROOT / "data" / "content_calendar.json"
REPURPOSED_DIR = REPO_ROOT / "data" / "repurposed"
PACKAGES_DIR = REPO_ROOT / "data" / "content_packages"


TWITTER_PROMPT = """You are a viral Twitter/X thread writer for @peptidealpharesearch — a science-backed peptides and longevity account.

Write a thread of 8-10 tweets. Rules:
- Tweet 1: bold hook, no fluff, max 200 chars (this is the scroll-stopper)
- Tweets 2-8: one insight per tweet. Short sentences. White space. Real data.
- Tweet 9: actionable takeaway or protocol
- Tweet 10: CTA — follow for more, retweet, or ask a question
- Each tweet numbered: "1/" "2/" etc.
- No hashtags except tweet 10 (max 3)
- Use line breaks generously — Twitter rewards white space

Return plain text only. No JSON. No explanation."""


LINKEDIN_PROMPT = """You are a LinkedIn content writer for a peptide and longevity science account.

Write a single LinkedIn post (200-300 words). Rules:
- Open with a punchy 1-2 line hook (not "I" or "We")
- Write for a professional audience: clinicians, biohackers, longevity investors, health entrepreneurs
- Include the key scientific mechanism or stat
- Use short paragraphs (2-3 sentences max)
- End with a thought-provoking question to drive comments
- 5 hashtags only, at the very end (professional niche tags)
- Tone: authoritative, measured, credible — not hype

Return plain text only. No JSON. No explanation."""


REEL_PROMPT = """You are a short-form video script writer for @peptidealpharesearch on Instagram.

Write a 30-60 second Reel script. Format:

HOOK (0-3 sec): [Talking head or text overlay — scroll-stopping first line]
POINT 1 (3-15 sec): [Key insight 1 — spoken line + B-roll suggestion]
POINT 2 (15-27 sec): [Key insight 2 — spoken line + B-roll suggestion]
POINT 3 (27-40 sec): [Key insight 3 or stat — spoken line + B-roll suggestion]
CTA (40-50 sec): [Call to action — follow, save, comment]
OUTRO (50-60 sec): [Optional: branding, music fade]

For each section include:
- SPOKEN: (exact words to say)
- B-ROLL: (visual suggestion — keep it achievable: phone camera, Canva text, stock clip)
- TEXT OVERLAY: (optional on-screen text)

Return plain text only. No JSON. No explanation."""


def load_calendar() -> dict:
    if CALENDAR_FILE.exists():
        return json.loads(CALENDAR_FILE.read_text())
    return {"ideas": []}


def get_idea(rank: Optional[int] = None) -> dict:
    cal = load_calendar()
    ideas = cal.get("ideas", [])
    if rank is not None:
        idea = next((i for i in ideas if i.get("rank") == rank), None)
        if not idea:
            raise ValueError(f"No idea found with rank {rank}")
        return idea
    for status in ("content_ready", "approved"):
        match = next((i for i in ideas if i.get("status") == status), None)
        if match:
            return match
    raise ValueError("No approved ideas found.")


def build_content_context(idea: dict) -> str:
    title = idea.get("title", "")
    hook = idea.get("hook", "")
    key_stat = idea.get("key_stat", "")
    slide_outline = idea.get("slide_outline", [])
    cta = idea.get("cta", "")

    # Try to load content package for richer context
    package_context = ""
    package_dir = PACKAGES_DIR / f"rank-{idea.get('rank', '')}"
    if package_dir.exists():
        for f in package_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                package_context = f"\n\nContent Package:\n{json.dumps(data, indent=2)[:2000]}"
                break
            except Exception:
                pass

    return f"""Title: {title}
Hook: {hook}
Key stat: {key_stat}
Slide outline: {json.dumps(slide_outline, indent=2) if slide_outline else 'N/A'}
CTA: {cta}{package_context}"""


def run(rank: Optional[int] = None) -> Path:
    """Repurpose the specified (or latest) idea into 3 formats."""
    log("repurpose", "running", f"Repurposing rank={rank}")
    print(f"[Repurpose Agent] Repurposing rank={rank}...")

    idea = get_idea(rank)
    title = idea.get("title", "Untitled")
    content_ctx = build_content_context(idea)

    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = REPURPOSED_DIR / f"{date_str}-rank-{idea.get('rank', 'X')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("  Writing Twitter/X thread...")
    twitter_text = call_llm(
        system=TWITTER_PROMPT,
        user=f"Write a Twitter thread based on:\n\n{content_ctx}",
        max_tokens=1200,
    )
    (output_dir / "twitter_thread.txt").write_text(twitter_text)

    print("  Writing LinkedIn post...")
    linkedin_text = call_llm(
        system=LINKEDIN_PROMPT,
        user=f"Write a LinkedIn post based on:\n\n{content_ctx}",
        max_tokens=600,
    )
    (output_dir / "linkedin_post.txt").write_text(linkedin_text)

    print("  Writing Reel script...")
    reel_text = call_llm(
        system=REEL_PROMPT,
        user=f"Write a Reel script based on:\n\n{content_ctx}",
        max_tokens=1000,
    )
    (output_dir / "reel_script.txt").write_text(reel_text)

    # Write index
    index = (
        f"# Repurposed Content: {title}\n"
        f"Generated: {datetime.now().isoformat()}\n\n"
        f"- twitter_thread.txt\n"
        f"- linkedin_post.txt\n"
        f"- reel_script.txt\n"
    )
    (output_dir / "README.md").write_text(index)

    # Update calendar
    cal = load_calendar()
    for idea_entry in cal.get("ideas", []):
        if idea_entry.get("rank") == idea.get("rank"):
            idea_entry["repurposed_dir"] = str(output_dir.relative_to(REPO_ROOT))
            idea_entry["repurposed_at"] = datetime.now().isoformat()
            break
    CALENDAR_FILE.write_text(json.dumps(cal, indent=2))

    log("repurpose", "done", f"3 formats saved to {output_dir.name}")
    print(f"[Repurpose Agent] Done. Formats saved to: {output_dir}")
    return output_dir


if __name__ == "__main__":
    import sys as _sys
    rank_arg = int(_sys.argv[1]) if len(_sys.argv) > 1 else None
    out = run(rank=rank_arg)
    print(f"\nRepurposed content in: {out}")
