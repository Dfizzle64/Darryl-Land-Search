import { AppShell } from "@/components/AppShell";
import { loadMarketParcelIndex } from "@/lib/data/marketParcelStore";
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
    marketParcelIndex,
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
    loadMarketParcelIndex(),
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
      "Lake, Orange, Osceola, Polk, and Seminole load every public parcel from 5.0 through 150.0 acres. Other markets load their own 5–150 acre tiles only while that market is selected. Parcel polygons stay off until you zoom in past the tract outlines. Counties without an open polygon source stay documented gaps.",
  };

  return (
    <AppShell
      parcels={emptyParcels}
      orlandoParcelsMeta={orlandoParcelsMeta}
      marketParcelIndex={marketParcelIndex}
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
