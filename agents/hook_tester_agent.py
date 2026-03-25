"""
Hook Tester Agent — generates 5 hook variants for an approved idea.

For each approved idea, produces 5 distinct hooks (scroll-stopper first lines)
with different emotional angles: curiosity, shock, authority, relatability, FOMO.
Saves variants back into content_calendar.json under the idea's hook_variants field.

Usage:
    from agents.hook_tester_agent import run
    variants = run(rank=1)          # by idea rank
    variants = run()                 # latest approved idea
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
CALENDAR_FILE = REPO_ROOT / "data" / "content_calendar.json"

SYSTEM_PROMPT = """You are a social media hook specialist for @peptidealpharesearch — a science-backed peptides and longevity Instagram account.

Your job is to write 5 distinct hook variants for carousel slide 1. Each hook must:
- Be under 12 words
- Be scroll-stopping and specific (use numbers, named peptides, or surprising claims)
- Be scientifically accurate — no exaggeration beyond what's in the brief
- NOT start with "I" or "We"
- NOT use generic openers like "Did you know..." or "Here's the thing..."

Return ONLY a valid JSON array of 5 objects, each with:
{
  "variant": 1,
  "angle": "curiosity|shock|authority|relatability|fomo",
  "hook": "the hook text",
  "reasoning": "one-sentence rationale"
}

No markdown wrapper. No explanation. JSON array only."""


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
    # Latest approved or pending
    for status in ("approved", "pending"):
        match = next((i for i in ideas if i.get("status") == status), None)
        if match:
            return match
    raise ValueError("No approved or pending ideas in calendar. Run /ideation first.")


def run(rank: Optional[int] = None) -> List[dict]:
    """Generate 5 hook variants for the specified (or latest) idea."""
    log("hook_tester", "running", f"Generating hooks for rank={rank}")
    print(f"[Hook Tester] Generating hooks for rank={rank}...")

    idea = get_idea(rank)
    title = idea.get("title", "")
    hook = idea.get("hook", "")
    slide_outline = idea.get("slide_outline", [])
    key_stat = idea.get("key_stat", "")

    user_prompt = f"""Generate 5 hook variants for this carousel idea:

Title: {title}
Original hook: {hook}
Key stat/claim: {key_stat}
Slide topics: {', '.join(str(s) for s in slide_outline[:4]) if slide_outline else 'N/A'}

Produce 5 distinct hooks with these emotional angles in order:
1. Curiosity — makes them need to know more
2. Shock — surprising or counterintuitive fact
3. Authority — scientific credibility signal
4. Relatability — speaks to a frustration or goal they have
5. FOMO — what they're missing out on

Return JSON array only."""

    raw = call_llm(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=1024).strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])

    try:
        variants = json.loads(raw)
    except json.JSONDecodeError as e:
        log("hook_tester", "error", f"JSON parse error: {e}")
        raise

    # Save back to calendar
    cal = load_calendar()
    for idea_entry in cal.get("ideas", []):
        if idea_entry.get("rank") == idea.get("rank"):
            idea_entry["hook_variants"] = variants
            idea_entry["hooks_generated_at"] = datetime.now().isoformat()
            break

    CALENDAR_FILE.write_text(json.dumps(cal, indent=2))
    log("hook_tester", "done", f"5 hooks saved for '{title}'")

    print(f"[Hook Tester] 5 hooks generated for: {title}")
    for v in variants:
        print(f"  [{v['angle'].upper()}] {v['hook']}")

    return variants


if __name__ == "__main__":
    import sys as _sys
    rank_arg = int(_sys.argv[1]) if len(_sys.argv) > 1 else None
    run(rank=rank_arg)
