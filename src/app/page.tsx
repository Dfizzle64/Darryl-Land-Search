import { AppShell } from "@/components/AppShell";
import { loadOrlandoParcelCollection, loadOrlandoParcelsMeta } from "@/lib/data/orlandoParcelStore";
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
  const [
    orlandoParcels,
    orlandoParcelsMeta,
    traffic,
    opportunityZones,
    oz2Tracts,
    ruralCatalog,
    ruralTracts,
    mfPriority,
    zoningConfig,
    fluConfig,
    meta,
  ] = await Promise.all([
    loadOrlandoParcelCollection(),
    loadOrlandoParcelsMeta(),
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

  const catalog = {
    ...ruralCatalog,
    parcelNote:
      "Orlando market loads partitioned parcel fixtures for Brevard, Lake, Marion, Orange, Osceola, Polk, Seminole, Sumter, and Volusia (public GIS). Zoning/FLU/AADT richness is Orange County first; other counties degrade gracefully. Other metros remain tract overlays until their parcel seeds land.",
  };

  return (
    <AppShell
      parcels={orlandoParcels}
      orlandoParcelsMeta={orlandoParcelsMeta}
      traffic={traffic}
      opportunityZones={opportunityZones}
      oz2Tracts={oz2Tracts}
      ruralCatalog={catalog}
      ruralTracts={ruralTracts}
      mfPriority={mfPriority}
      zoningConfig={zoningConfig}
      fluConfig={fluConfig}
      meta={meta}
    />
  );
}
