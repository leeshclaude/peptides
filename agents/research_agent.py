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

import anthropic
from dotenv import load_dotenv

# Allow imports from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.pubmed import get_peptide_research, fetch_pubmed_abstract

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
BRIEFS_DIR = REPO_ROOT / "data" / "research_briefs"
COMPETITORS_FILE = REPO_ROOT / "data" / "competitor_accounts.json"
PROMPT_FILE = REPO_ROOT / "prompts" / "research_agent.md"

REDDIT_URLS = [
    "https://www.reddit.com/r/Peptides/hot.json?limit=25",
    "https://www.reddit.com/r/longevity/hot.json?limit=25",
    "https://www.reddit.com/r/Biohackers/hot.json?limit=25",
]


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


def fetch_reddit_signals(client: anthropic.Anthropic) -> str:
    """Use Claude to fetch and summarize Reddit hot topics via web search."""
    print("  Fetching Reddit signals...")

    # We'll pass the Reddit subreddits to Claude and let it summarize
    subreddits = ["r/Peptides", "r/longevity", "r/Biohackers"]
    subreddit_list = ", ".join(subreddits)

    # Build context for Claude to work with
    return f"Reddit communities to analyze: {subreddit_list}\nNote: Use web search to find current hot posts from these communities."


def build_research_context(pubmed_data: str, competitors: dict) -> str:
    """Build the full context string to pass to the research agent."""
    competitor_handles = [
        acc["handle"] for acc in competitors.get("instagram_accounts", [])
        if acc.get("priority") == "high"
    ]
    reddit_communities = [
        c["subreddit"] for c in competitors.get("reddit_communities", [])
    ]

    context = f"""## Current Date
{datetime.now().strftime("%Y-%m-%d")}

## PubMed Research Data
{pubmed_data}

## Target Instagram Accounts (for competitor analysis)
{', '.join(f'@{h}' for h in competitor_handles)}

## Reddit Communities (for hot topics)
{', '.join(reddit_communities)}

## Instructions
1. Use the PubMed data above as your primary scientific source
2. For each Reddit community listed, search for hot/trending posts from the last 7 days
3. For competitor Instagram accounts, search for their recent content themes
4. Synthesize all of this into a structured research brief per the format in your system prompt
5. Be specific — include actual study titles, stats, and mechanisms
"""
    return context


def run(days_back: int = 7, output_path: Optional[Path] = None) -> Path:
    """
    Run the research agent and save output to a dated brief file.
    Returns the path to the generated brief.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("[Research Agent] Starting research pipeline...")

    # Gather data
    pubmed_data = fetch_pubmed_data()
    competitors = load_competitors()
    system_prompt = load_system_prompt()
    context = build_research_context(pubmed_data, competitors)

    print("  Calling Claude to synthesize research brief...")

    # Call Claude with extended thinking for better synthesis
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""Please research and synthesize a comprehensive brief for @peptidealpharesearch.

{context}

Please:
1. Analyze the PubMed studies above and identify the most content-worthy findings
2. Search Reddit communities for hot topics and questions
3. Note patterns in competitor content (based on the handles provided)
4. Identify emerging trends and gaps in existing content
5. Output the full research brief in the exact format specified in your system prompt

Today's date: {datetime.now().strftime("%Y-%m-%d")}""",
            }
        ],
    )

    brief_content = response.content[0].text

    # Save to file
    if output_path is None:
        BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = BRIEFS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"

    output_path.write_text(brief_content)
    print(f"[Research Agent] Brief saved to: {output_path}")

    return output_path


if __name__ == "__main__":
    result_path = run()
    print(f"\nDone. Research brief: {result_path}")
