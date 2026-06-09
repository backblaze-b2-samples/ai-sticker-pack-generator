from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# Prefix under which every sticker-pack artifact lives. B2 is the sole store;
# this prefix is the scoped namespace the /packs library reads from.
PACKS_PREFIX = "sticker-packs/"


class StylePreset(StrEnum):
    """A fixed visual style prepended to every per-sticker prompt so the whole
    pack reads as one coherent set. Subjects/poses vary; the style stays fixed.
    """

    KAWAII = "kawaii"
    PIXEL_ART = "pixel-art"
    FLAT_VECTOR = "flat-vector"
    WATERCOLOR = "watercolor"
    RETRO_CARTOON = "retro-cartoon"
    THREE_D_CLAY = "3d-clay"


class Quality(StrEnum):
    """gpt-image-1 quality tier. `low` is the cost-efficient default; quality
    and pack size are the cost levers surfaced in the UI.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Platform(StrEnum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    IMESSAGE = "imessage"


# Demo guardrails: keep a default run well under the $1 cost rule. Larger /
# higher-quality runs are opt-in with an in-UI cost note.
MAX_PACK_SIZE = 30
DEFAULT_PACK_SIZE = 12
SAFE_PACK_SIZE = 16  # at/below this, `low` quality stays well under $1


class GeneratePackRequest(BaseModel):
    theme: str = Field(min_length=2, max_length=200)
    style: StylePreset = StylePreset.KAWAII
    pack_size: int = Field(default=DEFAULT_PACK_SIZE, ge=1, le=MAX_PACK_SIZE)
    quality: Quality = Quality.LOW


class Sticker(BaseModel):
    index: int
    key: str
    prompt: str
    size_bytes: int
    size_human: str


class PackManifest(BaseModel):
    """Source-of-truth manifest persisted at sticker-packs/<id>/pack.json."""

    pack_id: str
    theme: str
    style: StylePreset
    quality: Quality
    created_at: datetime
    sticker_count: int
    stickers: list[Sticker]


class PackSummary(BaseModel):
    """Lightweight library-grid entry (cover sticker + theme + count)."""

    pack_id: str
    theme: str
    style: StylePreset
    created_at: datetime
    sticker_count: int
    cover_key: str | None = None


class PackStats(BaseModel):
    """Dashboard metrics scoped to the sticker-packs/ prefix."""

    total_packs: int
    total_stickers: int
    stickers_this_week: int
    storage_bytes: int
    storage_human: str


class DailyPackCount(BaseModel):
    date: str
    packs: int


class StickerUrlRequest(BaseModel):
    """Boundary model for the presigned sticker-URL endpoint."""

    key: str


class ExportRequest(BaseModel):
    platform: Platform


class ExportResult(BaseModel):
    pack_id: str
    platform: Platform
    key: str
    url: str
    size_bytes: int
    size_human: str
    cached: bool
