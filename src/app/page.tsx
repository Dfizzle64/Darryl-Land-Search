import { AppShell } from "@/components/AppShell";
import { loadOrlandoParcelsMeta } from "@/lib/data/orlandoParcelStore";
import type { ParcelCollection } from "@/lib/types";
import {
  loadEligiblePackTracts,
  loadFixtureMeta,
  loadFluConfig,
  loadOpportunityZones,
  loadOtherMarketsCatalog,
  loadOz2Tracts,
  loadRuralMarketsCatalog,
  loadRuralMarketTracts,
  loadScMfPriority,
  loadUrbanMarketsCatalog,
  loadTrafficCollection,
  loadZoningConfig,
} from "@/lib/data/loadFixtures";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const emptyParcels: ParcelCollection = { type: "FeatureCollection", features: [] };
  const [
    orlandoParcelsMeta,
    traffic,
    opportunityZones,
    oz2Tracts,
    ruralCatalog,
    ruralTracts,
    urbanCatalog,
    otherCatalog,
    eligibleTracts,
    mfPriority,
    zoningConfig,
    fluConfig,
    meta,
  ] = await Promise.all([
    loadOrlandoParcelsMeta(),
    loadTrafficCollection(),
    loadOpportunityZones(),
    loadOz2Tracts(),
    loadRuralMarketsCatalog(),
    loadRuralMarketTracts(),
    loadUrbanMarketsCatalog(),
    loadOtherMarketsCatalog(),
    loadEligiblePackTracts(),
    loadScMfPriority(),
    loadZoningConfig(),
    loadFluConfig(),
    loadFixtureMeta(),
  ]);

  const catalog = {
    ...ruralCatalog,
    parcelNote:
      "Lake, Orange, Osceola, Polk, and Seminole load every public parcel from 5.0 through 150.0 acres (Florida DOH EHWATER; Orange zoning and FLU from OCPA and county open data). Parcels under 5 or over 150 are excluded. Brevard, Marion, Sumter, and Volusia stay thinner samples. The map requests the current viewport so the full extract stays responsive. Other metros remain tract overlays.",
  };

  return (
    <AppShell
      parcels={emptyParcels}
      orlandoParcelsMeta={orlandoParcelsMeta}
      traffic={traffic}
      opportunityZones={opportunityZones}
      oz2Tracts={oz2Tracts}
      ruralCatalog={catalog}
      ruralTracts={ruralTracts}
      urbanCatalog={urbanCatalog}
      otherCatalog={otherCatalog}
      eligibleTracts={eligibleTracts}
      mfPriority={mfPriority}
      zoningConfig={zoningConfig}
      fluConfig={fluConfig}
      meta={meta}
    />
  );
}
