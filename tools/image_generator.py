"""
Image generation tool — Gemini Imagen → ImgBB hosting → public URL.

Usage:
    from tools.image_generator import generate_and_host
    url = generate_and_host("your detailed prompt here", name="slide-1")
"""

import base64
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
IMGBB_API_KEY  = os.environ.get("IMGBB_API_KEY")

IMAGEN_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "imagen-4.0-fast-generate-001:predict"
)


def generate_image_b64(prompt: str) -> str:
    """Call Imagen 4 Fast and return base64-encoded PNG."""
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY not set in .env")

    resp = requests.post(
        IMAGEN_URL,
        params={"key": GEMINI_API_KEY},
        json={
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "3:4",
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["predictions"][0]["bytesBase64Encoded"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Imagen response: {data}") from e


def upload_to_imgbb(b64_data: str, name: str) -> str:
    """Upload base64 image to ImgBB and return the direct image URL."""
    if not IMGBB_API_KEY:
        raise EnvironmentError("IMGBB_API_KEY not set in .env")

    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        params={"key": IMGBB_API_KEY},
        data={"image": b64_data, "name": name},
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise RuntimeError(f"ImgBB upload failed: {result}")
    return result["data"]["url"]


def generate_and_host(prompt: str, name: str = "slide") -> str:
    """
    Generate an image from a prompt and return a public URL.
    Full pipeline: Gemini Imagen → ImgBB → URL.
    """
    print(f"  Generating image: {name}...")
    b64 = generate_image_b64(prompt)
    print(f"  Uploading to ImgBB: {name}...")
    url = upload_to_imgbb(b64, name)
    print(f"  Done: {url}")
    return url


def generate_slide_images(slides: list[dict]) -> list[str]:
    """
    Generate images for a list of slides.

    Each slide dict must have:
        - slide_number (int)
        - image_prompt (str)

    Returns a list of public image URLs in slide order.
    """
    urls = []
    for slide in slides:
        num = slide["slide_number"]
        prompt = slide["image_prompt"]
        name = f"peptide-carousel-slide-{num}"
        url = generate_and_host(prompt, name=name)
        urls.append(url)
    return urls


if __name__ == "__main__":
    # Quick smoke test
    test_prompt = (
        "Single strand of human hair suspended against pure black background, "
        "lit by cold blue-white beam, partially translucent with glowing interior, "
        "microscopic peptide molecules hovering at cuticle surface, "
        "pharmaceutical editorial style, Nature journal cover aesthetic, "
        "no people, no packaging."
    )
    print("Testing image generation pipeline...")
    url = generate_and_host(test_prompt, name="test-slide-1")
    print(f"\nSuccess! Image URL: {url}")
