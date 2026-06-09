"""Tests for sticker-pack generation orchestration.

The repo layer (OpenAI image_client + B2 put_bytes) is fully mocked — no real
OpenAI or B2 calls are made.
"""

import pytest

from app.repo.image_client import ImageGenerationError
from app.service import stickers as stickers_service
from app.service.stickers import StickerGenerationError, generate_pack
from app.types import GeneratePackRequest, Quality, StylePreset

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes"


@pytest.fixture
def stored(monkeypatch):
    """Capture every put_bytes call and stub image generation to succeed."""
    calls: list[tuple[str, bytes, str]] = []
    monkeypatch.setattr(
        stickers_service, "put_bytes", lambda k, d, ct: calls.append((k, d, ct))
    )
    monkeypatch.setattr(
        stickers_service, "generate_sticker_image", lambda prompt, quality: PNG
    )
    return calls


def test_generate_pack_stores_stickers_and_manifest(stored):
    req = GeneratePackRequest(
        theme="happy cats", style=StylePreset.KAWAII, pack_size=3, quality=Quality.LOW
    )
    manifest = generate_pack(req)

    assert manifest.sticker_count == 3
    assert manifest.theme == "happy cats"
    assert len(manifest.stickers) == 3
    # 3 stickers + 1 manifest object stored
    keys = [k for k, _, _ in stored]
    assert sum(1 for k in keys if k.endswith(".png")) == 3
    assert any(k.endswith("/pack.json") for k in keys)
    # All artifacts live under the scoped prefix
    assert all(k.startswith("sticker-packs/") for k in keys)


def test_generate_pack_prompts_share_style_vary_pose(monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr(stickers_service, "put_bytes", lambda k, d, ct: None)

    def capture(prompt, quality):
        captured.append(prompt)
        return PNG

    monkeypatch.setattr(stickers_service, "generate_sticker_image", capture)

    generate_pack(
        GeneratePackRequest(theme="robots", style=StylePreset.PIXEL_ART, pack_size=2)
    )
    assert len(captured) == 2
    # Same style descriptor in every prompt; different pose text.
    assert all("pixel-art" in p for p in captured)
    assert captured[0] != captured[1]


def test_generate_pack_aborts_when_first_sticker_fails(monkeypatch):
    monkeypatch.setattr(stickers_service, "put_bytes", lambda k, d, ct: None)

    def boom(prompt, quality):
        raise ImageGenerationError("OPENAI_API_KEY is not set.")

    monkeypatch.setattr(stickers_service, "generate_sticker_image", boom)

    with pytest.raises(StickerGenerationError):
        generate_pack(GeneratePackRequest(theme="robots", pack_size=2))


def test_generate_pack_tolerates_partial_failure(monkeypatch):
    stored: list[str] = []
    monkeypatch.setattr(
        stickers_service, "put_bytes", lambda k, d, ct: stored.append(k)
    )

    calls = {"n": 0}

    def flaky(prompt, quality):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ImageGenerationError("transient")
        return PNG

    monkeypatch.setattr(stickers_service, "generate_sticker_image", flaky)

    manifest = generate_pack(GeneratePackRequest(theme="robots", pack_size=3))
    # 2 of 3 succeeded; manifest reflects only the stored stickers
    assert manifest.sticker_count == 2
