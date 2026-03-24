"""
Canva template ID management and brand configuration for @peptidealpharesearch.
Used by the content creation agent when calling Canva MCP tools.
"""
from typing import Optional, List
# ─── Template IDs ─────────────────────────────────────────────────────────────
# Replace these with your actual Canva template design IDs.
# To find an ID: open design in Canva → URL contains /design/DAF_XXXXXXXX/
# ──────────────────────────────────────────────────────────────────────────────

CANVA_TEMPLATES = {
    "research_breakdown": None,    # 7-slide: hook + 5 content + CTA
    "protocol_deep_dive": None,    # 8-slide: hook + 6 content + CTA
    "myth_busting": None,          # 6-slide: myth + reality x2 + evidence + CTA
    "mechanism_explainer": None,   # 7-slide: hook + pathway + steps + CTA
    "single_stat": None,           # 1-slide infographic
}

# ─── Brand Colors ──────────────────────────────────────────────────────────────

BRAND_COLORS = {
    "primary": "#0A1628",          # Deep navy
    "accent_teal": "#00D4FF",      # Electric teal
    "accent_gold": "#FFB347",      # Warm gold
    "text_light": "#FFFFFF",       # White
    "text_dark": "#1A1A2E",        # Near-black
}

# ─── Slide Structure Definitions ───────────────────────────────────────────────

TEMPLATE_STRUCTURES = {
    "research_breakdown": {
        "slide_count": 7,
        "slides": [
            {"index": 0, "role": "hook",       "max_words": 8,  "has_subtext": True},
            {"index": 1, "role": "context",    "max_words": 40, "has_subtext": False},
            {"index": 2, "role": "finding_1",  "max_words": 40, "has_subtext": False},
            {"index": 3, "role": "finding_2",  "max_words": 40, "has_subtext": False},
            {"index": 4, "role": "mechanism",  "max_words": 40, "has_subtext": False},
            {"index": 5, "role": "takeaway",   "max_words": 40, "has_subtext": False},
            {"index": 6, "role": "cta",        "max_words": 15, "has_subtext": True},
        ],
    },
    "protocol_deep_dive": {
        "slide_count": 8,
        "slides": [
            {"index": 0, "role": "hook",       "max_words": 8,  "has_subtext": True},
            {"index": 1, "role": "overview",   "max_words": 40, "has_subtext": False},
            {"index": 2, "role": "dosing",     "max_words": 40, "has_subtext": False},
            {"index": 3, "role": "timing",     "max_words": 40, "has_subtext": False},
            {"index": 4, "role": "synergies",  "max_words": 40, "has_subtext": False},
            {"index": 5, "role": "evidence",   "max_words": 40, "has_subtext": False},
            {"index": 6, "role": "cautions",   "max_words": 40, "has_subtext": False},
            {"index": 7, "role": "cta",        "max_words": 15, "has_subtext": True},
        ],
    },
    "myth_busting": {
        "slide_count": 6,
        "slides": [
            {"index": 0, "role": "hook",       "max_words": 8,  "has_subtext": True},
            {"index": 1, "role": "myth_1",     "max_words": 40, "has_subtext": False},
            {"index": 2, "role": "reality_1",  "max_words": 40, "has_subtext": False},
            {"index": 3, "role": "myth_2",     "max_words": 40, "has_subtext": False},
            {"index": 4, "role": "evidence",   "max_words": 40, "has_subtext": False},
            {"index": 5, "role": "cta",        "max_words": 15, "has_subtext": True},
        ],
    },
    "mechanism_explainer": {
        "slide_count": 7,
        "slides": [
            {"index": 0, "role": "hook",       "max_words": 8,  "has_subtext": True},
            {"index": 1, "role": "what_is_it", "max_words": 40, "has_subtext": False},
            {"index": 2, "role": "step_1",     "max_words": 40, "has_subtext": False},
            {"index": 3, "role": "step_2",     "max_words": 40, "has_subtext": False},
            {"index": 4, "role": "step_3",     "max_words": 40, "has_subtext": False},
            {"index": 5, "role": "outcome",    "max_words": 40, "has_subtext": False},
            {"index": 6, "role": "cta",        "max_words": 15, "has_subtext": True},
        ],
    },
}

# ─── Helper Functions ──────────────────────────────────────────────────────────

def get_template_id(template_type: str) -> Optional[str]:
    """Return the Canva template ID for the given type, or None if not configured."""
    return CANVA_TEMPLATES.get(template_type)


def get_template_structure(template_type: str) -> Optional[dict]:
    """Return the slide structure definition for a template type."""
    return TEMPLATE_STRUCTURES.get(template_type)


def validate_slide_copy(template_type: str, slides: List[dict]) -> List[str]:
    """
    Validate slide copy against template constraints.
    Returns list of warning strings (empty = all good).
    """
    structure = get_template_structure(template_type)
    if not structure:
        return [f"Unknown template type: {template_type}"]

    warnings = []
    expected_count = structure["slide_count"]
    if len(slides) != expected_count:
        warnings.append(
            f"Expected {expected_count} slides for {template_type}, got {len(slides)}"
        )

    for i, (slide_def, slide_copy) in enumerate(
        zip(structure["slides"], slides), start=1
    ):
        headline = slide_copy.get("headline", "")
        word_count = len(headline.split())
        max_words = slide_def["max_words"]
        if word_count > max_words:
            warnings.append(
                f"Slide {i} ({slide_def['role']}): {word_count} words exceeds max {max_words}"
            )

    return warnings


def list_configured_templates() -> List[str]:
    """Return list of template types that have IDs configured."""
    return [k for k, v in CANVA_TEMPLATES.items() if v is not None]


def all_templates_configured() -> bool:
    """Return True if all templates have IDs set."""
    return all(v is not None for v in CANVA_TEMPLATES.values())
