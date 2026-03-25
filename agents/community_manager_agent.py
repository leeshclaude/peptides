"""
Community Manager Agent — drafts replies to inbound comments on your posts.

Takes a list of comments (as text input or from data/inbound_comments.json)
and for each comment produces 3 reply options ranked by tone:
1. Value-add (adds science, resource, or deeper insight)
2. Engagement (asks a follow-up question, keeps the convo going)
3. Warm (brief, friendly, human)

Output saved to data/reply_queue.md for manual copy-paste.

Usage:
    from agents.community_manager_agent import run
    path = run()                       # reads data/inbound_comments.json
    path = run(comments=[...])        # pass comments directly
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
INBOUND_FILE = REPO_ROOT / "data" / "inbound_comments.json"
REPLY_QUEUE_FILE = REPO_ROOT / "data" / "reply_queue.md"

SYSTEM_PROMPT = """You are the community manager for @peptidealpharesearch — a science-backed peptides and longevity Instagram account.

Your replies must:
- Sound human and genuine (not like a bot)
- Reflect our brand: knowledgeable, warm, non-salesy
- NEVER give medical advice or recommend dosing
- Use first-person singular ("I" not "we")
- Be appropriately concise for Instagram comments (1-4 sentences max)
- Optionally use 1 emoji if it fits naturally — never force it

For each comment, return EXACTLY 3 reply options as a JSON array:
[
  {
    "type": "value_add",
    "reply": "..."
  },
  {
    "type": "engagement",
    "reply": "..."
  },
  {
    "type": "warm",
    "reply": "..."
  }
]

Return JSON array only. No markdown wrapper. No explanation. One array per comment."""


def load_inbound_comments() -> List[dict]:
    """Load comments from inbound_comments.json or return empty list."""
    if INBOUND_FILE.exists():
        data = json.loads(INBOUND_FILE.read_text())
        if isinstance(data, list):
            return data
        return data.get("comments", [])
    return []


def run(comments: Optional[List[dict]] = None) -> Path:
    """Draft reply options for all inbound comments."""
    log("community_manager", "running", "Drafting comment replies")
    print("[Community Manager] Drafting replies to comments...")

    if comments is None:
        comments = load_inbound_comments()

    if not comments:
        msg = (
            "No comments to process.\n\n"
            "Add comments to data/inbound_comments.json in this format:\n"
            '[\n  {"username": "@user", "comment": "their comment text", "post": "post title"}\n]'
        )
        REPLY_QUEUE_FILE.write_text(
            f"# Reply Queue\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"No inbound comments found.\n\n{msg}\n"
        )
        log("community_manager", "done", "No comments to process")
        print("[Community Manager] No comments found. Queue file updated with instructions.")
        return REPLY_QUEUE_FILE

    sections = [
        f"# Reply Queue\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"**{len(comments)} comment(s) to reply to**\n",
        "---\n",
    ]

    for idx, comment_data in enumerate(comments, 1):
        username = comment_data.get("username", "@unknown")
        comment_text = comment_data.get("comment", "")
        post = comment_data.get("post", "recent post")

        if not comment_text:
            continue

        print(f"  Drafting replies for comment {idx}/{len(comments)}...")

        user_prompt = f"""Draft 3 reply options for this Instagram comment on our post about "{post}":

Username: {username}
Comment: "{comment_text}"

Return 3 reply options as JSON array."""

        raw = call_llm(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=600).strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])

        try:
            replies = json.loads(raw)
        except json.JSONDecodeError:
            replies = [{"type": "fallback", "reply": raw[:200]}]

        sections.append(f"## Comment {idx}: {username}")
        sections.append(f'> "{comment_text}"')
        sections.append(f"Post: _{post}_\n")

        for r in replies:
            rtype = r.get("type", "reply").replace("_", " ").title()
            reply_text = r.get("reply", "")
            sections.append(f"**{rtype}:**")
            sections.append(f"{reply_text}\n")

        sections.append("---\n")

    REPLY_QUEUE_FILE.write_text("\n".join(sections))
    log("community_manager", "done", f"{len(comments)} comments processed")
    print(f"[Community Manager] Reply queue saved to: {REPLY_QUEUE_FILE}")
    return REPLY_QUEUE_FILE


if __name__ == "__main__":
    path = run()
    print(f"\nReply queue: {path}")
    print("\n" + path.read_text()[:800])
