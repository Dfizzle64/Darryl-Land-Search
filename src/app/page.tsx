import { AppShell } from "@/components/AppShell";
import { getParcelProvider } from "@/lib/data/adapters";
import { loadFixtureMeta, loadTrafficCollection, loadZoningConfig } from "@/lib/data/loadFixtures";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [parcels, traffic, zoningConfig, meta] = await Promise.all([
    getParcelProvider().listParcels(),
    loadTrafficCollection(),
    loadZoningConfig(),
    loadFixtureMeta(),
  ]);

  return (
    <AppShell
      parcels={parcels}
      traffic={traffic}
      zoningConfig={zoningConfig}
      meta={meta}
    />
  );
}
