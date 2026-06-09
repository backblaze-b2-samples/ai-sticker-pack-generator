"""Tests for the pack library + export service.

The repo layer (B2 get_object_bytes / put_bytes / list_files / delete_prefix /
get_presigned_url) is fully mocked — no real B2 calls.
"""

import io
import zipfile
from datetime import UTC, datetime

import pytest
from PIL import Image

from app.service import packs as packs_service
from app.service.packs import (
    PackNotFoundError,
    delete_pack,
    export_pack,
    get_pack,
    get_pack_stats,
    list_packs,
)
from app.types import FileMetadata, PackManifest, Platform, Quality, Sticker, StylePreset


def _png_bytes() -> bytes:
    img = Image.new("RGBA", (1024, 1024), (255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _manifest(pack_id: str = "abc123", n: int = 2) -> PackManifest:
    return PackManifest(
        pack_id=pack_id,
        theme="happy cats",
        style=StylePreset.KAWAII,
        quality=Quality.LOW,
        created_at=datetime.now(UTC),
        sticker_count=n,
        stickers=[
            Sticker(
                index=i + 1,
                key=f"sticker-packs/{pack_id}/stickers/{i + 1:02d}.png",
                prompt="p",
                size_bytes=10,
                size_human="10.0 B",
            )
            for i in range(n)
        ],
    )


def _file(key: str) -> FileMetadata:
    return FileMetadata(
        key=key,
        filename=key.split("/")[-1],
        folder="sticker-packs/",
        size_bytes=100,
        size_human="100 B",
        content_type="application/octet-stream",
        uploaded_at=datetime.now(UTC),
        url=None,
    )


def test_list_packs_reads_manifests(monkeypatch):
    manifest = _manifest()
    monkeypatch.setattr(
        packs_service,
        "list_files",
        lambda prefix, max_keys: [_file("sticker-packs/abc123/pack.json")],
    )
    monkeypatch.setattr(
        packs_service, "get_object_bytes", lambda key: manifest.model_dump_json().encode()
    )

    summaries = list_packs()
    assert len(summaries) == 1
    assert summaries[0].theme == "happy cats"
    assert summaries[0].sticker_count == 2
    assert summaries[0].cover_key.endswith("/01.png")


def test_get_pack_missing_raises(monkeypatch):
    monkeypatch.setattr(packs_service, "get_object_bytes", lambda key: None)
    with pytest.raises(PackNotFoundError):
        get_pack("nope")


def test_export_pack_builds_zip(monkeypatch):
    manifest = _manifest()
    png = _png_bytes()

    def fake_get(key):
        if key.endswith("pack.json"):
            return manifest.model_dump_json().encode()
        if key.endswith("/exports/telegram.zip"):
            return None  # not cached
        return png

    put_calls: list[str] = []
    monkeypatch.setattr(packs_service, "get_object_bytes", fake_get)
    monkeypatch.setattr(packs_service, "put_bytes", lambda k, d, ct: put_calls.append(k))
    monkeypatch.setattr(
        packs_service, "get_presigned_url", lambda key, filename=None: "https://signed"
    )

    result = export_pack("abc123", Platform.TELEGRAM)
    assert result.cached is False
    assert result.url == "https://signed"
    assert result.key.endswith("/exports/telegram.zip")
    assert any(k.endswith("/exports/telegram.zip") for k in put_calls)


def test_export_pack_uses_cache(monkeypatch):
    manifest = _manifest()
    # Build a tiny valid zip to serve as the cached object.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("IMPORT.md", "x")
    cached = buf.getvalue()

    def fake_get(key):
        if key.endswith("pack.json"):
            return manifest.model_dump_json().encode()
        if key.endswith("/exports/discord.zip"):
            return cached
        return None

    monkeypatch.setattr(packs_service, "get_object_bytes", fake_get)
    monkeypatch.setattr(
        packs_service,
        "put_bytes",
        lambda k, d, ct: pytest.fail("should not rebuild a cached export"),
    )
    monkeypatch.setattr(
        packs_service, "get_presigned_url", lambda key, filename=None: "https://signed"
    )

    result = export_pack("abc123", Platform.DISCORD)
    assert result.cached is True


def test_delete_pack(monkeypatch):
    manifest = _manifest()
    monkeypatch.setattr(
        packs_service, "get_object_bytes", lambda key: manifest.model_dump_json().encode()
    )
    monkeypatch.setattr(packs_service, "delete_prefix", lambda prefix: 4)

    assert delete_pack("abc123") == 4


def test_pack_stats_counts_stickers(monkeypatch):
    files = [
        _file("sticker-packs/abc123/pack.json"),
        _file("sticker-packs/abc123/stickers/01.png"),
        _file("sticker-packs/abc123/stickers/02.png"),
        _file("sticker-packs/def456/pack.json"),
        _file("sticker-packs/def456/stickers/01.png"),
    ]
    monkeypatch.setattr(packs_service, "list_files", lambda prefix, max_keys: files)

    stats = get_pack_stats()
    assert stats.total_packs == 2
    assert stats.total_stickers == 3
