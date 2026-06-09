"use client";

import Link from "next/link";
import { Sticker } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Button } from "@/components/ui/button";
import { StickerImage } from "@/components/packs/sticker-image";
import { usePacks } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import { styleLabel } from "@/lib/sticker-style";

export function PackLibrary() {
  const { data: packs = [], isLoading, error, refetch } = usePacks();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-56 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  if (packs.length === 0) {
    return (
      <EmptyState
        icon={Sticker}
        title="No packs yet"
        description="Generate your first sticker pack to start your library."
        action={
          <Button asChild size="sm">
            <Link href="/generate">Generate a pack</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {packs.map((pack) => (
        <Link key={pack.pack_id} href={`/packs/${pack.pack_id}`}>
          <Card className="card-hover overflow-hidden">
            <StickerImage
              packId={pack.pack_id}
              stickerKey={pack.cover_key ?? undefined}
              alt={pack.theme}
              className="aspect-square w-full"
            />
            <CardContent className="p-4 space-y-2">
              <div className="font-semibold text-sm truncate">{pack.theme}</div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <Badge variant="secondary" className="text-[11px]">
                  {styleLabel(pack.style)}
                </Badge>
                <span className="tabular-nums">{pack.sticker_count} stickers</span>
              </div>
              <div className="text-[11px] text-muted-foreground">
                {formatDate(pack.created_at)}
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}
