import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CHARLOTTE_FLU_EMPTY, CHARLOTTE_ZONING_EMPTY } from "../lib/charlotteMunicipal";

type Catalog = {
  doNotInventOpportunityZones: boolean;
  doNotInventSchoolGrades: boolean;
  doNotInventBaseFloodElevations: boolean;
  doNotRedownloadCountyParcels: boolean;
  blockedUrlFragments: string[];
  stubCodes: string[];
  counties: Record<string, { source: string | null; featureCount: number; parcelBaseline: boolean }>;
  places: {
    municipality: string;
    fips: string[];
    fluStatus: string;
    zoning: { url: string; code: string };
    flu: { url: string; code: string };
  }[];
  rejected: string[];
};

type Summary = {
  opportunityZonesInvented: number;
  schoolGradesInvented: number;
  baseFloodElevationsInvented: number;
  countyParcelsRedownloaded: boolean;
  parcelBaseline: boolean;
  counties: { fips: string; featureCount: number; zoningJoinedCount: number; fluJoinedCount: number; opportunityZoneCount: number }[];
  byPlace: Record<string, { zoningJoined: number; fluJoined: number; indexedZoning: number; indexedFlu: number }>;
  overlays: { url: string }[];
};

const root = process.cwd();
const catalog = JSON.parse(readFileSync(path.join(root, "data/charlotte-municipal.json"), "utf8")) as Catalog;
const summary = JSON.parse(readFileSync(path.join(root, "data/fixtures/charlotte-municipal-join.json"), "utf8")) as Summary;

describe("Charlotte County, Florida municipal zoning and future land use", () => {
  it("wires Punta Gorda city layers and rejects the county stubs and namesakes", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.doNotInventSchoolGrades).toBe(true);
    expect(catalog.doNotInventBaseFloodElevations).toBe(true);
    expect(catalog.doNotRedownloadCountyParcels).toBe(true);
    expect(catalog.places.map((place) => place.municipality)).toEqual(["Punta Gorda"]);
    expect(catalog.counties["12015"]).toMatchObject({ source: null, featureCount: 0, parcelBaseline: false });
    const place = catalog.places[0];
    expect(place.fips).toEqual(["12015"]);
    expect(place.fluStatus).toBe("city");
    expect(place.zoning.url).toContain("ZoningOfficial_View/FeatureServer/0");
    expect(place.zoning.code).toBe("Zoning_Cla");
    expect(place.flu.url).toContain("FLU_All_2045/FeatureServer/5");
    expect(place.flu.code).toBe("LUName");
    expect(catalog.stubCodes).toContain("CITY");
    const blocked = catalog.blockedUrlFragments.join(" ");
    expect(blocked).toMatch(/BO_Charlotte/);
    expect(blocked).toMatch(/prefer-official/);
    expect(blocked).toMatch(/agis3\.charlottecountyfl\.gov/);
    expect(blocked).toMatch(/belize/i);
    const urls = `${place.zoning.url} ${place.flu.url}`;
    expect(urls).not.toMatch(/BO_Charlotte|prefer-official|agis3\.charlottecountyfl\.gov|CharlotteNC|belize/i);
    expect(catalog.rejected.join(" ")).toMatch(/North Carolina/);
    expect(catalog.rejected.join(" ")).toMatch(/Belize/);
    expect(catalog.rejected.join(" ")).toMatch(/ZONE_/);
    expect(catalog.rejected.join(" ")).toMatch(/NEWLU/);
    expect(CHARLOTTE_ZONING_EMPTY).toMatch(/Punta Gorda/);
    expect(CHARLOTTE_ZONING_EMPTY).toMatch(/CITY/);
    expect(CHARLOTTE_FLU_EMPTY).toMatch(/NEWLU/);
    const script = readFileSync(path.join(root, "scripts/join_charlotte_municipal.py"), "utf8");
    expect(script).not.toMatch(/floridahealth\.gov|EHWATER/);
    expect(script).toMatch(/ZoningOfficial_View/);
  });

  it("does not download a Charlotte County parcel shelf", () => {
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.schoolGradesInvented).toBe(0);
    expect(summary.baseFloodElevationsInvented).toBe(0);
    expect(summary.countyParcelsRedownloaded).toBe(false);
    expect(summary.parcelBaseline).toBe(false);
    expect(summary.counties[0]).toMatchObject({
      fips: "12015",
      featureCount: 0,
      zoningJoinedCount: 0,
      fluJoinedCount: 0,
      opportunityZoneCount: 0,
    });
    expect(summary.byPlace["Punta Gorda"].indexedZoning).toBeGreaterThan(0);
    expect(summary.byPlace["Punta Gorda"].indexedFlu).toBeGreaterThan(0);
    expect(summary.byPlace["Punta Gorda"].zoningJoined).toBe(0);
    expect(summary.byPlace["Punta Gorda"].fluJoined).toBe(0);
    const overlayUrls = summary.overlays.map((item) => item.url).join(" ");
    expect(overlayUrls).toContain("ZoningOfficial_View/FeatureServer/0");
    expect(overlayUrls).toContain("FLU_All_2045/FeatureServer/5");
    expect(overlayUrls).not.toMatch(/BO_Charlotte|CCGISLayers|belize/i);
    expect(existsSync(path.join(root, "data/fixtures/market-parcels/counties/12015"))).toBe(false);
  });
});
