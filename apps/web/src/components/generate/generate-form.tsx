"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Wand2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { GeneratingLoader } from "@/components/ui/generating-loader";
import { ApiError } from "@/lib/api-client";
import { useGeneratePack } from "@/lib/queries";
import {
  DEFAULT_PACK_SIZE,
  MAX_PACK_SIZE,
  QUALITY_OPTIONS,
  SAFE_PACK_SIZE,
  STYLE_OPTIONS,
} from "@/lib/sticker-style";
import type { Quality, StylePreset } from "@ai-sticker-pack-generator/shared";

export function GenerateForm() {
  const router = useRouter();
  const generate = useGeneratePack();

  const [theme, setTheme] = useState("");
  const [style, setStyle] = useState<StylePreset>("kawaii");
  const [packSize, setPackSize] = useState(DEFAULT_PACK_SIZE);
  const [quality, setQuality] = useState<Quality>("low");

  // Cost guardrail: a large, high-quality pack can exceed the $1 demo budget.
  const costy = packSize > SAFE_PACK_SIZE || quality !== "low";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = theme.trim();
    if (trimmed.length < 2) {
      toast.error("Describe a theme (at least 2 characters).");
      return;
    }
    generate.mutate(
      { theme: trimmed, style, pack_size: packSize, quality },
      {
        onSuccess: (manifest) => {
          toast.success(
            `Generated ${manifest.sticker_count} stickers for "${manifest.theme}"`,
          );
          router.push(`/packs/${manifest.pack_id}`);
        },
        onError: (err) => {
          const detail =
            err instanceof ApiError ? err.message : "Generation failed";
          toast.error(detail);
        },
      },
    );
  };

  if (generate.isPending) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-4 py-20">
          <GeneratingLoader size="lg" variant="stars" label="Generating your pack…" />
          <p className="text-sm text-muted-foreground max-w-sm text-center">
            Creating {packSize} stickers in a consistent style. This can take a
            minute — each sticker is generated and stored in B2.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">New sticker pack</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="theme">Theme prompt</Label>
            <Textarea
              id="theme"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="e.g. a grumpy orange cat, a happy avocado, a tiny astronaut"
              rows={3}
              maxLength={200}
            />
            <p className="text-xs text-muted-foreground">
              One subject works best — poses and expressions vary automatically.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Style preset</Label>
              <Select value={style} onValueChange={(v) => setStyle(v as StylePreset)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STYLE_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Quality</Label>
              <Select value={quality} onValueChange={(v) => setQuality(v as Quality)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {QUALITY_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2 max-w-[12rem]">
            <Label htmlFor="pack_size">Pack size</Label>
            <Input
              id="pack_size"
              type="number"
              min={1}
              max={MAX_PACK_SIZE}
              value={packSize}
              onChange={(e) =>
                setPackSize(
                  Math.max(1, Math.min(MAX_PACK_SIZE, Number(e.target.value) || 1)),
                )
              }
            />
          </div>

          {costy && (
            <p className="text-xs text-[var(--attention)]">
              Heads up: larger packs and higher quality cost more. The demo
              default (≤{SAFE_PACK_SIZE} stickers at Low) stays well under $1.
            </p>
          )}

          <Button type="submit" className="h-9">
            <Wand2 className="h-4 w-4" />
            Generate pack
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
