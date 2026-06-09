import type { Platform, Quality, StylePreset } from "@ai-sticker-pack-generator/shared";

// Human-readable labels for the fixed style presets exposed by the backend.
// Keep the keys in sync with services/api/app/types/stickers.py::StylePreset.
const STYLE_LABELS: Record<StylePreset, string> = {
  kawaii: "Kawaii",
  "pixel-art": "Pixel Art",
  "flat-vector": "Flat Vector",
  watercolor: "Watercolor",
  "retro-cartoon": "Retro Cartoon",
  "3d-clay": "3D Clay",
};

export const STYLE_OPTIONS: { value: StylePreset; label: string }[] = (
  Object.keys(STYLE_LABELS) as StylePreset[]
).map((value) => ({ value, label: STYLE_LABELS[value] }));

export function styleLabel(style: StylePreset): string {
  return STYLE_LABELS[style] ?? style;
}

export const QUALITY_OPTIONS: { value: Quality; label: string }[] = [
  { value: "low", label: "Low — cheapest (~$0.011/sticker)" },
  { value: "medium", label: "Medium — sharper, costs more" },
  { value: "high", label: "High — best, costs most" },
];

export const PLATFORM_LABELS: Record<Platform, string> = {
  telegram: "Telegram",
  whatsapp: "WhatsApp",
  discord: "Discord",
  imessage: "iMessage",
};

export const PLATFORMS: Platform[] = ["telegram", "whatsapp", "discord", "imessage"];

// Demo guardrail mirrored from the backend: at/below this many stickers the
// default `low` quality stays well under the $1 cost rule.
export const SAFE_PACK_SIZE = 16;
export const DEFAULT_PACK_SIZE = 12;
export const MAX_PACK_SIZE = 30;
