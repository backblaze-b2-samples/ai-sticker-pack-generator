import { PackDetail } from "@/components/packs/pack-detail";

export default async function PackDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PackDetail packId={id} />;
}
