"""
Canva template ID management and brand configuration for @peptidealpharesearch.
Used by the content creation agent when calling Canva MCP tools.
"""
from typing import Optional, List

# ─── Template IDs ─────────────────────────────────────────────────────────────
# Primary carousel template — 8-slide format used for all content types.
# Skill: canva-peptide-carousel.skill
# ──────────────────────────────────────────────────────────────────────────────

CANVA_TEMPLATES = {
    "carousel": "DAHEVyvHuDg",     # 8-slide: hook + supporting hook + 5 content + CTA
}

# Convenience alias — the default template for all carousel content
DEFAULT_TEMPLATE_ID = CANVA_TEMPLATES["carousel"]

# ─── Brand Colors ──────────────────────────────────────────────────────────────

BRAND_COLORS = {
    "primary": "#0A1628",          # Deep navy
    "accent_teal": "#00D4FF",      # Electric teal
    "accent_gold": "#FFB347",      # Warm gold
    "text_light": "#FFFFFF",       # White
    "text_dark": "#1A1A2E",        # Near-black
}

# ─── Slide Structure (matches canva-peptide-carousel.skill) ────────────────────
#
# Slide 1 — Hook only (ALL CAPS, 10–15 words, no body text)
# Slide 2 — Supporting hook (header + body, 2–3 sentences)
# Slides 3–6 — Content build (header hook + body, one idea per slide)
# Slide 7 — Payoff/revelation (header + body)
# Slide 8 — CTA: "Follow @peptidealpharesearch" + engagement question
# ──────────────────────────────────────────────────────────────────────────────

TEMPLATE_STRUCTURES = {
    "carousel": {
        "slide_count": 8,
        "slides": [
            {
                "index": 0,
                "role": "hook",
                "description": "ALL CAPS scroll-stopper, 10–15 words, no body text",
                "has_header": True,
                "has_body": False,
                "header_style": "ALL CAPS",
                "header_min_words": 10,
                "header_max_words": 15,
            },
            {
                "index": 1,
                "role": "supporting_hook",
                "description": "Second hook that extends/reframes Slide 1, sets up the problem",
                "has_header": True,
                "has_body": True,
                "body_max_sentences": 3,
            },
            {
                "index": 2,
                "role": "problem",
                "description": "Establish the problem or gap in mainstream thinking",
                "has_header": True,
                "has_body": True,
                "body_max_sentences": 4,
            },
            {
                "index": 3,
                "role": "mechanism",
                "description": "Introduce the mechanism or research — get specific",
                "has_header": True,
                "has_body": True,
                "body_max_sentences": 4,
            },
            {
                "index": 4,
                "role": "insight",
                "description": "Surprising detail, stat, or counterintuitive insight",
                "has_header": True,
                "has_body": True,
                "body_max_sentences": 4,
            },
            {
                "index": 5,
                "role": "possibility",
                "description": "Pivot toward what's different — hint at change",
                "has_header": True,
                "has_body": True,
                "body_max_sentences": 4,
            },
            {
                "index": 6,
                "role": "payoff",
                "description": "The aha moment — what the reader now knows/believes",
                "has_header": True,
                "has_body": True,
                "body_max_sentences": 3,
            },
            {
                "index": 7,
                "role": "cta",
                "description": "Header: 'Follow @peptidealpharesearch'. Body: one engagement question only.",
                "has_header": True,
                "has_body": True,
                "header_fixed": "Follow @peptidealpharesearch",
                "body_max_sentences": 1,
            },
        ],
    },
}

# ─── Helper Functions ──────────────────────────────────────────────────────────

def get_template_id(template_type: str = "carousel") -> Optional[str]:
    """Return the Canva template ID for the given type."""
    return CANVA_TEMPLATES.get(template_type)


def get_template_structure(template_type: str = "carousel") -> Optional[dict]:
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

    for slide_def, slide_copy in zip(structure["slides"], slides):
        i = slide_def["index"] + 1
        header = slide_copy.get("header", slide_copy.get("headline", ""))

        # Check hook word count
        if slide_def["role"] == "hook":
            word_count = len(header.split())
            if word_count < slide_def.get("header_min_words", 0):
                warnings.append(f"Slide {i} (hook): {word_count} words — minimum is {slide_def['header_min_words']}")
            if word_count > slide_def.get("header_max_words", 999):
                warnings.append(f"Slide {i} (hook): {word_count} words — maximum is {slide_def['header_max_words']}")
            if header != header.upper():
                warnings.append(f"Slide {i} (hook): header must be ALL CAPS")

        # Check body exists when required
        if slide_def["has_body"] and not slide_copy.get("body"):
            warnings.append(f"Slide {i} ({slide_def['role']}): missing body text")

        # Check CTA header
        if slide_def["role"] == "cta" and "fixed" in slide_def.get("header_fixed", ""):
            if "peptidealpharesearch" not in header.lower():
                warnings.append(f"Slide {i} (cta): header should include @peptidealpharesearch")

    return warnings


def list_configured_templates() -> List[str]:
    """Return list of template types that have IDs configured."""
    return [k for k, v in CANVA_TEMPLATES.items() if v is not None]


def all_templates_configured() -> bool:
    """Return True if all templates have IDs set."""
    return all(v is not None for v in CANVA_TEMPLATES.values())
