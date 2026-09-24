import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { MARTIN_IRC_FLU_EMPTY, MARTIN_IRC_ZONING_EMPTY } from "../lib/martinIrcMunicipal";

type Layer = { url: string; code: string; role?: string };
type Catalog = {
  doNotInventOpportunityZones: boolean;
  doNotRedownloadCountyParcels: boolean;
  blockedUrlFragments: string[];
  stubCodes: string[];
  counties: Record<string, { source: string; featureCount: number }>;
  places: {
    municipality: string;
    fips: string;
    idField?: string;
    fluStatus: string;
    zoning: Layer;
    flu?: Layer;
  }[];
  partials: { municipality: string; cityRest: string | null; zoning: Layer; flu: Layer }[];
  gaps: { municipality: string; situs: string[] }[];
  rejected: string[];
};

type PlaceStat = { parcels: number; zoningJoined: number; fluJoined: number; fluStatus?: string; cityRest?: string | null };
type CountySummary = {
  fips: string;
  source: string;
  featureCount: number;
  zoningJoinedCount: number;
  fluJoinedCount: number;
  opportunityZoneCount: number;
  byPlace: Record<string, PlaceStat>;
  overlays: { url: string }[];
};
type Summary = {
  opportunityZonesInvented: number;
  countyParcelsRedownloaded: boolean;
  counties: CountySummary[];
  gaps: string[];
};

const root = process.cwd();
const catalog = JSON.parse(readFileSync(path.join(root, "data/martin-irc-municipal.json"), "utf8")) as Catalog;
const summary = JSON.parse(readFileSync(path.join(root, "data/fixtures/martin-irc-municipal-join.json"), "utf8")) as Summary;

const STUBS = new Set([
  "JUPITER ISLAND",
  "INDIANTOWN",
  "OCEAN BREEZE",
  "SEWALLS POINT",
  "SEWALL'S POINT",
  "NO DATA",
  "CITY",
  "COUNTY",
  "NONE",
  "NULL",
  "UN",
]);

const VERO_FLU_CODES = new Set(["RL", "RM", "RH", "C", "I", "MX", "CV", "ES", "GU", "P", "MHP", "MR"]);

function features(fips: string): {
  parcelId: string;
  situsCity: string | null;
  zoningCode: string | null;
  flu: { code?: string | null; source?: string | null } | null;
  opportunityZone: unknown;
  source: string;
  municipal?: { zoningLayer?: string | null; fluLayer?: string | null } | null;
}[] {
  const folder = path.join(root, "data/fixtures/market-parcels/counties", fips, "tiles");
  const rows: ReturnType<typeof features> = [];
  for (const name of readdirSync(folder)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(folder, name), "utf8")) as {
      features: { properties: (typeof rows)[number] }[];
    };
    for (const feature of collection.features) rows.push(feature.properties);
  }
  return rows;
}

describe("Martin and Indian River municipal zoning and future land use", () => {
  it("wires the city layers and leaves the named gaps blank", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.doNotRedownloadCountyParcels).toBe(true);
    expect(catalog.places.map((place) => place.municipality)).toEqual(["Stuart", "Indiantown", "Vero Beach", "Sebastian"]);
    expect(catalog.counties["12085"]).toMatchObject({ source: "fl-doh-ehwaters-12085", featureCount: 3802 });
    expect(catalog.counties["12061"]).toMatchObject({ source: "fl-doh-ehwaters-12061", featureCount: 3416 });
    const stuart = catalog.places[0];
    expect(stuart.idField).toBe("PCN");
    expect(stuart.zoning.url).toBe("https://services.arcgis.com/RyoFD3Lw9KSERnvQ/arcgis/rest/services/COS_Zoning/FeatureServer/0");
    expect(stuart.zoning.code).toBe("ZONING");
    expect(stuart.flu?.url).toBe("https://services.arcgis.com/RyoFD3Lw9KSERnvQ/arcgis/rest/services/Future_Land_Use/FeatureServer/0");
    expect(stuart.flu?.code).toBe("LAND_USE");
    const indiantown = catalog.places[1];
    expect(indiantown.zoning.url).toContain("voi_zoning_public/FeatureServer/0");
    expect(indiantown.zoning.code).toBe("Abbrev");
    expect(indiantown.flu?.url).toContain("voi_flu_public/FeatureServer/0");
    expect(indiantown.flu?.code).toBe("FLU");
    const vero = catalog.places[2];
    expect(vero.zoning.url).toBe("https://services1.arcgis.com/mK9abRqiJFkUgbPZ/arcgis/rest/services/ZoningDistricts/FeatureServer/0");
    expect(vero.flu?.url).toBe("https://services1.arcgis.com/mK9abRqiJFkUgbPZ/arcgis/rest/services/ZoningFutureLandUse/FeatureServer/0");
    expect(vero.zoning.url).not.toBe(vero.flu?.url);
    expect(vero.zoning.code).toBe("Code");
    expect(vero.flu?.code).toBe("Code");
    expect(catalog.places[3].flu).toBeUndefined();
    expect(catalog.places[3].fluStatus).toBe("gap");
    expect(catalog.places[3].zoning.url).toBe("https://gisportal.ircgov.com/server3/rest/services/COS/COS_Zoning/MapServer/0");
    expect(catalog.partials[0].cityRest).toBeNull();
    expect(catalog.partials[0].municipality).toBe("Ocean Breeze");
    expect(catalog.gaps.map((gap) => gap.municipality)).toEqual([
      "Sewall's Point",
      "Jupiter Island",
      "Fellsmere",
      "Indian River Shores",
      "Orchid",
    ]);
    const urls = [
      ...catalog.places.flatMap((place) => [place.zoning.url, place.flu?.url ?? ""]),
      catalog.partials[0].zoning.url,
      catalog.partials[0].flu.url,
    ].join(" ");
    expect(urls).not.toMatch(/maps\.ocoee\.org|\/COVB\/|Zoning_Flu|pbcgov|clearviewgeographic|ZoningMerged|Zoning_Parcels/);
    expect(catalog.rejected.join(" ")).toMatch(/Ocoee/);
    expect(catalog.rejected.join(" ")).toMatch(/COVB/);
    expect(catalog.stubCodes).toEqual([...STUBS]);
    const script = readFileSync(path.join(root, "scripts/join_martin_irc_municipal.py"), "utf8");
    expect(script).toMatch(/doNotRedownloadCountyParcels/);
    expect(script).not.toMatch(/maps\.ocoee\.org|\/COVB\/|Parcels\/MapServer/);
    expect(MARTIN_IRC_ZONING_EMPTY).toMatch(/Sewall's Point/);
    expect(MARTIN_IRC_ZONING_EMPTY).toMatch(/Jupiter Island/);
    expect(MARTIN_IRC_FLU_EMPTY).toMatch(/Sebastian/);
  });

  it("stamps city zoning onto the existing Martin and Indian River DOH shelves", () => {
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.countyParcelsRedownloaded).toBe(false);
    expect(summary.gaps).toEqual(["Sewall's Point", "Jupiter Island", "Fellsmere", "Indian River Shores", "Orchid"]);
    const byFips = new Map(summary.counties.map((county) => [county.fips, county]));
    const martin = byFips.get("12085");
    const irc = byFips.get("12061");
    expect(martin).toMatchObject({ source: "fl-doh-ehwaters-12085", featureCount: 3802, opportunityZoneCount: 0 });
    expect(irc).toMatchObject({ source: "fl-doh-ehwaters-12061", featureCount: 3416, opportunityZoneCount: 0 });
    expect(martin?.zoningJoinedCount).toBeGreaterThan(0);
    expect(martin?.fluJoinedCount).toBeGreaterThan(0);
    expect(irc?.zoningJoinedCount).toBeGreaterThan(0);
    expect(irc?.fluJoinedCount).toBeGreaterThan(0);
    for (const name of ["Stuart", "Indiantown", "Vero Beach"]) {
      const place = martin?.byPlace[name] ?? irc?.byPlace[name];
      expect(place?.zoningJoined).toBeGreaterThan(0);
      expect(place?.fluJoined).toBeGreaterThan(0);
    }
    expect(irc?.byPlace.Sebastian?.zoningJoined).toBeGreaterThan(0);
    expect(irc?.byPlace.Sebastian?.fluJoined).toBe(0);
    expect(martin?.byPlace["Ocean Breeze"]?.cityRest ?? null).toBeNull();
    const overlayUrls = summary.counties.flatMap((county) => county.overlays.map((item) => item.url)).join(" ");
    expect(overlayUrls).toContain("COS_Zoning/FeatureServer/0");
    expect(overlayUrls).toContain("Future_Land_Use/FeatureServer/0");
    expect(overlayUrls).toContain("voi_zoning_public");
    expect(overlayUrls).toContain("voi_flu_public");
    expect(overlayUrls).toContain("ZoningDistricts/FeatureServer/0");
    expect(overlayUrls).toContain("ZoningFutureLandUse/FeatureServer/0");
    expect(overlayUrls).toContain("COS/COS_Zoning/MapServer/0");
    expect(overlayUrls).not.toMatch(/Future_Landuse_Zoning|\/COVB\/|maps\.ocoee\.org|ZoningMerged/);

    const blanks = new Set(["SEWALL'S POINT", "SEWALLS POINT", "JUPITER ISLAND", "FELLSMERE", "INDIAN RIVER SHORES", "ORCHID"]);
    for (const fips of ["12085", "12061"] as const) {
      const county = byFips.get(fips)!;
      const rows = features(fips);
      expect(rows).toHaveLength(county.featureCount);
      expect(rows.filter((row) => row.zoningCode).length).toBe(county.zoningJoinedCount);
      expect(rows.filter((row) => row.flu?.code).length).toBe(county.fluJoinedCount);
      for (const row of rows) {
        expect(row.opportunityZone ?? null).toBeNull();
        expect(row.source).toBe(county.source);
        expect(STUBS.has((row.zoningCode ?? "").toUpperCase())).toBe(false);
        expect(STUBS.has((row.flu?.code ?? "").toUpperCase())).toBe(false);
        const situs = (row.situsCity ?? "").trim().toUpperCase();
        if (blanks.has(situs)) {
          expect(row.zoningCode).toBeNull();
          expect(row.flu ?? null).toBeNull();
        }
        if (situs === "SEBASTIAN") expect(row.flu ?? null).toBeNull();
        if (situs === "VERO BEACH" && row.flu?.code) {
          expect(VERO_FLU_CODES.has(row.flu.code)).toBe(true);
          expect(row.flu.source).toBe("vero-beach-flu");
          expect(row.municipal?.zoningLayer ?? "").toContain("ZoningDistricts/FeatureServer/0");
          expect(row.municipal?.fluLayer ?? "").toContain("ZoningFutureLandUse/FeatureServer/0");
        }
      }
    }
  });
});
