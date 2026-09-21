import { AppShell } from "@/components/AppShell";
import { getParcelProvider } from "@/lib/data/adapters";
import {
  loadFixtureMeta,
  loadFluConfig,
  loadOpportunityZones,
  loadTrafficCollection,
  loadZoningConfig,
} from "@/lib/data/loadFixtures";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [parcels, traffic, opportunityZones, zoningConfig, fluConfig, meta] = await Promise.all([
    getParcelProvider().listParcels(),
    loadTrafficCollection(),
    loadOpportunityZones(),
    loadZoningConfig(),
    loadFluConfig(),
    loadFixtureMeta(),
  ]);

  return (
    <AppShell
      parcels={parcels}
      traffic={traffic}
      opportunityZones={opportunityZones}
      zoningConfig={zoningConfig}
      fluConfig={fluConfig}
      meta={meta}
    />
  );
}
