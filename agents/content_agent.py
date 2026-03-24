"""
Content Creation Agent — generates Canva carousel designs from approved ideas.

Takes an approved idea from content_calendar.json and:
1. Generates finalized slide copy via Claude
2. Creates a Canva design using the MCP (when run inside Claude Code)
3. Updates the calendar entry with design references

NOTE: Canva MCP calls must be made interactively inside Claude Code.
This agent generates the content package and instructions; the actual
MCP tool calls are made by Claude Code when you run this via the orchestrator.
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
from tools.canva_helpers import (
    get_template_id,
    get_template_structure,
    validate_slide_copy,
    list_configured_templates,
    all_templates_configured,
)

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
CALENDAR_FILE = REPO_ROOT / "data" / "content_calendar.json"
BRAND_FILE = REPO_ROOT / "data" / "brand_guidelines.md"
PROMPT_FILE = REPO_ROOT / "prompts" / "content_agent.md"
OUTPUT_DIR = REPO_ROOT / "data" / "content_packages"


def load_system_prompt() -> str:
    return PROMPT_FILE.read_text()


def load_calendar() -> dict:
    return json.loads(CALENDAR_FILE.read_text())


def save_calendar(calendar: dict) -> None:
    CALENDAR_FILE.write_text(json.dumps(calendar, indent=2))


def get_approved_ideas(calendar: dict) -> List[dict]:
    return [i for i in calendar.get("ideas", []) if i.get("status") == "approved"]


def get_pending_ideas(calendar: dict) -> List[dict]:
    return [i for i in calendar.get("ideas", []) if i.get("status") == "pending"]


def list_ideas(calendar: dict) -> None:
    """Print all ideas with their status and rank."""
    ideas = calendar.get("ideas", [])
    if not ideas:
        print("No ideas in calendar yet.")
        return

    print("\n── Content Calendar ─────────────────────────────────")
    for idea in ideas:
        status = idea.get("status", "?")
        rank = idea.get("rank", "?")
        title = idea.get("title", "Untitled")
        score = idea.get("priority_score", 0)
        day = idea.get("recommended_post_day", "")
        print(f"  [{status:8}] #{rank} [{score:.1f}] {title} — {day}")


def approve_idea(idea_rank: int, calendar: dict) -> Optional[dict]:
    """Mark an idea as approved by rank number."""
    for idea in calendar.get("ideas", []):
        if idea.get("rank") == idea_rank:
            idea["status"] = "approved"
            idea["approved_at"] = datetime.now().isoformat()
            return idea
    return None


def generate_content_package(idea: dict, client: anthropic.Anthropic) -> dict:
    """Use Claude to generate finalized slide copy and caption for an idea."""
    system_prompt = load_system_prompt()
    brand_guidelines = BRAND_FILE.read_text()

    template_type = _infer_template_type(idea.get("pillar", ""))
    structure = get_template_structure(template_type)
    slide_count = structure["slide_count"] if structure else 7

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""Generate the complete content package for this carousel idea.

## Idea Brief
Title: {idea.get('title')}
Pillar: {idea.get('pillar')}
Hook: {idea.get('hook')}
Hook subtext: {idea.get('hook_subtext', '')}
Slide outline:
{chr(10).join(idea.get('slide_outline', []))}
CTA: {idea.get('cta')}
Hashtags: {', '.join(idea.get('hashtags', []))}
Source material: {idea.get('source_material')}

## Template Type
{template_type} ({slide_count} slides)

## Brand Guidelines (excerpt)
{brand_guidelines[:1500]}

## Requirements
- Return ONLY a valid JSON object (no markdown wrapper)
- Follow the exact schema in your system prompt
- Slide copy should be punchy, data-driven, specific
- Caption: 150-250 words, ends with CTA
- Include the full hashtag list at the end of the caption
- design_title should be descriptive and include today's date: {datetime.now().strftime('%Y-%m-%d')}""",
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])

    package = json.loads(raw)

    # Validate slide copy
    warnings = validate_slide_copy(template_type, package.get("slides", []))
    if warnings:
        print("  [Warnings]")
        for w in warnings:
            print(f"    - {w}")

    return package


def _infer_template_type(pillar: str) -> str:
    mapping = {
        "Research Breakdown": "research_breakdown",
        "Protocol Deep Dive": "protocol_deep_dive",
        "Myth Busting": "myth_busting",
        "Mechanism Explainer": "mechanism_explainer",
        "Biohacker Profile": "research_breakdown",  # fallback
    }
    return mapping.get(pillar, "research_breakdown")


def run(idea_rank: Optional[int] = None) -> Path:
    """
    Run the content agent for an approved idea.

    If idea_rank is provided, that idea will be approved and processed.
    If None, processes the highest-ranked approved idea.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    calendar = load_calendar()

    if idea_rank is not None:
        print(f"[Content Agent] Approving idea #{idea_rank}...")
        approved = approve_idea(idea_rank, calendar)
        if not approved:
            raise ValueError(f"No idea with rank {idea_rank} found in calendar.")
        save_calendar(calendar)

    approved_ideas = get_approved_ideas(calendar)
    if not approved_ideas:
        list_ideas(calendar)
        print("\nNo approved ideas. Use --idea <rank> to approve one.")
        sys.exit(0)

    # Process the first approved idea
    idea = approved_ideas[0]
    print(f"[Content Agent] Generating content package for: {idea['title']}")

    print("  Generating slide copy and caption...")
    package = generate_content_package(idea, client)

    # Save content package
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = idea["title"].lower().replace(" ", "_")[:40]
    package_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_{safe_title}.json"
    package_path.write_text(json.dumps(package, indent=2))

    print(f"  Content package saved: {package_path}")

    # Print Canva creation instructions
    template_type = package.get("template_type", "research_breakdown")
    template_id = get_template_id(template_type)

    print("\n── Canva Creation Instructions ──────────────────────")
    if template_id:
        print(f"  Template ID: {template_id}")
        print(f"  Template type: {template_type}")
    else:
        print(f"  ⚠ No template ID configured for '{template_type}'")
        print("  → Add template IDs to tools/canva_helpers.py first")
        print("  → Or use Canva MCP to create a new design from scratch")

    print(f"\n  Design title: {package.get('design_title')}")
    print(f"\n  Slides to populate ({len(package.get('slides', []))}):")
    for slide in package.get("slides", []):
        print(f"    Slide {slide['slide_number']}: {slide.get('headline', '')[:60]}")

    print(f"\n  Caption preview:")
    caption_preview = package.get("caption", "")[:200]
    print(f"    {caption_preview}...")

    # Update calendar entry
    for cal_idea in calendar.get("ideas", []):
        if cal_idea.get("rank") == idea.get("rank") and cal_idea.get("status") == "approved":
            cal_idea["status"] = "content_ready"
            cal_idea["content_package_path"] = str(package_path)
            cal_idea["content_ready_at"] = datetime.now().isoformat()
            break

    save_calendar(calendar)
    print(f"\n[Content Agent] Calendar updated — idea marked as content_ready")

    return package_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--idea", type=int, help="Rank of idea to approve and create")
    parser.add_argument("--list", action="store_true", help="List all ideas")
    args = parser.parse_args()

    if args.list:
        cal = load_calendar()
        list_ideas(cal)
    else:
        result = run(idea_rank=args.idea)
        print(f"\nContent package: {result}")
