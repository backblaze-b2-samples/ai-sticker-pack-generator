"""Sticker-pack generation orchestration (service layer).

Flow: build per-sticker prompts (shared style descriptor + varied poses) →
call the image_client adapter → store each sticker PNG + a pack.json manifest
to B2 under sticker-packs/<pack-id>/. B2 is the sole store; the manifest is
the source of truth.
"""

import json
import logging
import uuid
from datetime import UTC, datetime

from app.repo import generate_sticker_image, put_bytes
from app.repo.image_client import ImageGenerationError
from app.types import (
    PACKS_PREFIX,
    GeneratePackRequest,
    PackManifest,
    Sticker,
    StylePreset,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

# A detailed, fixed style descriptor per preset. Prepended to every
# per-sticker prompt so subjects/poses vary while the visual style stays
# locked across the whole pack — consistent style with no second model.
_STYLE_DESCRIPTORS: dict[StylePreset, str] = {
    StylePreset.KAWAII: (
        "kawaii chibi sticker, soft rounded shapes, pastel palette, thick "
        "clean outline, big expressive eyes, simple cute shading"
    ),
    StylePreset.PIXEL_ART: (
        "16-bit pixel-art sticker, crisp pixels, limited retro palette, "
        "1px dark outline, dithered shading"
    ),
    StylePreset.FLAT_VECTOR: (
        "flat vector sticker, bold geometric shapes, minimal gradients, "
        "clean even outline, modern illustration style"
    ),
    StylePreset.WATERCOLOR: (
        "watercolor sticker, soft painted edges, gentle color bleeds, "
        "hand-painted texture, light pencil sketch lines"
    ),
    StylePreset.RETRO_CARTOON: (
        "1930s rubber-hose retro cartoon sticker, bold black outlines, "
        "limited muted palette, vintage print texture"
    ),
    StylePreset.THREE_D_CLAY: (
        "3D claymation sticker, soft matte clay material, gentle studio "
        "lighting, rounded handmade forms, subtle ambient occlusion"
    ),
}

# Built-in pose / expression variations (NOT LLM-expanded — deliberately a
# fixed list to keep the build lightweight and deterministic). Cycled over
# the requested pack size so even large packs stay coherent.
_POSE_VARIATIONS: list[str] = [
    "happy and waving hello",
    "laughing out loud",
    "giving a thumbs up",
    "blowing a kiss with a heart",
    "crying with big tears",
    "angry with steam",
    "sleeping peacefully",
    "surprised with wide eyes",
    "thinking with a finger on chin",
    "celebrating with confetti",
    "winking and smiling",
    "shrugging confused",
    "in love with heart eyes",
    "cheering with both arms up",
    "eating happily",
    "sad and pouting",
    "cool wearing sunglasses",
    "shy and blushing",
    "dancing joyfully",
    "giving a high five",
    "thumbs down disapproving",
    "yawning sleepy",
    "excited jumping",
    "facepalming embarrassed",
    "holding a coffee cup",
    "reading a book",
    "taking a selfie",
    "throwing confetti party",
    "meditating calmly",
    "running in a hurry",
]


class StickerGenerationError(Exception):
    """Raised when a pack cannot be generated."""

    def __init__(self, detail: str, status_code: int = 502):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _build_prompt(theme: str, style: StylePreset, pose: str) -> str:
    """Combine the fixed style descriptor, the theme, and a pose variation."""
    descriptor = _STYLE_DESCRIPTORS[style]
    return (
        f"A die-cut sticker of {theme}, {pose}. "
        f"Style: {descriptor}. "
        "Single centered subject, transparent background, no text, "
        "no drop shadow, no border frame."
    )


def _manifest_key(pack_id: str) -> str:
    return f"{PACKS_PREFIX}{pack_id}/pack.json"


def _sticker_key(pack_id: str, index: int) -> str:
    return f"{PACKS_PREFIX}{pack_id}/stickers/{index:02d}.png"


def generate_pack(request: GeneratePackRequest) -> PackManifest:
    """Generate a full sticker pack and persist it to B2.

    Generates `pack_size` stickers; each is stored as a transparent PNG. The
    pack.json manifest is written last so a pack only appears in the library
    once it's complete. Raises StickerGenerationError if no sticker could be
    generated.
    """
    pack_id = uuid.uuid4().hex[:12]
    created_at = datetime.now(UTC)
    stickers: list[Sticker] = []

    for i in range(request.pack_size):
        pose = _POSE_VARIATIONS[i % len(_POSE_VARIATIONS)]
        prompt = _build_prompt(request.theme, request.style, pose)
        try:
            png = generate_sticker_image(prompt, quality=request.quality.value)
        except ImageGenerationError as e:
            # First sticker failing usually means misconfig / hard error —
            # abort rather than store an empty pack. Later failures leave a
            # partial pack (logged); see docs/RELIABILITY.md.
            if not stickers:
                raise StickerGenerationError(e.detail) from e
            logger.warning(
                "Sticker %d/%d failed for pack %s: %s",
                i + 1,
                request.pack_size,
                pack_id,
                e.detail,
            )
            continue

        key = _sticker_key(pack_id, i + 1)
        put_bytes(key, png, "image/png")
        stickers.append(
            Sticker(
                index=i + 1,
                key=key,
                prompt=prompt,
                size_bytes=len(png),
                size_human=humanize_bytes(len(png)),
            )
        )

    if not stickers:
        raise StickerGenerationError("No stickers could be generated for this pack.")

    manifest = PackManifest(
        pack_id=pack_id,
        theme=request.theme,
        style=request.style,
        quality=request.quality,
        created_at=created_at,
        sticker_count=len(stickers),
        stickers=stickers,
    )
    put_bytes(
        _manifest_key(pack_id),
        manifest.model_dump_json().encode("utf-8"),
        "application/json",
    )
    logger.info(
        "Pack generated: pack_id=%s theme=%s stickers=%d",
        pack_id,
        request.theme,
        len(stickers),
    )
    return manifest


def parse_manifest(raw: bytes) -> PackManifest:
    """Deserialize a pack.json manifest read back from B2."""
    return PackManifest.model_validate(json.loads(raw))
