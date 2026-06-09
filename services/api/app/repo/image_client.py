"""OpenAI image-generation adapter (repo layer).

Wraps the OpenAI `gpt-image-1` model. The SDK is imported *lazily inside the
function* (house style) so that:
  - boto3-style "external SDK only in repo/" containment is matched by the
    OpenAI SDK too,
  - module import never fails when the optional dependency or API key is
    absent (keeps test collection and `from main import app` hermetic).

Stickers are generated with a transparent background natively
(`background="transparent"`), so no post-processing / background-removal
sidecar is needed.
"""

import base64
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# gpt-image-1 generation parameters. Size + quality are the cost levers;
# quality is passed through per request. 1024² transparent PNG is the
# canonical sticker source asset (exports downscale from here).
_IMAGE_SIZE = "1024x1024"
_OUTPUT_FORMAT = "png"


class ImageGenerationError(Exception):
    """Raised when image generation fails or is misconfigured."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def generate_sticker_image(prompt: str, quality: str = "low") -> bytes:
    """Generate a single transparent-background sticker PNG from a prompt.

    Returns the raw PNG bytes. Raises ImageGenerationError on missing config
    or any SDK/API failure. The OpenAI SDK is imported lazily here on purpose.
    """
    if not settings.openai_api_key:
        raise ImageGenerationError(
            "OPENAI_API_KEY is not set. Add it to .env to generate stickers."
        )

    # Lazy import — keeps the SDK out of module scope (house style) and lets
    # the app import cleanly when the dependency/key is absent.
    try:
        from openai import OpenAI
    except ImportError as e:  # pragma: no cover - dependency guard
        raise ImageGenerationError(
            "The 'openai' package is not installed. Run: pip install -r requirements.txt"
        ) from e

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=_IMAGE_SIZE,
            background="transparent",
            output_format=_OUTPUT_FORMAT,
            quality=quality,
            n=1,
        )
    except Exception as e:  # SDK raises a family of errors; normalize them.
        logger.warning("OpenAI image generation failed: %s", e)
        raise ImageGenerationError(f"Image generation failed: {e}") from e

    data = response.data
    if not data or not getattr(data[0], "b64_json", None):
        raise ImageGenerationError("Image generation returned no image data.")
    return base64.b64decode(data[0].b64_json)
