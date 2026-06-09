export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Sticker pack generator ---

export type StylePreset =
  | "kawaii"
  | "pixel-art"
  | "flat-vector"
  | "watercolor"
  | "retro-cartoon"
  | "3d-clay";

export type Quality = "low" | "medium" | "high";

export type Platform = "telegram" | "whatsapp" | "discord" | "imessage";

export interface GeneratePackRequest {
  theme: string;
  style: StylePreset;
  pack_size: number;
  quality: Quality;
}

export interface Sticker {
  index: number;
  key: string;
  prompt: string;
  size_bytes: number;
  size_human: string;
}

export interface PackManifest {
  pack_id: string;
  theme: string;
  style: StylePreset;
  quality: Quality;
  created_at: string;
  sticker_count: number;
  stickers: Sticker[];
}

export interface PackSummary {
  pack_id: string;
  theme: string;
  style: StylePreset;
  created_at: string;
  sticker_count: number;
  cover_key: string | null;
}

export interface ExportResult {
  pack_id: string;
  platform: Platform;
  key: string;
  url: string;
  size_bytes: number;
  size_human: string;
  cached: boolean;
}

export interface PackStats {
  total_packs: number;
  total_stickers: number;
  stickers_this_week: number;
  storage_bytes: number;
  storage_human: string;
}

export interface DailyPackCount {
  date: string;
  packs: number;
}
