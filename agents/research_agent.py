"""
Research Agent — gathers peptide/longevity research and community intelligence.

Outputs a dated markdown brief to data/research_briefs/YYYY-MM-DD.md
"""
from typing import Optional, List
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.pubmed import get_peptide_research
from tools.llm import call_llm

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
BRIEFS_DIR = REPO_ROOT / "data" / "research_briefs"
COMPETITORS_FILE = REPO_ROOT / "data" / "competitor_accounts.json"
PROMPT_FILE = REPO_ROOT / "prompts" / "research_agent.md"


def load_system_prompt() -> str:
    return PROMPT_FILE.read_text()


def load_competitors() -> dict:
    return json.loads(COMPETITORS_FILE.read_text())


def fetch_pubmed_data() -> str:
    """Fetch recent peptide and longevity research from PubMed."""
    print("  Fetching PubMed data...")
    data = get_peptide_research(days_back=7)

    sections = []

    if data["peptide_studies"]:
        sections.append("### Peptide Studies (PubMed, last 7 days)")
        for study in data["peptide_studies"][:10]:
            sections.append(
                f"- **{study['title']}** | {study['journal']} | {study['pub_date']} | {study['url']}"
            )
    else:
        sections.append("### Peptide Studies (PubMed)\nNo results in last 7 days.")

    if data["longevity_studies"]:
        sections.append("\n### Longevity Studies (PubMed, last 7 days)")
        for study in data["longevity_studies"][:10]:
            sections.append(
                f"- **{study['title']}** | {study['journal']} | {study['pub_date']} | {study['url']}"
            )

    if data["preprints"]:
        sections.append("\n### Preprints (bioRxiv, last 7 days)")
        for pre in data["preprints"][:5]:
            sections.append(
                f"- **{pre['title']}** [PREPRINT] | {pre['date']} | {pre['url']}"
            )

    return "\n".join(sections)


def build_research_context(pubmed_data: str, competitors: dict) -> str:
    competitor_handles = [
        acc["handle"] for acc in competitors.get("instagram_accounts", [])
        if acc.get("priority") == "high"
    ]
    reddit_communities = [
        c["subreddit"] for c in competitors.get("reddit_communities", [])
    ]

    return f"""## Current Date
{datetime.now().strftime("%Y-%m-%d")}

## PubMed Research Data
{pubmed_data}

## Target Instagram Accounts (for competitor analysis)
{', '.join(f'@{h}' for h in competitor_handles)}

## Reddit Communities (for hot topics)
{', '.join(reddit_communities)}

## Instructions
1. Use the PubMed data above as your primary scientific source
2. For each Reddit community listed, note trending topics and questions in the peptide/longevity niche
3. For competitor Instagram accounts, note common content themes
4. Synthesize into a structured research brief per the format in your system prompt
5. Be specific — include actual study titles, stats, and mechanisms

Today's date: {datetime.now().strftime("%Y-%m-%d")}"""


def run(days_back: int = 7, output_path: Optional[Path] = None) -> Path:
    """Run the research agent and save output to a dated brief file."""
    print("[Research Agent] Starting research pipeline...")

    pubmed_data = fetch_pubmed_data()
    competitors = load_competitors()
    system_prompt = load_system_prompt()
    context = build_research_context(pubmed_data, competitors)

    print("  Synthesizing research brief...")
    brief_content = call_llm(system=system_prompt, user=context, max_tokens=4096)

    if output_path is None:
        BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = BRIEFS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"

    output_path.write_text(brief_content)
    print(f"[Research Agent] Brief saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    result_path = run()
    print(f"\nDone. Research brief: {result_path}")
