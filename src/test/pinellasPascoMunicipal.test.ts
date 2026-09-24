import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

type Catalog = {
  doNotInventOpportunityZones: boolean;
  doNotRedownloadCountyParcels: boolean;
  blockedUrlFragments: string[];
  rejected: string[];
  partialFluGap: string;
  wired: {
    municipality: string;
    fips: string;
    fluStatus: string;
    zoning: { url: string };
    flu: { url: string };
  }[];
  partials: { municipality: string; service: string }[];
  gaps: { municipality: string; fips: string; situs: string[] }[];
};

type JoinSummary = {
  opportunityZonesInvented: number;
  countyParcelsRedownloaded: boolean;
  gaps: string[];
  counties: {
    fips: string;
    source: string;
    featureCount: number;
    zoningJoinedCount: number;
    fluJoinedCount: number;
    byPlace: Record<string, { parcels: number; zoningJoined: number; fluJoined: number; fluStatus: string }>;
    overlays: { url: string }[];
  }[];
};

const root = process.cwd();
const catalog = JSON.parse(readFileSync(path.join(root, "data/pinellas-pasco-municipal.json"), "utf8")) as Catalog;
const summary = JSON.parse(
  readFileSync(path.join(root, "data/fixtures/pinellas-pasco-municipal-join.json"), "utf8"),
) as JoinSummary;

function county(fips: string) {
  return summary.counties.find((item) => item.fips === fips);
}

function features(fips: string): {
  zoningCode: string | null;
  flu: { code?: string | null } | null;
  situsCity: string | null;
  opportunityZone: unknown;
  acreage?: number | null;
  municipal?: { placeId?: string } | null;
}[] {
  const folder = path.join(root, "data/fixtures/market-parcels/counties", fips, "tiles");
  const rows: {
    zoningCode: string | null;
    flu: { code?: string | null } | null;
    situsCity: string | null;
    opportunityZone: unknown;
    acreage?: number | null;
    municipal?: { placeId?: string } | null;
  }[] = [];
  for (const name of readdirSync(folder)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(folder, name), "utf8")) as {
      features: { properties: (typeof rows)[number] }[];
    };
    for (const feature of collection.features) rows.push(feature.properties);
  }
  return rows;
}

describe("Pinellas and Pasco municipal overlays", () => {
  it("keeps the wired city layers and blocks the wrong-geography services", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.doNotRedownloadCountyParcels).toBe(true);
    expect(catalog.wired.map((place) => place.municipality)).toEqual([
      "Dunedin",
      "Pinellas Park",
      "Tarpon Springs",
      "Safety Harbor",
      "Oldsmar",
      "New Port Richey",
      "Zephyrhills",
    ]);
    const urls = catalog.wired.flatMap((place) => [place.zoning.url, place.flu.url]);
    expect(urls).toContain("https://gis.dunedingov.com/server/rest/services/CommunityDevelopment/ZoningDistrict/FeatureServer/0");
    expect(urls).toContain("https://services6.arcgis.com/fH2ZwfxOgb5eaBS4/arcgis/rest/services/Planning_Development_2_WFL1/FeatureServer/19");
    expect(urls).toContain("https://gis.ctsfl.us/arcgis/rest/services/Hosted/Zoning_2025/FeatureServer/3");
    expect(urls).toContain("https://services3.arcgis.com/mmHgYti6dbsFdG2U/arcgis/rest/services/SafetyHarborZoning_11272023/FeatureServer/0");
    expect(urls).toContain("https://services8.arcgis.com/4LjX8EYY898im7w3/arcgis/rest/services/Public_Zoning/FeatureServer/0");
    expect(urls).toContain(
      "https://services7.arcgis.com/5fOG6RMXXiEvqNzn/arcgis/rest/services/NPR_2026_Community_Development_Map_WFL1/FeatureServer/10",
    );
    expect(urls).toContain("https://services6.arcgis.com/Q4fB6OTUhdN4M9BR/arcgis/rest/services/Zhills_EnGov_Map_11_2025/FeatureServer/4");
    expect(urls.join(" ")).not.toContain("Zhills_EnGov_Map_11_2025/FeatureServer/3");
    expect(urls.join(" ")).not.toContain("gulfport-ms.gov");
    expect(urls.join(" ")).not.toContain("Countywide_Plan_Map");
    expect(catalog.partials.map((place) => place.municipality)).toEqual([
      "Seminole",
      "South Pasadena",
      "Treasure Island",
      "Kenneth City",
      "North Redington Beach",
      "Indian Shores",
      "Belleair",
      "Indian Rocks Beach",
      "Redington Shores",
      "Madeira Beach",
    ]);
    expect(catalog.gaps.map((place) => place.municipality)).toEqual([
      "Largo",
      "Gulfport",
      "Belleair Beach",
      "Belleair Bluffs",
      "Redington Beach",
      "St. Pete Beach",
      "Port Richey",
      "Dade City",
      "San Antonio",
      "St. Leo",
    ]);
    const rejected = catalog.rejected.join(" ");
    expect(rejected).toMatch(/Hernando/);
    expect(rejected).toMatch(/Anderson/);
    expect(rejected).toMatch(/Gulfport, Mississippi/);
    const script = readFileSync(path.join(root, "scripts/pinellas_pasco_muni.py"), "utf8");
    expect(script).not.toMatch(/tampa_shed|seed_tampa|PascoMapper/);
    expect(script).toMatch(/doNotRedownloadCountyParcels/);
  });

  it("stamps city zoning onto the existing DOH shelves", () => {
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.countyParcelsRedownloaded).toBe(false);
    const pinellas = county("12103");
    const pasco = county("12101");
    expect(pinellas?.source).toBe("fl-doh-ehwaters-12103");
    expect(pasco?.source).toBe("fl-doh-ehwaters-12101");
    expect(pinellas?.featureCount).toBe(18638);
    expect(pasco?.featureCount).toBe(10590);
    for (const name of ["Dunedin", "Pinellas Park", "Tarpon Springs", "Safety Harbor", "Oldsmar"]) {
      expect(pinellas?.byPlace[name]?.zoningJoined).toBeGreaterThan(0);
      expect(pinellas?.byPlace[name]?.fluJoined).toBeGreaterThan(0);
      expect(pinellas?.byPlace[name]?.fluStatus).toBe("city");
    }
    for (const name of ["New Port Richey", "Zephyrhills"]) {
      expect(pasco?.byPlace[name]?.zoningJoined).toBeGreaterThan(0);
      expect(pasco?.byPlace[name]?.fluJoined).toBeGreaterThan(0);
      expect(pasco?.byPlace[name]?.fluStatus).toBe("city");
    }
    for (const name of catalog.partials.map((place) => place.municipality)) {
      const row = pinellas?.byPlace[name];
      expect(row?.fluJoined).toBe(0);
      expect(row?.fluStatus).toBe("gap");
      if (name === "North Redington Beach") expect(row?.parcels).toBe(0);
      if (name === "Redington Shores") expect(row?.zoningJoined).toBe(0);
      if ((row?.parcels ?? 0) > 0 && name !== "Redington Shores") expect(row?.zoningJoined).toBeGreaterThan(0);
    }
    const overlayUrls = [...(pinellas?.overlays ?? []), ...(pasco?.overlays ?? [])].map((item) => item.url).join(" ");
    expect(overlayUrls).not.toContain("gulfport-ms.gov");
    expect(overlayUrls).not.toContain("Zhills_EnGov_Map_11_2025/FeatureServer/3");
    expect(overlayUrls).toContain("Zhills_EnGov_Map_11_2025/FeatureServer/4");

    const guarded = new Set(["NPR", "PR", "SA", "DC", "ZH", "UN"]);
    const pinellasFeatures = features("12103");
    const pascoFeatures = features("12101");
    const pinellasShelf = JSON.parse(
      readFileSync(path.join(root, "data/fixtures/market-parcels/counties/12103/county.json"), "utf8"),
    ) as { featureCount: number; minAcres: number; maxAcres: number };
    const pascoShelf = JSON.parse(
      readFileSync(path.join(root, "data/fixtures/market-parcels/counties/12101/county.json"), "utf8"),
    ) as { featureCount: number; minAcres: number; maxAcres: number };
    expect(pinellasFeatures).toHaveLength(pinellasShelf.featureCount);
    expect(pascoFeatures).toHaveLength(pascoShelf.featureCount);
    expect(pinellasShelf).toMatchObject({ minAcres: 5, maxAcres: 150 });
    expect(pascoShelf).toMatchObject({ minAcres: 5, maxAcres: 150 });
    expect(pinellasFeatures.some((row) => row.municipal?.placeId)).toBe(true);
    expect(pascoFeatures.some((row) => row.municipal?.placeId)).toBe(true);
    for (const props of [...pinellasFeatures, ...pascoFeatures]) {
      const acres = props.acreage ?? 0;
      expect(acres).toBeGreaterThanOrEqual(5);
      expect(acres).toBeLessThanOrEqual(150);
      expect(props.opportunityZone ?? null).toBeNull();
      if (!props.municipal?.placeId) continue;
      expect(guarded.has(props.zoningCode?.toUpperCase() ?? "")).toBe(false);
    }
  });
});
