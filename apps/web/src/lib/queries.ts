"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  deleteFile,
  deletePack,
  exportPack,
  generatePack,
  getFiles,
  getFileStats,
  getHealth,
  getPack,
  getPackActivity,
  getPacks,
  getPackStats,
  getPreviewUrl,
  getStickerUrl,
  getUploadActivity,
} from "@/lib/api-client";
import type { HealthResponse } from "@/lib/api-client";
import type {
  FileMetadata,
  GeneratePackRequest,
  PackManifest,
  PackSummary,
  Platform,
} from "@ai-sticker-pack-generator/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  health: () => [...qk.all, "health"] as const,
  healthBanner: () => [...qk.all, "health", "banner"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  packs: () => [...qk.all, "packs"] as const,
  pack: (id: string) => [...qk.all, "packs", id] as const,
  packStats: () => [...qk.all, "packs", "stats"] as const,
  packActivity: (days: number) =>
    [...qk.all, "packs", "stats", "activity", days] as const,
  stickerUrl: (packId: string, key: string) =>
    [...qk.all, "sticker-url", packId, key] as const,
};

async function getHealthBannerStatus(): Promise<HealthResponse | null> {
  try {
    return await getHealth();
  } catch {
    return null;
  }
}

export function useHealth() {
  return useQuery<HealthResponse, ApiError>({
    queryKey: qk.health(),
    queryFn: getHealth,
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: false,
  });
}

export function useHealthBannerStatus() {
  return useQuery({
    queryKey: qk.healthBanner(),
    queryFn: getHealthBannerStatus,
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: false,
  });
}

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Sticker packs ---

export function usePacks() {
  return useQuery<PackSummary[], ApiError>({
    queryKey: qk.packs(),
    queryFn: getPacks,
  });
}

export function usePack(packId: string) {
  return useQuery<PackManifest, ApiError>({
    queryKey: qk.pack(packId),
    queryFn: () => getPack(packId),
    enabled: !!packId,
  });
}

export function usePackStats() {
  return useQuery({
    queryKey: qk.packStats(),
    queryFn: getPackStats,
  });
}

export function usePackActivity(days = 7) {
  return useQuery({
    queryKey: qk.packActivity(days),
    queryFn: () => getPackActivity(days),
  });
}

export function useGeneratePack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (request: GeneratePackRequest) => generatePack(request),
    onSuccess: () => {
      // New pack changes the library, stats, and activity.
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

export function useExportPack(packId: string) {
  return useMutation({
    mutationFn: (platform: Platform) => exportPack(packId, platform),
  });
}

export function useDeletePack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (packId: string) => deletePack(packId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// Presigned URL for a single sticker. Cached per (pack, key); the presigned
// URL itself has an expiry so we keep it stale-while-revalidate for 5 min.
export function useStickerUrl(packId: string, key: string | undefined) {
  return useQuery({
    queryKey: qk.stickerUrl(packId, key ?? ""),
    queryFn: () => getStickerUrl(packId, key as string),
    enabled: !!packId && !!key,
    staleTime: 5 * 60_000,
  });
}
