"use client";

/* eslint-disable @next/next/no-img-element */
import { ImageIcon } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useStickerUrl } from "@/lib/queries";

interface StickerImageProps {
  packId: string;
  stickerKey: string | undefined;
  alt: string;
  className?: string;
}

// Renders a single sticker by resolving its presigned URL. A subtle
// checkerboard backdrop reads through the transparent (die-cut) PNG so the
// transparency is obvious. Uses a plain <img> (not next/image) because the
// presigned URL is short-lived and per-request — next/image's optimizer
// would cache stale signed URLs.
export function StickerImage({ packId, stickerKey, alt, className }: StickerImageProps) {
  const { data, isLoading, error } = useStickerUrl(packId, stickerKey);

  return (
    <div
      className={`relative flex items-center justify-center overflow-hidden rounded-md sticker-checker ${className ?? ""}`}
    >
      {isLoading ? (
        <Skeleton className="absolute inset-0 h-full w-full" />
      ) : error || !data?.url ? (
        <ImageIcon className="h-6 w-6 text-muted-foreground" />
      ) : (
        <img
          src={data.url}
          alt={alt}
          className="h-full w-full object-contain p-2"
          loading="lazy"
        />
      )}
    </div>
  );
}
