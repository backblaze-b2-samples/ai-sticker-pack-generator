import Link from "next/link";
import { Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PackLibrary } from "@/components/packs/pack-library";

export default function PacksPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Packs</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your generated sticker packs, stored under{" "}
            <code className="text-xs">sticker-packs/</code> in B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/generate">
            <Wand2 className="h-3.5 w-3.5" />
            New pack
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <PackLibrary />
      </div>
    </div>
  );
}
