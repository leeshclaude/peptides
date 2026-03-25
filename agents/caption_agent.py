"""
Caption Agent — writes the full Instagram caption for an approved idea.

Produces a caption with:
- Opening hook (matches chosen slide 1 hook)
- 3-5 sentence value body
- CTA (save/share/comment prompt)
- Rotating hashtag set (30 tags — mix of niche, mid, broad)
- Scientific disclaimer

Output saved to data/captions/YYYY-MM-DD-rank-N.md

Usage:
    from agents.caption_agent import run
    path = run(rank=1)
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
CAPTIONS_DIR = REPO_ROOT / "data" / "captions"
BRAND_FILE = REPO_ROOT / "data" / "brand_guidelines.md"

SYSTEM_PROMPT = """You are the caption writer for @peptidealpharesearch — a science-backed peptides and longevity Instagram account.

Brand voice: Authoritative but accessible. Science-first. No hype. No fluff. Speak to educated biohackers, longevity enthusiasts, and health-optimisers.

Caption structure you MUST follow:
1. HOOK LINE — the strongest 1-2 sentence opener (use the slide 1 hook if available, else write one)
2. BODY — 3-5 sentences expanding the key insight. Reference specific peptides, mechanisms, or stats.
3. CTA — one clear call to action. Rotate between: "Save this for later", "Share with someone who needs this", "Drop a 💊 if you found this useful", "What peptide are you researching? Comment below."
4. HASHTAGS — exactly 30 hashtags on their own line. Mix:
   - 5 niche (e.g. #peptidescience, #BPC157, #GHK-Cu)
   - 10 mid-tier (e.g. #biohacking, #longevityresearch, #peptides)
   - 10 broad (e.g. #antiaging, #healthoptimization, #wellness)
   - 5 trending/rotating (e.g. #longevity2025, #healthtech)
5. DISCLAIMER — end with: "📚 For educational purposes only. Not medical advice. Always consult a qualified healthcare professional."

Return the caption as plain text (no JSON). Include all 5 sections in order."""


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
    for status in ("approved", "content_ready"):
        match = next((i for i in ideas if i.get("status") == status), None)
        if match:
            return match
    raise ValueError("No approved ideas found. Run /ideation and approve an idea first.")


def run(rank: Optional[int] = None) -> Path:
    """Write caption for the specified (or latest approved) idea."""
    log("caption", "running", f"Writing caption for rank={rank}")
    print(f"[Caption Agent] Writing caption for rank={rank}...")

    idea = get_idea(rank)
    title = idea.get("title", "")
    hook = idea.get("hook", "")
    slide_outline = idea.get("slide_outline", [])
    cta = idea.get("cta", "")
    hashtags = idea.get("hashtags", [])
    key_stat = idea.get("key_stat", "")

    # Prefer chosen hook variant if available
    chosen_hook = hook
    variants = idea.get("hook_variants", [])
    if variants:
        chosen_hook = variants[0].get("hook", hook)

    brand_guidelines = ""
    if BRAND_FILE.exists():
        brand_guidelines = BRAND_FILE.read_text()[:1500]

    user_prompt = f"""Write a full Instagram caption for this carousel post:

Title: {title}
Slide 1 hook: {chosen_hook}
Key stat/claim: {key_stat}
Slide topics: {json.dumps(slide_outline, indent=2) if slide_outline else 'N/A'}
Suggested CTA: {cta}
Suggested hashtags (can supplement): {', '.join(hashtags[:15]) if hashtags else 'N/A'}

Brand guidelines:
{brand_guidelines}

Write the full caption now. Plain text only."""

    caption_text = call_llm(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=1500)

    CAPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = CAPTIONS_DIR / f"{date_str}-rank-{idea.get('rank', 'X')}.md"

    output_path.write_text(
        f"# Caption: {title}\n"
        f"Generated: {datetime.now().isoformat()}\n\n"
        f"---\n\n"
        f"{caption_text}\n"
    )

    # Update calendar with caption path
    cal = load_calendar()
    for idea_entry in cal.get("ideas", []):
        if idea_entry.get("rank") == idea.get("rank"):
            idea_entry["caption_file"] = str(output_path.relative_to(REPO_ROOT))
            idea_entry["caption_generated_at"] = datetime.now().isoformat()
            break
    CALENDAR_FILE.write_text(json.dumps(cal, indent=2))

    log("caption", "done", f"Caption saved: {output_path.name}")
    print(f"[Caption Agent] Caption saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    import sys as _sys
    rank_arg = int(_sys.argv[1]) if len(_sys.argv) > 1 else None
    path = run(rank=rank_arg)
    print(f"\nCaption saved: {path}")
    print("\n" + path.read_text())
