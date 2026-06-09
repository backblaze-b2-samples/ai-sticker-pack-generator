import { GenerateForm } from "@/components/generate/generate-form";

export default function GeneratePage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Generate</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Describe a theme and pick a style — get a consistent sticker pack,
          stored in B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2 max-w-3xl">
        <GenerateForm />
      </div>
    </div>
  );
}
