"""
PubMed & bioRxiv search wrapper using free E-utilities API (no key required).
"""

import requests
from datetime import datetime, timedelta
from typing import List, Optional


PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
BIORXIV_BASE = "https://api.biorxiv.org/details"

PEPTIDE_QUERY = (
    "(peptide[Title/Abstract] OR BPC157[Title/Abstract] OR TB-500[Title/Abstract] "
    "OR thymosin[Title/Abstract] OR GHK-Cu[Title/Abstract] OR Epithalon[Title/Abstract] "
    "OR Selank[Title/Abstract] OR Semax[Title/Abstract] OR CJC-1295[Title/Abstract] "
    "OR ipamorelin[Title/Abstract] OR GHRP[Title/Abstract]) "
    "AND (longevity[Title/Abstract] OR anti-aging[Title/Abstract] OR "
    "biohacking[Title/Abstract] OR performance[Title/Abstract] OR "
    "recovery[Title/Abstract] OR neuroprotection[Title/Abstract] OR "
    "tissue repair[Title/Abstract])"
)

LONGEVITY_QUERY = (
    "(longevity OR lifespan OR healthspan OR senescence OR mTOR OR AMPK OR sirtuins "
    "OR autophagy OR telomere OR NAD+ OR NMN OR rapamycin) "
    "AND (human[Title/Abstract] OR clinical[Title/Abstract] OR trial[Title/Abstract])"
)


def search_pubmed(
    query: str,
    days_back: int = 7,
    max_results: int = 20,
) -> List[dict]:
    """Search PubMed for recent articles matching query."""
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    date_to = datetime.now().strftime("%Y/%m/%d")

    # Step 1: search for IDs
    search_url = f"{PUBMED_BASE}/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "datetype": "pdat",
        "mindate": date_from,
        "maxdate": date_to,
        "retmode": "json",
        "usehistory": "y",
    }

    try:
        resp = requests.get(search_url, params=search_params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[PubMed] Search error: {e}")
        return []

    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    # Step 2: fetch summaries
    summary_url = f"{PUBMED_BASE}/esummary.fcgi"
    summary_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "json",
    }

    try:
        resp = requests.get(summary_url, params=summary_params, timeout=15)
        resp.raise_for_status()
        summary_data = resp.json()
    except requests.RequestException as e:
        print(f"[PubMed] Summary fetch error: {e}")
        return []

    articles = []
    result = summary_data.get("result", {})
    for pmid in ids:
        if pmid not in result:
            continue
        item = result[pmid]
        articles.append({
            "pmid": pmid,
            "title": item.get("title", ""),
            "authors": [a.get("name", "") for a in item.get("authors", [])[:3]],
            "journal": item.get("source", ""),
            "pub_date": item.get("pubdate", ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "abstract_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })

    return articles


def fetch_pubmed_abstract(pmid: str) -> str:
    """Fetch the abstract text for a specific PubMed article."""
    url = f"{PUBMED_BASE}/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": pmid,
        "rettype": "abstract",
        "retmode": "text",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.text.strip()
    except requests.RequestException as e:
        return f"Error fetching abstract: {e}"


def search_biorxiv(query: str, days_back: int = 7, max_results: int = 10) -> List[dict]:
    """Search bioRxiv for recent preprints."""
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")

    url = f"{BIORXIV_BASE}/biorxiv/{date_from}/{date_to}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[bioRxiv] Error: {e}")
        return []

    collection = data.get("collection", [])
    query_lower = query.lower()
    query_terms = query_lower.replace("(", "").replace(")", "").split()[:5]

    results = []
    for item in collection:
        title = item.get("title", "").lower()
        abstract = item.get("abstract", "").lower()
        if any(term in title or term in abstract for term in query_terms):
            results.append({
                "doi": item.get("doi", ""),
                "title": item.get("title", ""),
                "authors": item.get("authors", ""),
                "date": item.get("date", ""),
                "category": item.get("category", ""),
                "url": f"https://www.biorxiv.org/content/{item.get('doi', '')}",
                "is_preprint": True,
            })
            if len(results) >= max_results:
                break

    return results


def get_peptide_research(days_back: int = 7) -> dict:
    """Convenience function: get all recent peptide + longevity research."""
    return {
        "peptide_studies": search_pubmed(PEPTIDE_QUERY, days_back=days_back),
        "longevity_studies": search_pubmed(LONGEVITY_QUERY, days_back=days_back),
        "preprints": search_biorxiv("peptide longevity biohacking", days_back=days_back),
        "retrieved_at": datetime.now().isoformat(),
        "days_back": days_back,
    }


if __name__ == "__main__":
    print("Testing PubMed search...")
    results = search_pubmed("BPC157 tissue repair", days_back=90, max_results=3)
    for r in results:
        print(f"  - {r['title'][:80]}... ({r['pub_date']})")
    print(f"Found {len(results)} results")
