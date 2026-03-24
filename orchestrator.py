#!/usr/bin/env python3
from typing import Optional, List
"""
Orchestrator — main pipeline runner for @peptidealpharesearch agent system.

Usage:
    python orchestrator.py --run research        # Research brief only
    python orchestrator.py --run ideation        # Ideation from latest brief
    python orchestrator.py --run content         # Canva creation for approved idea
    python orchestrator.py --run content --idea 2  # Approve idea #2 and create
    python orchestrator.py --run engagement      # Draft engagement comments
    python orchestrator.py --run full            # Full pipeline (research + ideation)
    python orchestrator.py --list                # List content calendar
    python orchestrator.py --status              # Show pipeline status
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


def check_env() -> bool:
    """Verify required environment variables are set."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("  1. Copy .env.example to .env")
        print("  2. Add your Anthropic API key")
        return False
    if key == "your_anthropic_api_key_here":
        print("ERROR: Replace the placeholder in .env with your actual API key.")
        return False
    return True


def run_research() -> bool:
    """Run the research agent."""
    from agents.research_agent import run
    try:
        output = run()
        print(f"\n✓ Research brief: {output}")
        return True
    except Exception as e:
        print(f"\n✗ Research agent failed: {e}")
        return False


def run_ideation(brief_path=None) -> bool:
    """Run the ideation agent."""
    from agents.ideation_agent import run
    from pathlib import Path
    try:
        bp = Path(brief_path) if brief_path else None
        output = run(brief_path=bp)
        print(f"\n✓ Content calendar updated: {output}")
        return True
    except FileNotFoundError as e:
        print(f"\n✗ {e}")
        print("  Run research first: python orchestrator.py --run research")
        return False
    except Exception as e:
        print(f"\n✗ Ideation agent failed: {e}")
        return False


def run_content(idea_rank: Optional[int] = None) -> bool:
    """Run the content creation agent."""
    from agents.content_agent import run, list_ideas, load_calendar
    try:
        output = run(idea_rank=idea_rank)
        print(f"\n✓ Content package: {output}")
        print("\n── Next Steps ────────────────────────────────────────")
        print("  1. Open the content package JSON in data/content_packages/")
        print("  2. Ask Claude Code to update Canva:")
        print('     "Update Canva with the content package at [path]"')
        print("     Claude will use the canva-peptide-carousel skill (template DAHEVyvHuDg)")
        print("  3. Review thumbnail previews, approve, then export and schedule")
        return True
    except Exception as e:
        print(f"\n✗ Content agent failed: {e}")
        return False


def run_engagement(overwrite: bool = False) -> bool:
    """Run the engagement agent."""
    from agents.engagement_agent import run
    try:
        output = run(append=not overwrite)
        print(f"\n✓ Engagement queue: {output}")
        print("\n── Next Steps ────────────────────────────────────────")
        print("  1. Open data/engagement_queue.md")
        print("  2. Review comment options for each post")
        print("  3. Copy-paste your chosen comments into Instagram manually")
        return True
    except Exception as e:
        print(f"\n✗ Engagement agent failed: {e}")
        return False


def show_status() -> None:
    """Display pipeline status."""
    from pathlib import Path
    import json

    repo_root = Path(__file__).parent
    briefs_dir = repo_root / "data" / "research_briefs"
    calendar_file = repo_root / "data" / "content_calendar.json"
    engagement_file = repo_root / "data" / "engagement_queue.md"

    print("\n── @peptidealpharesearch Pipeline Status ────────────")

    # Research briefs
    briefs = sorted(briefs_dir.glob("*.md"), reverse=True) if briefs_dir.exists() else []
    if briefs:
        latest = briefs[0]
        age = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
        print(f"\n  Research Brief:  {latest.name} ({age}d old)")
    else:
        print("\n  Research Brief:  None — run 'python orchestrator.py --run research'")

    # Content calendar
    if calendar_file.exists():
        cal = json.loads(calendar_file.read_text())
        ideas = cal.get("ideas", [])
        pending = [i for i in ideas if i.get("status") == "pending"]
        approved = [i for i in ideas if i.get("status") == "approved"]
        ready = [i for i in ideas if i.get("status") == "content_ready"]
        posted = [i for i in ideas if i.get("status") == "posted"]
        print(f"\n  Content Calendar:")
        print(f"    {len(pending)} pending · {len(approved)} approved · {len(ready)} ready · {len(posted)} posted")
        if pending:
            print(f"    Top idea: #{pending[0]['rank']} {pending[0]['title']} [{pending[0].get('priority_score', 0):.1f}]")
    else:
        print("\n  Content Calendar: Empty — run ideation after research")

    # Engagement queue
    if engagement_file.exists():
        age = (datetime.now() - datetime.fromtimestamp(engagement_file.stat().st_mtime)).total_seconds() / 3600
        print(f"\n  Engagement Queue: Updated {age:.1f}h ago")
    else:
        print("\n  Engagement Queue: None")

    print()


def show_calendar() -> None:
    """Display content calendar."""
    from agents.content_agent import list_ideas, load_calendar
    list_ideas(load_calendar())
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="@peptidealpharesearch content automation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--run",
        choices=["research", "ideation", "content", "engagement", "full"],
        help="Which agent to run",
    )
    parser.add_argument(
        "--idea",
        type=int,
        help="Idea rank to approve for content creation",
    )
    parser.add_argument(
        "--brief",
        type=str,
        help="Path to specific brief file (for ideation)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List content calendar",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show pipeline status",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite engagement queue instead of appending",
    )

    args = parser.parse_args()

    if args.list:
        show_calendar()
        return

    if args.status or not args.run:
        show_status()
        if not args.run:
            parser.print_help()
        return

    if not check_env():
        sys.exit(1)

    success = True

    if args.run == "research":
        success = run_research()

    elif args.run == "ideation":
        success = run_ideation(brief_path=args.brief)

    elif args.run == "content":
        success = run_content(idea_rank=args.idea)

    elif args.run == "engagement":
        success = run_engagement(overwrite=args.overwrite)

    elif args.run == "full":
        print("Running full pipeline: research → ideation")
        print("=" * 50)
        if run_research():
            print()
            run_ideation()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
