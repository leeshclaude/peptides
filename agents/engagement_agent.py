"""
Engagement Agent — drafts comments for target accounts' recent posts.

Fetches recent posts from high-priority competitor accounts (public web)
and generates 3 comment options per post (value-add, question, insight).

Outputs to data/engagement_queue.md for manual copy-paste into Instagram.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.llm import call_llm

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
COMPETITORS_FILE = REPO_ROOT / "data" / "competitor_accounts.json"
ENGAGEMENT_QUEUE_FILE = REPO_ROOT / "data" / "engagement_queue.md"
PROMPT_FILE = REPO_ROOT / "prompts" / "engagement_agent.md"

# Number of top-priority accounts to check per run
MAX_ACCOUNTS = 5
# Number of posts per account to draft comments for
POSTS_PER_ACCOUNT = 2


def load_system_prompt() -> str:
    return PROMPT_FILE.read_text()


def load_competitors() -> dict:
    return json.loads(COMPETITORS_FILE.read_text())


def get_priority_accounts(competitors: dict) -> List[dict]:
    """Return high-priority Instagram accounts, sorted by priority."""
    accounts = competitors.get("instagram_accounts", [])
    high = [a for a in accounts if a.get("priority") == "high"]
    medium = [a for a in accounts if a.get("priority") == "medium"]
    return (high + medium)[:MAX_ACCOUNTS]


def fetch_instagram_posts_context(handle: str) -> str:
    """
    Build context string for Claude to research this account's recent posts.
    Since Instagram doesn't have a public API, we instruct Claude to search
    for recent public content from the account.
    """
    return f"Instagram account: @{handle} — search for their most recent posts (last 24-48 hours)"


def generate_engagement_comments(accounts: List[dict]) -> str:
    """Draft engagement comments for target accounts' recent posts."""
    system_prompt = load_system_prompt()

    account_list = "\n".join(
        f"- @{a['handle']} ({a.get('notes', '')})"
        for a in accounts
    )

    user_prompt = f"""Draft engagement comments for @peptidealpharesearch to post on these accounts' recent content.

## Target Accounts (prioritized)
{account_list}

## Instructions
1. For each account, search for their most recent posts (last 24-48 hours)
2. For each relevant post found, draft 3 comment options (value-add, question, insight)
3. Focus on posts about: peptides, longevity, biohacking, research, protocols
4. Skip posts that are purely promotional or unrelated to the niche
5. Follow the exact output format in your system prompt
6. Aim for {POSTS_PER_ACCOUNT} posts per account where possible

## Context
- We are @peptidealpharesearch — a science-forward peptide/longevity account
- Comments should reflect genuine expertise and add real value
- Tone: knowledgeable, curious, collegial — never promotional
- Today: {datetime.now().strftime("%Y-%m-%d %H:%M")} EST

Generate the full engagement queue in the format specified in your system prompt."""

    return call_llm(system=system_prompt, user=user_prompt, max_tokens=4000)


def load_existing_queue() -> str:
    if ENGAGEMENT_QUEUE_FILE.exists():
        return ENGAGEMENT_QUEUE_FILE.read_text()
    return ""


def run(append: bool = True) -> Path:
    """
    Run the engagement agent and output comment drafts.
    If append=True, prepends new content to existing queue.
    """
    competitors = load_competitors()

    print("[Engagement Agent] Identifying target accounts...")
    accounts = get_priority_accounts(competitors)
    print(f"  Targeting {len(accounts)} accounts: {', '.join('@' + a['handle'] for a in accounts)}")

    print("  Researching recent posts and drafting comments...")
    comments_content = generate_engagement_comments(accounts)

    # Build the output file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"""# Engagement Queue
Generated: {timestamp}
Accounts monitored: {', '.join('@' + a['handle'] for a in accounts)}

> **Instructions:** Copy-paste comments manually into Instagram.
> Comments are ordered by recommended priority.
> Post comments within 1-2 hours of the target post for best visibility.

---

"""

    if append and ENGAGEMENT_QUEUE_FILE.exists():
        existing = load_existing_queue()
        # Find the first --- divider and insert after header
        new_content = header + comments_content + "\n\n---\n\n## Previous Queue\n\n" + existing
    else:
        new_content = header + comments_content

    ENGAGEMENT_QUEUE_FILE.write_text(new_content)
    print(f"[Engagement Agent] Queue saved to: {ENGAGEMENT_QUEUE_FILE}")

    # Print preview
    lines = comments_content.split("\n")
    preview_lines = [l for l in lines[:30] if l.strip()][:10]
    print("\n── Preview ──────────────────────────────────────────")
    for line in preview_lines:
        print(f"  {line}")
    print(f"  ... ({len(lines)} total lines)")

    return ENGAGEMENT_QUEUE_FILE


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite queue instead of appending",
    )
    args = parser.parse_args()

    result = run(append=not args.overwrite)
    print(f"\nDone. Engagement queue: {result}")
