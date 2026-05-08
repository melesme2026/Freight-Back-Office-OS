import { PortalRuntime } from "@/components/portal/PortalRuntime";

export default async function PortalLoadPage({ params }: { params: Promise<{ loadId: string }> }) {
  const { loadId } = await params;
  return <PortalRuntime routeLoadId={loadId} />;
}
