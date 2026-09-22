import { AppShell } from "@/components/AppShell";
import { getParcelProvider } from "@/lib/data/adapters";
import {
  loadFixtureMeta,
  loadFluConfig,
  loadOpportunityZones,
  loadOz2Tracts,
  loadRuralMarketsCatalog,
  loadRuralMarketTracts,
  loadScMfPriority,
  loadTrafficCollection,
  loadZoningConfig,
} from "@/lib/data/loadFixtures";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [parcels, traffic, opportunityZones, oz2Tracts, ruralCatalog, ruralTracts, mfPriority, zoningConfig, fluConfig, meta] =
    await Promise.all([
      getParcelProvider().listParcels(),
      loadTrafficCollection(),
      loadOpportunityZones(),
      loadOz2Tracts(),
      loadRuralMarketsCatalog(),
      loadRuralMarketTracts(),
      loadScMfPriority(),
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
      ruralCatalog={ruralCatalog}
      ruralTracts={ruralTracts}
      mfPriority={mfPriority}
      zoningConfig={zoningConfig}
      fluConfig={fluConfig}
      meta={meta}
    />
  );
}
