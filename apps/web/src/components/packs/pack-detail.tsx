"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Download, Trash2, Package } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { StickerImage } from "@/components/packs/sticker-image";
import { ApiError, getStickerUrl } from "@/lib/api-client";
import { useDeletePack, useExportPack, usePack } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import { PLATFORM_LABELS, PLATFORMS, styleLabel } from "@/lib/sticker-style";
import type { Platform } from "@ai-sticker-pack-generator/shared";

export function PackDetail({ packId }: { packId: string }) {
  const router = useRouter();
  const { data: pack, isLoading, error, refetch } = usePack(packId);
  const exportMut = useExportPack(packId);
  const deleteMut = useDeletePack();
  const [exporting, setExporting] = useState<Platform | null>(null);

  const handleStickerDownload = async (key: string) => {
    try {
      const { url } = await getStickerUrl(packId, key);
      window.open(url, "_blank");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to download sticker");
    }
  };

  const handleExport = (platform: Platform) => {
    setExporting(platform);
    exportMut.mutate(platform, {
      onSuccess: (result) => {
        toast.success(
          `${PLATFORM_LABELS[platform]} export ready (${result.size_human})`,
        );
        window.open(result.url, "_blank");
      },
      onError: (err) => {
        toast.error(err instanceof ApiError ? err.message : "Export failed");
      },
      onSettled: () => setExporting(null),
    });
  };

  const handleDelete = () => {
    deleteMut.mutate(packId, {
      onSuccess: () => {
        toast.success("Pack deleted");
        router.push("/packs");
      },
      onError: (err) => {
        toast.error(err instanceof ApiError ? err.message : "Failed to delete pack");
      },
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full rounded-md" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !pack) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 space-y-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/packs")}
          className="h-7 -ml-2 text-muted-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to packs
        </Button>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="page-title">{pack.theme}</h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="secondary">{styleLabel(pack.style)}</Badge>
              <span>{pack.sticker_count} stickers</span>
              <span>·</span>
              <span>{formatDate(pack.created_at)}</span>
            </div>
          </div>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 text-destructive">
                <Trash2 className="h-3.5 w-3.5" />
                Delete pack
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this pack?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently removes all {pack.sticker_count} stickers, the
                  manifest, and any cached exports from B2. This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  disabled={deleteMut.isPending}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {deleteMut.isPending ? "Deleting…" : "Delete"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Export to a platform</CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          <p className="text-sm text-muted-foreground mb-4">
            Builds a ready-to-import bundle (resized + an IMPORT.md how-to),
            stores it in B2, and downloads it via a presigned URL.
          </p>
          <div className="flex flex-wrap gap-2">
            {PLATFORMS.map((platform) => (
              <Button
                key={platform}
                variant="outline"
                size="sm"
                onClick={() => handleExport(platform)}
                disabled={exporting !== null}
              >
                <Package className="h-3.5 w-3.5" />
                {exporting === platform
                  ? "Building…"
                  : PLATFORM_LABELS[platform]}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
        {pack.stickers.map((sticker) => (
          <div key={sticker.key} className="group relative">
            <StickerImage
              packId={packId}
              stickerKey={sticker.key}
              alt={`${pack.theme} sticker ${sticker.index}`}
              className="aspect-square w-full border border-border"
            />
            <Button
              variant="secondary"
              size="icon"
              onClick={() => handleStickerDownload(sticker.key)}
              className="absolute top-2 right-2 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label={`Download sticker ${sticker.index}`}
            >
              <Download className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
