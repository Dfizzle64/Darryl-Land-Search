import { AppShell } from "@/components/AppShell";
import { getParcelProvider } from "@/lib/data/adapters";
import {
  loadFixtureMeta,
  loadFluConfig,
  loadOpportunityZones,
  loadOz2Tracts,
  loadTrafficCollection,
  loadZoningConfig,
} from "@/lib/data/loadFixtures";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [parcels, traffic, opportunityZones, oz2Tracts, zoningConfig, fluConfig, meta] = await Promise.all([
    getParcelProvider().listParcels(),
    loadTrafficCollection(),
    loadOpportunityZones(),
    loadOz2Tracts(),
    loadZoningConfig(),
    loadFluConfig(),
    loadFixtureMeta(),
  ]);

  return (
    <AppShell
      parcels={parcels}
      traffic={traffic}
      opportunityZones={opportunityZones}
      oz2Tracts={oz2Tracts}
      zoningConfig={zoningConfig}
      fluConfig={fluConfig}
      meta={meta}
    />
  );
}
