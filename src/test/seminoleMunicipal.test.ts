import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { SEMINOLE_FLU_EMPTY, SEMINOLE_ZONING_EMPTY } from "../lib/seminoleMunicipal";

type Catalog = {
  doNotInventOpportunityZones: boolean;
  doNotRedownloadCountyParcels: boolean;
  blockedUrlFragments: string[];
  stubCodes: string[];
  places: {
    municipality: string;
    idField?: string;
    zoning: { url: string; code: string };
    flu: { url: string; code: string };
  }[];
  gaps: { municipality: string }[];
  rejected: string[];
};

type Summary = {
  source: string;
  featureCount: number;
  zoningJoinedCount: number;
  fluJoinedCount: number;
  opportunityZonesInvented: number;
  countyParcelsRedownloaded: boolean;
  byPlace: Record<string, { parcels: number; zoningJoined: number; fluJoined: number }>;
  overlays: { url: string }[];
};

const root = process.cwd();
const catalog = JSON.parse(readFileSync(path.join(root, "data/seminole-municipal.json"), "utf8")) as Catalog;
const summary = JSON.parse(readFileSync(path.join(root, "data/fixtures/seminole-municipal-join.json"), "utf8")) as Summary;

function features(): {
  parcelId: string;
  situsCity: string | null;
  zoningCode: string | null;
  flu: { code?: string | null; source?: string | null } | null;
  opportunityZone: unknown;
}[] {
  const folder = path.join(root, "data/fixtures/orlando-parcels/tiles/12117");
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

describe("Seminole municipal zoning and future land use", () => {
  it("wires the six city layers and blocks the retired and wrong-geography services", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.doNotRedownloadCountyParcels).toBe(true);
    expect(catalog.places.map((place) => place.municipality)).toEqual([
      "Casselberry",
      "Winter Springs",
      "Lake Mary",
      "Sanford",
      "Oviedo",
      "Altamonte Springs",
    ]);
    expect(catalog.places.map((place) => place.zoning.url)).toEqual([
      "https://maps.casselberry.org/mapping/rest/services/CommDev/Casselberry_Zoning/FeatureServer/0",
      "https://services5.arcgis.com/hbtBppF7t3PpouVf/arcgis/rest/services/City_of_Winter_Springs_Zoning/FeatureServer/3",
      "https://services1.arcgis.com/v0YMSb0ovdJoIQKg/arcgis/rest/services/PW_Zoning_Landuse_Query_AGO/FeatureServer/3",
      "https://gis.sanfordfl.gov/server/rest/services/Zoning/MapServer/0",
      "https://maps.cityofoviedo.net/arcgis/rest/services/Oviedo_Service_Data/DevelopmentServices/MapServer/11",
      "https://webgis.altamonte.org/gis/rest/services/EnerGov/EnerGovService/MapServer/39",
    ]);
    expect(catalog.places.map((place) => place.flu.url)).toEqual([
      "https://maps.casselberry.org/mapping/rest/services/CommDev/Casselberry_FLU/FeatureServer/3",
      "https://services5.arcgis.com/hbtBppF7t3PpouVf/arcgis/rest/services/Future_Land_Use_WFL1/FeatureServer/1",
      "https://services1.arcgis.com/v0YMSb0ovdJoIQKg/arcgis/rest/services/PW_Zoning_Landuse_Query_AGO/FeatureServer/4",
      "https://gis.sanfordfl.gov/server/rest/services/Land_Use/MapServer/2",
      "https://maps.cityofoviedo.net/arcgis/rest/services/Oviedo_Service_Data/DevelopmentServices/MapServer/10",
      "https://webgis.altamonte.org/gis/rest/services/EnerGov/EnerGovService/MapServer/44",
    ]);
    expect(catalog.places.find((place) => place.municipality === "Casselberry")?.idField).toBe("PARCEL");
    expect(catalog.places.find((place) => place.municipality === "Winter Springs")?.idField).toBe("PIN");
    expect(catalog.places.find((place) => place.municipality === "Lake Mary")?.zoning.code).toBe("Zoning");
    expect(catalog.places.find((place) => place.municipality === "Lake Mary")?.flu.code).toBe("FLUCODE");
    expect(catalog.gaps.map((gap) => gap.municipality)).toEqual(["Longwood"]);
    const urls = catalog.places.flatMap((place) => [place.zoning.url, place.flu.url]).join(" ");
    expect(urls).not.toMatch(/DSZoning|0EfLIvtSLPR9PKI2|Zoning_Flu|n4VF6lyYfB5kizho|giswebtechguru|EnerGov_WFL1/);
    expect(catalog.rejected.join(" ")).toMatch(/Hernando/);
    expect(catalog.rejected.join(" ")).toMatch(/Winter Park/);
    expect(catalog.stubCodes).toContain("SEMINOLE COUNTY");
    expect(catalog.stubCodes).toContain("CITY");
    const script = readFileSync(path.join(root, "scripts/join_seminole_municipal.py"), "utf8");
    expect(script).not.toMatch(/0EfLIvtSLPR9PKI2|n4VF6lyYfB5kizho/);
    expect(script).toMatch(/doNotRedownloadCountyParcels/);
    expect(SEMINOLE_ZONING_EMPTY).toMatch(/Longwood/);
    expect(SEMINOLE_FLU_EMPTY).toMatch(/Longwood/);
  });

  it("stamps city zoning onto the existing Seminole DOH shelf", () => {
    expect(summary.source).toBe("doh-ehwaters");
    expect(summary.featureCount).toBe(4788);
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.countyParcelsRedownloaded).toBe(false);
    expect(summary.zoningJoinedCount).toBeGreaterThan(0);
    expect(summary.fluJoinedCount).toBeGreaterThan(0);
    for (const name of catalog.places.map((place) => place.municipality)) {
      expect(summary.byPlace[name]?.zoningJoined).toBeGreaterThan(0);
      expect(summary.byPlace[name]?.fluJoined).toBeGreaterThan(0);
    }
    const overlayUrls = summary.overlays.map((item) => item.url).join(" ");
    expect(overlayUrls).not.toMatch(/DSZoning|Zoning_Flu|EnerGov_WFL1|n4VF6lyYfB5kizho/);
    expect(overlayUrls).toContain("DevelopmentServices/MapServer/11");
    expect(overlayUrls).toContain("Casselberry_FLU/FeatureServer/3");
    expect(overlayUrls).toContain("FeatureServer/4");
    expect(overlayUrls).not.toContain("Zhills");

    const rows = features();
    expect(rows).toHaveLength(4788);
    const byId = new Map(rows.map((row) => [row.parcelId, row]));
    expect(byId.get("2620305AR0D000570")?.zoningCode).toBe("I");
    expect(byId.get("2620305AR0D00131A")?.zoningCode ?? null).toBeNull();
    expect(byId.get("0821315JU00001840")?.zoningCode).toBe("PUD");
    expect(byId.get("0821315JU00001840")?.flu?.source).toBe("winter-springs-flu");
    const blanks = new Set(["LONGWOOD", "WINTER PARK", "APOPKA", "MAITLAND", "GENEVA", "CHULUOTA"]);
    const stubs = new Set(["SEMINOLE COUNTY", "CITY", "NONE", "NULL", "UN"]);
    for (const row of rows) {
      expect(row.opportunityZone ?? null).toBeNull();
      const municipal = (row as { municipal?: { placeId?: string } | null }).municipal;
      if (!municipal?.placeId) continue;
      const code = row.zoningCode?.toUpperCase() ?? "";
      expect(stubs.has(code)).toBe(false);
      const situs = (row.situsCity ?? "").toUpperCase();
      expect(blanks.has(situs)).toBe(false);
    }
  });
});
