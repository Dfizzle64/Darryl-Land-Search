import { AppShell } from "@/components/AppShell";
import { getParcelProvider } from "@/lib/data/adapters";
import { loadFixtureMeta, loadFluConfig, loadTrafficCollection, loadZoningConfig } from "@/lib/data/loadFixtures";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [parcels, traffic, zoningConfig, fluConfig, meta] = await Promise.all([
    getParcelProvider().listParcels(),
    loadTrafficCollection(),
    loadZoningConfig(),
    loadFluConfig(),
    loadFixtureMeta(),
  ]);

  return (
    <AppShell
      parcels={parcels}
      traffic={traffic}
      zoningConfig={zoningConfig}
      fluConfig={fluConfig}
      meta={meta}
    />
  );
}
