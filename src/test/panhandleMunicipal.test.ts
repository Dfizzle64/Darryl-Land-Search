import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { PANHANDLE_FLU_EMPTY, PANHANDLE_ZONING_EMPTY } from "../lib/panhandleMunicipal";

type Layer = { url?: string; code?: string; where?: string };

type Place = {
  municipality: string;
  fips: string[];
  coverage: string;
  zoning?: Layer;
  flu?: Layer;
};

type Catalog = {
  doNotInventOpportunityZones: boolean;
  doNotInventSchoolGrades: boolean;
  doNotInventBaseFloodElevations: boolean;
  doNotRedownloadCountyParcels: boolean;
  blockedUrlFragments: string[];
  counties: Record<string, { source: string | null; featureCount: number; parcelBaseline: boolean }>;
  places: Place[];
  partials: { municipality: string; situs: string[] }[];
  gapSitus: Record<string, string[]>;
  rejected: string[];
};

type Summary = {
  opportunityZonesInvented: number;
  schoolGradesInvented: number;
  baseFloodElevationsInvented: number;
  countyParcelsRedownloaded: boolean;
  counties: { fips: string; featureCount: number; zoningJoinedCount: number; fluJoinedCount: number; opportunityZoneCount: number; source: string | null }[];
  byPlace: Record<string, { parcels: number; zoningJoined: number; fluJoined: number; indexedZoning: number; indexedFlu: number }>;
  overlays: { url: string }[];
  partials: string[];
};

const root = process.cwd();
const catalog = JSON.parse(readFileSync(path.join(root, "data/panhandle-municipal.json"), "utf8")) as Catalog;
const summary = JSON.parse(readFileSync(path.join(root, "data/fixtures/panhandle-municipal-join.json"), "utf8")) as Summary;

function place(name: string): Place {
  const found = catalog.places.find((item) => item.municipality === name);
  if (!found) throw new Error(name);
  return found;
}

describe("Panhandle Florida municipal zoning and future land use", () => {
  it("wires the city layers and leaves the hard gaps unpublished", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.doNotInventSchoolGrades).toBe(true);
    expect(catalog.doNotInventBaseFloodElevations).toBe(true);
    expect(catalog.doNotRedownloadCountyParcels).toBe(true);
    expect(catalog.places.map((item) => item.municipality)).toEqual([
      "Panama City",
      "Pensacola",
      "Callaway",
      "Mexico Beach",
      "Lynn Haven",
      "Parker",
      "Springfield",
      "Destin",
      "Fort Walton Beach",
      "Panama City Beach",
      "DeFuniak Springs",
      "Paxton",
      "Milton",
      "Gulf Breeze",
      "Jay",
    ]);
    expect(catalog.counties["12005"]).toMatchObject({ source: null, featureCount: 0, parcelBaseline: false });
    expect(catalog.counties["12033"]).toMatchObject({ source: "fl-doh-ehwaters-12033", featureCount: 9097, parcelBaseline: true });
    expect(catalog.counties["12091"]).toMatchObject({ source: "fl-doh-ehwaters-12091", featureCount: 5854 });
    expect(catalog.counties["12113"]).toMatchObject({ source: "fl-doh-ehwaters-12113", featureCount: 7011 });
    expect(catalog.counties["12131"]).toMatchObject({ source: "fl-doh-ehwaters-12131", featureCount: 8179 });

    const panama = place("Panama City");
    expect(panama.zoning?.url).toContain("Zoning_CPC/FeatureServer/0");
    expect(panama.zoning?.code).toBe("LABEL");
    expect(panama.flu?.url).toContain("FutureLandUse_CPC/FeatureServer/0");
    expect(panama.flu?.code).toBe("LANDUSE");
    expect(panama.zoning?.url).not.toMatch(/LandUsePlanning/);

    const pensacola = place("Pensacola");
    expect(pensacola.coverage).toBe("zoning");
    expect(pensacola.flu).toBeUndefined();
    expect(pensacola.zoning?.url).toContain("maps.cityofpensacola.com/arcgis/rest/services/Zoning_WebMap_MIL1/MapServer/16");
    expect(pensacola.zoning?.code).toBe("ZONING");

    expect(place("Callaway").zoning?.where).toBe("SUB_ZONING=2");
    expect(place("Callaway").flu?.where).toBe("SUB_FLU=2");
    expect(place("Mexico Beach").zoning?.where).toBe("SUB_ZONING=4");
    expect(place("Mexico Beach").flu?.where).toBe("SUB_FLU=4");
    for (const name of ["Lynn Haven", "Parker", "Springfield", "Paxton"]) {
      expect(place(name).coverage).toBe("flu");
      expect(place(name).zoning).toBeUndefined();
    }
    expect(place("Lynn Haven").flu?.where).toBe("SUB_FLU=3");
    expect(place("Parker").flu?.where).toBe("SUB_FLU=7");
    expect(place("Springfield").flu?.where).toBe("SUB_FLU=8");
    expect(place("Paxton").flu?.code).toBe("FLU_CLASS");
    expect(place("Milton").flu).toBeUndefined();
    expect(place("Jay").flu).toBeUndefined();
    expect(place("Milton").zoning?.url).toContain("City_of_Milton_Zoning");
    expect(place("Gulf Breeze").zoning?.url).toContain("Gulf_Breeze_Zoning");
    expect(place("Gulf Breeze").flu?.code).toBe("flum");
    expect(place("Jay").zoning?.url).toContain("TownOfJayZoning");
    expect(place("Destin").zoning?.url).toContain("Zoning_JulyB_WFL1/FeatureServer/0");
    expect(place("Fort Walton Beach").flu?.url).toContain("gis.fwb.org/arcgis/rest/services/Maps/FLU/MapServer/0");
    expect(place("Panama City Beach").zoning?.url).toContain("Land_Use_and_Zoning/FeatureServer/47");
    expect(place("DeFuniak Springs").zoning?.url).toContain("WeeklyUpdatesDFS/FeatureServer/7");

    expect(catalog.partials.map((item) => item.municipality)).toEqual(["Freeport"]);
    expect(catalog.gapSitus["12033"]).toEqual(["CENTURY", "PENSACOLA BEACH"]);
    expect(catalog.gapSitus["12091"]).toEqual([
      "CRESTVIEW",
      "NICEVILLE",
      "VALPARAISO",
      "MARY ESTHER",
      "LAUREL HILL",
      "SHALIMAR",
      "CINCO BAYOU",
    ]);

    const urls = catalog.places
      .flatMap((item) => [item.zoning?.url, item.flu?.url])
      .filter(Boolean)
      .join(" ");
    for (const fragment of catalog.blockedUrlFragments) {
      expect(urls).not.toContain(fragment);
    }
    expect(urls).not.toMatch(/WeeklyUpdatesFreeport|AccelaMain|gis\.cityofpensacola\.com/);
    expect(catalog.rejected.join(" ")).toMatch(/523/);
    expect(catalog.rejected.join(" ")).toMatch(/Freeport/);
    expect(PANHANDLE_ZONING_EMPTY).toMatch(/Freeport/);
    expect(PANHANDLE_FLU_EMPTY).toMatch(/Pensacola/);
    const script = readFileSync(path.join(root, "scripts/join_panhandle_municipal.py"), "utf8");
    expect(script).not.toMatch(/floridahealth\.gov|EHWATER|WeeklyUpdatesFreeport/);
    expect(script).toMatch(/Panama City/);
    expect(script).toMatch(/LandUsePlanning/);
    expect(existsSync(path.join(root, "data/fixtures/market-parcels/counties/12005"))).toBe(false);
  });

  it("stamps the existing DOH shelves and leaves Bay, Freeport, and the gap cities blank", () => {
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.schoolGradesInvented).toBe(0);
    expect(summary.baseFloodElevationsInvented).toBe(0);
    expect(summary.countyParcelsRedownloaded).toBe(false);
    expect(summary.partials).toEqual(["Freeport"]);
    expect(summary.counties).toEqual([
      expect.objectContaining({ fips: "12033", featureCount: 9097, zoningJoinedCount: 810, fluJoinedCount: 0, opportunityZoneCount: 0, source: "fl-doh-ehwaters-12033" }),
      expect.objectContaining({ fips: "12091", featureCount: 5854, zoningJoinedCount: 270, fluJoinedCount: 270, opportunityZoneCount: 0, source: "fl-doh-ehwaters-12091" }),
      expect.objectContaining({ fips: "12113", featureCount: 7011, zoningJoinedCount: 85, fluJoinedCount: 9, opportunityZoneCount: 0, source: "fl-doh-ehwaters-12113" }),
      expect.objectContaining({ fips: "12131", featureCount: 8179, zoningJoinedCount: 135, fluJoinedCount: 158, opportunityZoneCount: 0, source: "fl-doh-ehwaters-12131" }),
      expect.objectContaining({ fips: "12005", featureCount: 0, zoningJoinedCount: 0, fluJoinedCount: 0, source: null }),
    ]);
    expect(summary.byPlace["Pensacola"]).toMatchObject({ parcels: 4368, zoningJoined: 810, fluJoined: 0 });
    expect(summary.byPlace["Destin"]).toMatchObject({ zoningJoined: 202, fluJoined: 202 });
    expect(summary.byPlace["Fort Walton Beach"]).toMatchObject({ zoningJoined: 68, fluJoined: 68 });
    expect(summary.byPlace["Milton"]).toMatchObject({ zoningJoined: 53, fluJoined: 0 });
    expect(summary.byPlace["Gulf Breeze"]).toMatchObject({ zoningJoined: 9, fluJoined: 9 });
    expect(summary.byPlace["Jay"]).toMatchObject({ zoningJoined: 23, fluJoined: 0 });
    expect(summary.byPlace["DeFuniak Springs"]).toMatchObject({ zoningJoined: 135, fluJoined: 134 });
    expect(summary.byPlace["Paxton"]).toMatchObject({ zoningJoined: 0, fluJoined: 24, indexedFlu: 103 });
    expect(summary.byPlace["Panama City Beach"]).toMatchObject({ parcels: 24, zoningJoined: 0, fluJoined: 0, indexedZoning: 633 });
    expect(summary.byPlace["Panama City"]).toMatchObject({ parcels: 0, zoningJoined: 0, fluJoined: 0, indexedZoning: 18777, indexedFlu: 17300 });
    expect(summary.byPlace["Callaway"].indexedZoning).toBeGreaterThan(0);
    expect(summary.byPlace["Lynn Haven"]).toMatchObject({ indexedZoning: 0, indexedFlu: 778, zoningJoined: 0 });
    const overlayUrls = summary.overlays.map((item) => item.url).join(" ");
    expect(overlayUrls).toContain("Zoning_WebMap_MIL1/MapServer/16");
    expect(overlayUrls).not.toMatch(/WeeklyUpdatesFreeport|gis\.cityofpensacola\.com|AccelaMain/);

    const gap = new Map(Object.entries(catalog.gapSitus).map(([fips, cities]) => [fips, new Set(cities)]));
    const freeport = new Set(["FREEPORT", "FREEPORT`"]);
    const totals = new Map<string, { n: number; zoning: number; flu: number }>();
    for (const fips of ["12033", "12091", "12113", "12131"]) {
      const tileDir = path.join(root, "data/fixtures/market-parcels/counties", fips, "tiles");
      let n = 0;
      let zoning = 0;
      let flu = 0;
      for (const name of readdirSync(tileDir)) {
        const data = JSON.parse(readFileSync(path.join(tileDir, name), "utf8")) as {
          features: { properties: Record<string, unknown> }[];
        };
        for (const feature of data.features) {
          n += 1;
          const props = feature.properties;
          const city = String(props.situsCity ?? "").toUpperCase();
          const zoningCode = props.zoningCode;
          const fluCode = (props.flu as { code?: string } | null)?.code;
          if (zoningCode) zoning += 1;
          if (fluCode) flu += 1;
          if (typeof zoningCode === "string") expect(zoningCode).not.toMatch(/^\d+$/);
          if (typeof fluCode === "string") expect(fluCode).not.toMatch(/^\d+$/);
          if (gap.get(fips)?.has(city) || freeport.has(city)) {
            expect(zoningCode ?? null).toBeNull();
            expect(fluCode ?? null).toBeNull();
          }
          if (city === "PENSACOLA" || city === "MILTON" || city === "JAY") expect(fluCode ?? null).toBeNull();
          if (city === "PAXTON") expect(zoningCode ?? null).toBeNull();
        }
      }
      totals.set(fips, { n, zoning, flu });
    }
    expect(totals.get("12033")).toEqual({ n: 9097, zoning: 810, flu: 0 });
    expect(totals.get("12091")).toEqual({ n: 5854, zoning: 270, flu: 270 });
    expect(totals.get("12113")).toEqual({ n: 7011, zoning: 85, flu: 9 });
    expect(totals.get("12131")).toEqual({ n: 8179, zoning: 135, flu: 158 });
  }, 30000);
});
