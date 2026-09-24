import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { MANATEE_SARASOTA_FLU_EMPTY, MANATEE_SARASOTA_ZONING_EMPTY } from "../lib/manateeSarasotaMunicipal";

type Layer = { url: string; code: string };
type Catalog = {
  doNotInventOpportunityZones: boolean;
  doNotInventSchoolGrades: boolean;
  doNotInventBaseFloodElevations: boolean;
  doNotRedownloadCountyParcels: boolean;
  blockedUrlFragments: string[];
  counties: Record<string, { source: string; featureCount: number }>;
  places: { municipality: string; fips: string[]; fluStatus: string; zoning: Layer; flu?: Layer }[];
  partials: { municipality: string; cityRest: string | null; situs: string[] }[];
  rejected: string[];
};

type Summary = {
  opportunityZonesInvented: number;
  schoolGradesInvented: number;
  baseFloodElevationsInvented: number;
  countyParcelsRedownloaded: boolean;
  counties: { fips: string; source: string; featureCount: number; zoningJoinedCount: number; fluJoinedCount: number; opportunityZoneCount: number }[];
  byPlace: Record<string, { zoningJoined: number; fluJoined: number; fluStatus: string }>;
  overlays: { url: string }[];
  partials: string[];
};

const root = process.cwd();
const catalog = JSON.parse(readFileSync(path.join(root, "data/manatee-sarasota-municipal.json"), "utf8")) as Catalog;
const summary = JSON.parse(readFileSync(path.join(root, "data/fixtures/manatee-sarasota-municipal-join.json"), "utf8")) as Summary;

function features(fips: string) {
  const folder = path.join(root, "data/fixtures/market-parcels/counties", fips, "tiles");
  const rows: {
    situsCity: string | null;
    zoningCode: string | null;
    flu: { code?: string | null } | null;
    opportunityZone: unknown;
    source: string;
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

describe("Manatee and Sarasota municipal zoning and future land use", () => {
  it("wires the city layers and leaves the barrier islands and Alabama namesake out", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.doNotInventSchoolGrades).toBe(true);
    expect(catalog.doNotInventBaseFloodElevations).toBe(true);
    expect(catalog.doNotRedownloadCountyParcels).toBe(true);
    expect(catalog.places.map((place) => place.municipality)).toEqual([
      "Bradenton",
      "Palmetto",
      "Longboat Key",
      "Sarasota",
      "North Port",
      "Venice",
    ]);
    expect(catalog.counties["12081"]).toMatchObject({ source: "fl-doh-ehwaters-12081", featureCount: 7239 });
    expect(catalog.counties["12115"]).toMatchObject({ source: "fl-doh-ehwaters-12115", featureCount: 4303 });
    const byName = new Map(catalog.places.map((place) => [place.municipality, place]));
    expect(byName.get("Bradenton")?.zoning.url).toContain("/Zoning/FeatureServer/0");
    expect(byName.get("Bradenton")?.flu?.url).toContain("/FLU_CoB/FeatureServer/0");
    expect(byName.get("Palmetto")?.zoning.code).toBe("ZONE");
    expect(byName.get("Palmetto")?.flu?.code).toBe("FLU");
    expect(byName.get("Longboat Key")?.fips).toEqual(["12081", "12115"]);
    expect(byName.get("Longboat Key")?.zoning.url).toContain("Longboat_Key_Zoning_Polygons");
    expect(byName.get("Longboat Key")?.flu?.url).toContain("/Future_Land_Use/FeatureServer/0");
    expect(byName.get("Sarasota")?.zoning.url).toContain("Zoning_Districts_(View_Only)");
    expect(byName.get("Sarasota")?.flu?.url).toContain("FutureLandUse/FeatureServer/3");
    expect(byName.get("North Port")?.flu).toBeUndefined();
    expect(byName.get("North Port")?.zoning.url).toContain("Hosted/CityNorthPortZoning/FeatureServer/0");
    expect(byName.get("Venice")?.fluStatus).toBe("gap");
    expect(byName.get("Venice")?.zoning.url).toContain("Hosted/CityVeniceZoning/FeatureServer/0");
    expect(catalog.partials.map((item) => item.municipality)).toEqual(["Anna Maria", "Bradenton Beach", "Holmes Beach"]);
    expect(catalog.partials.every((item) => item.cityRest === null)).toBe(true);
    const urls = catalog.places.flatMap((place) => [place.zoning.url, place.flu?.url ?? ""]).join(" ");
    expect(urls).not.toMatch(/3u10F1chkeawsUZY|CityVeniceZoningView|Hosted\/CitySarasotaZoning|geoport\.venicefl\.gov|Hosted\/FLUBoundary/);
    expect(catalog.rejected.join(" ")).toMatch(/Alabama/);
    expect(MANATEE_SARASOTA_ZONING_EMPTY).toMatch(/Anna Maria/);
    expect(MANATEE_SARASOTA_FLU_EMPTY).toMatch(/North Port/);
    expect(MANATEE_SARASOTA_FLU_EMPTY).toMatch(/Venice/);
  });

  it("stamps city zoning onto the existing Manatee and Sarasota DOH shelves", () => {
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.schoolGradesInvented).toBe(0);
    expect(summary.baseFloodElevationsInvented).toBe(0);
    expect(summary.countyParcelsRedownloaded).toBe(false);
    expect(summary.partials).toEqual(["Anna Maria", "Bradenton Beach", "Holmes Beach"]);
    const byFips = new Map(summary.counties.map((county) => [county.fips, county]));
    expect(byFips.get("12081")).toMatchObject({ source: "fl-doh-ehwaters-12081", featureCount: 7239, opportunityZoneCount: 0 });
    expect(byFips.get("12115")).toMatchObject({ source: "fl-doh-ehwaters-12115", featureCount: 4303, opportunityZoneCount: 0 });
    for (const name of ["Bradenton", "Palmetto", "Longboat Key", "Sarasota"]) {
      expect(summary.byPlace[name]?.zoningJoined).toBeGreaterThan(0);
      expect(summary.byPlace[name]?.fluJoined).toBeGreaterThan(0);
    }
    expect(summary.byPlace["North Port"]?.zoningJoined).toBeGreaterThan(0);
    expect(summary.byPlace["North Port"]?.fluJoined).toBe(0);
    expect(summary.byPlace.Venice?.zoningJoined).toBeGreaterThan(0);
    expect(summary.byPlace.Venice?.fluJoined).toBe(0);
    const overlayUrls = summary.overlays.map((item) => item.url).join(" ");
    expect(overlayUrls).toContain("FutureLandUse/FeatureServer/3");
    expect(overlayUrls).toContain("Hosted/CityNorthPortZoning");
    expect(overlayUrls).not.toMatch(/3u10F1chkeawsUZY|CityVeniceZoningView|CitySarasotaZoning/);

    const blanks = new Set(["ANNA MARIA", "BRADENTON BEACH", "HOLMES BEACH"]);
    for (const fips of ["12081", "12115"] as const) {
      const county = byFips.get(fips)!;
      const rows = features(fips);
      expect(rows).toHaveLength(county.featureCount);
      expect(rows.filter((row) => row.zoningCode).length).toBe(county.zoningJoinedCount);
      expect(rows.filter((row) => row.flu?.code).length).toBe(county.fluJoinedCount);
      for (const row of rows) {
        expect(row.opportunityZone ?? null).toBeNull();
        expect(row.source).toBe(county.source);
        const situs = (row.situsCity ?? "").trim().toUpperCase();
        if (blanks.has(situs)) {
          expect(row.zoningCode).toBeNull();
          expect(row.flu ?? null).toBeNull();
        }
        if (situs === "NORTH PORT" || situs === "VENICE") expect(row.flu ?? null).toBeNull();
      }
    }
  });
});
