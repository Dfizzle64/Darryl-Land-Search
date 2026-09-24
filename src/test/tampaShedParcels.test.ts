import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { getParcelProvider } from "../lib/data/adapters";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

type CountyRow = {
  fips: string;
  source: string;
  queryUrl: string;
  featureCount: number;
  coverage: string;
  gaps: string[];
  path: string;
  zoningJoinedCount: number;
  fluJoinedCount: number;
  municipalityCounts: Record<string, number>;
  rejected?: string[];
  overlays?: { role: string; url: string }[];
  municipalOverlayJoins?: Record<string, { parcels: number; zoningJoined: number; fluJoined: number; fluStatus: string }>;
};

const root = process.cwd();

function countyRow(fips: string): CountyRow {
  const file = path.join(root, "data/fixtures/market-parcels/counties", fips, "county.json");
  expect(existsSync(file)).toBe(true);
  return JSON.parse(readFileSync(file, "utf8")) as CountyRow;
}

function findFeature(relativeTiles: string, accept: (feature: ParcelFeature) => boolean): ParcelFeature | undefined {
  const folder = path.join(root, relativeTiles);
  const files = readdirSync(folder).filter((name) => name.endsWith(".geojson"));
  for (const file of files) {
    const collection = JSON.parse(readFileSync(path.join(folder, file), "utf8")) as ParcelCollection;
    const found = collection.features.find(accept);
    if (found) return found;
  }
  return undefined;
}

function iterateFeatures(relativeTiles: string): ParcelFeature[] {
  const folder = path.join(root, relativeTiles);
  const files = readdirSync(folder).filter((name) => name.endsWith(".geojson"));
  const features: ParcelFeature[] = [];
  for (const file of files) {
    const collection = JSON.parse(readFileSync(path.join(folder, file), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

function sampleFeatures(relativeTiles: string, limit: number): ParcelFeature[] {
  const folder = path.join(root, relativeTiles);
  const files = readdirSync(folder).filter((name) => name.endsWith(".geojson"));
  expect(files.length).toBeGreaterThan(0);
  const features: ParcelFeature[] = [];
  for (const file of files) {
    const collection = JSON.parse(readFileSync(path.join(folder, file), "utf8")) as ParcelCollection;
    features.push(...collection.features);
    if (features.length >= limit) break;
  }
  return features.slice(0, limit);
}

describe("Tampa shed county cards", () => {
  it("wires Hillsborough, Pasco, Pinellas, and the Polk upgrade", () => {
    const sources = JSON.parse(readFileSync(path.join(root, "data/tampa-shed-parcel-sources.json"), "utf8")) as {
      counties: { fips: string; source: string; queryUrl: string }[];
    };
    for (const expected of sources.counties) {
      const row = countyRow(expected.fips);
      expect(row.source).toBe(expected.source);
      expect(row.queryUrl).toBe(expected.queryUrl);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.featureCount).toBeGreaterThan(1000);
      expect(row.path.startsWith(`data/fixtures/market-parcels/counties/${expected.fips}/`)).toBe(true);
      expect(row.path.includes("orlando-parcels")).toBe(false);
    }
  });

  it("rejects the Pasco hosted master-list subset and keeps city stubs out of zoning codes", () => {
    const pasco = countyRow("12101");
    expect(pasco.queryUrl).toContain("PascoMapper/Parcels/MapServer/7");
    expect(pasco.queryUrl).not.toContain("County_Master_Property_List");
    expect(pasco.rejected?.join(" ")).toContain("County_Master_Property_List");
    expect(pasco.featureCount).toBeGreaterThan(10_000);
    expect(pasco.gaps.join(" ")).toMatch(/placeholder/i);
    const features = sampleFeatures(pasco.path, 400);
    for (const feature of features) {
      const code = feature.properties.zoningCode?.toUpperCase();
      expect(code === "NPR" || code === "PR" || code === "SA").toBe(false);
      expect(feature.properties.municipality).toBeTruthy();
    }
    expect(pasco.municipalityCounts["Unincorporated Pasco"]).toBeGreaterThan(1000);
    expect(pasco.municipalityCounts["New Port Richey"]).toBeGreaterThan(0);
  });

  it("labels Hillsborough municipalities and does not treat VI as a qualified sale", () => {
    const hillsborough = countyRow("12057");
    expect(hillsborough.queryUrl).toContain("ParcelPublishing/FeatureServer/12");
    expect(hillsborough.zoningJoinedCount).toBeGreaterThan(8000);
    expect(hillsborough.fluJoinedCount).toBeGreaterThan(8000);
    for (const label of ["Tampa", "Temple Terrace", "Plant City", "Unincorporated Hillsborough"]) {
      expect(hillsborough.municipalityCounts[label]).toBeGreaterThan(20);
    }
    expect(hillsborough.gaps.join(" ")).toMatch(/VI/);
    const features = sampleFeatures(hillsborough.path, 80);
    for (const feature of features) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.municipality).toBeTruthy();
      expect(feature.properties.lastSale.qualified === "V" || feature.properties.lastSale.qualified === "I").toBe(false);
      expect(feature.properties.marketIds).toEqual(["Tampa"]);
    }
  });

  it("keeps Pinellas market value empty and labels St. Petersburg, Clearwater, and Largo", () => {
    const pinellas = countyRow("12103");
    expect(pinellas.queryUrl).toContain("PublicWebGIS/Parcels/MapServer/1");
    expect(pinellas.gaps.join(" ")).toMatch(/just\/market/i);
    expect(pinellas.municipalityCounts["St. Petersburg"]).toBeGreaterThan(20);
    expect(pinellas.municipalityCounts.Clearwater).toBeGreaterThan(20);
    expect(pinellas.municipalityCounts.Largo).toBeGreaterThan(20);
    expect(pinellas.municipalityCounts["Unincorporated Pinellas"]).toBeGreaterThan(20);
    const features = sampleFeatures(pinellas.path, 120);
    for (const feature of features) {
      expect(feature.properties.tax.marketValue).toBeNull();
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
    }
    const appraiser = parcelAppraiserUrl({ parcelId: "1", countyFips: "12103" });
    expect(appraiser.href).toContain("pcpao.org");
    expect(appraiser.label).toContain("Pinellas");
  });

  it("upgrades Polk parcels and joins Lakeland zoning without inventing county districts", () => {
    const polk = countyRow("12105");
    expect(polk.queryUrl).toContain("Property_Appraiser/MapServer/134");
    expect(polk.path.includes("orlando-parcels")).toBe(false);
    expect(polk.zoningJoinedCount).toBeGreaterThan(100);
    expect(polk.zoningJoinedCount).toBeLessThan(polk.featureCount / 2);
    expect(polk.fluJoinedCount).toBeGreaterThan(2000);
    expect(polk.gaps.join(" ")).toMatch(/zoning-district/i);
    expect(polk.gaps.join(" ")).toMatch(/Lakeland/i);
    expect(polk.rejected?.join(" ")).toContain("lakelandgov.net");
    expect(polk.rejected?.join(" ")).not.toContain("services1.arcgis.com");
    const overlayUrls = (polk.overlays ?? []).map((overlay) => overlay.url).join(" ");
    expect(overlayUrls).toContain("services1.arcgis.com/mcbQY5xNGGGM1vBX/arcgis/rest/services/Zoning/FeatureServer/0");
    expect(overlayUrls).toContain("services1.arcgis.com/mcbQY5xNGGGM1vBX/arcgis/rest/services/Future_Land_Use/FeatureServer/0");
    const features = sampleFeatures(polk.path, 60);
    for (const feature of features) {
      expect(feature.properties.marketIds?.includes("Orlando")).toBe(false);
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.municipality).toBeTruthy();
    }
    const lakeland = findFeature(
      polk.path,
      (feature) =>
        feature.properties.municipality === "Lakeland" &&
        Boolean(feature.properties.zoningCode) &&
        feature.properties.flu?.source === "lakeland-flu",
    );
    expect(lakeland?.properties.zoningCode).toBeTruthy();
    expect(lakeland?.properties.zoningDistrict).toBe(lakeland?.properties.zoningCode);
    expect(lakeland?.properties.flu?.jurisdiction).toBe("Lakeland");
    expect(lakeland?.properties.flu?.source).toBe("lakeland-flu");
    const orlandoTile = path.join(root, "data/fixtures/orlando-parcels/tiles/12105");
    expect(existsSync(orlandoTile)).toBe(true);
  });

  it("joins Pinellas and Pasco city zoning without painting the wrong cities", () => {
    const pinellas = countyRow("12103");
    const pasco = countyRow("12101");
    const pinellasJoins = pinellas.municipalOverlayJoins ?? {};
    const pascoJoins = pasco.municipalOverlayJoins ?? {};
    for (const name of ["Dunedin", "Pinellas Park", "Tarpon Springs", "Safety Harbor", "Oldsmar"]) {
      expect(pinellasJoins[name]?.zoningJoined).toBeGreaterThan(0);
      expect(pinellasJoins[name]?.fluJoined).toBeGreaterThan(0);
      expect(pinellasJoins[name]?.fluStatus).toBe("city");
    }
    for (const name of ["New Port Richey", "Zephyrhills"]) {
      expect(pascoJoins[name]?.zoningJoined).toBeGreaterThan(0);
      expect(pascoJoins[name]?.fluJoined).toBeGreaterThan(0);
    }
    for (const name of [
      "Seminole",
      "South Pasadena",
      "Treasure Island",
      "Kenneth City",
      "North Redington Beach",
      "Indian Shores",
      "Belleair",
      "Indian Rocks Beach",
      "Madeira Beach",
    ]) {
      expect(pinellasJoins[name]?.zoningJoined).toBeGreaterThan(0);
      expect(pinellasJoins[name]?.fluJoined).toBe(0);
      expect(pinellasJoins[name]?.fluStatus).toBe("gap");
    }
    expect(pinellasJoins["Redington Shores"]?.fluJoined).toBe(0);
    const overlayUrls = [...(pinellas.overlays ?? []), ...(pasco.overlays ?? [])].map((item) => item.url).join(" ");
    expect(overlayUrls).toContain("gis.dunedingov.com");
    expect(overlayUrls).toContain("Planning_Development_2_WFL1/FeatureServer/19");
    expect(overlayUrls).toContain("Zoning_2025/FeatureServer/3");
    expect(overlayUrls).toContain("SafetyHarborZoning_11272023");
    expect(overlayUrls).toContain("Public_Zoning/FeatureServer/0");
    expect(overlayUrls).toContain("NPR_2026_Community_Development_Map_WFL1/FeatureServer/10");
    expect(overlayUrls).toContain("Zhills_EnGov_Map_11_2025/FeatureServer/4");
    expect(overlayUrls).toContain("Zoning_2025/FeatureServer/3");
    expect(overlayUrls).not.toContain("Zhills_EnGov_Map_11_2025/FeatureServer/3");
    expect(overlayUrls).not.toContain("gulfport-ms.gov");
    expect(overlayUrls).not.toContain("Countywide_Plan_Map");
    const rejected = `${pinellas.rejected?.join(" ")} ${pasco.rejected?.join(" ")}`;
    expect(rejected).toMatch(/Hernando/);
    expect(rejected).toMatch(/Anderson/);
    expect(rejected).toMatch(/Gulfport, Mississippi/);
    expect(pinellas.gaps.join(" ")).toMatch(/Largo/);
    expect(pasco.gaps.join(" ")).toMatch(/placeholder/i);

    const park = findFeature(pinellas.path, (feature) => feature.properties.parcelId === "253015000004300100");
    expect(park?.properties.municipality).toBe("Pinellas Park");
    expect(park?.properties.zoningCode).toBe("CH");
    expect(park?.properties.flu?.code).toBe("CG");
    expect(park?.properties.flu?.source).toBe("pinellas-park-flu");
    expect(park?.properties.opportunityZone ?? null).toBeNull();

    const dunedin = findFeature(pinellas.path, (feature) => feature.properties.parcelId === "142815000003200100");
    expect(dunedin?.properties.zoningCode).toBe("MPL");
    expect(dunedin?.properties.flu?.code).toBe("R/OS");
    expect(dunedin?.properties.flu?.source).toBe("dunedin-flu");

    const seminole = findFeature(pinellas.path, (feature) => feature.properties.parcelId === "353015798840000010");
    expect(seminole?.properties.zoningCode).toBe("R/OS");
    expect(seminole?.properties.flu).toBeNull();
    expect(seminole?.properties.zoningCode).not.toBe("UN");

    const largo = findFeature(pinellas.path, (feature) => feature.properties.municipality === "Largo" && feature.properties.flu?.source === "largo-flu");
    expect(largo?.properties.zoningCode).toBeNull();

    const gulfport = findFeature(pinellas.path, (feature) => feature.properties.municipality === "Gulfport");
    expect(gulfport?.properties.zoningCode).toBeNull();
    expect(gulfport?.properties.flu).toBeNull();

    const npr = findFeature(pasco.path, (feature) => feature.properties.parcelId === "33-25-16-0070-00800-0000");
    expect(npr?.properties.municipality).toBe("New Port Richey");
    expect(npr?.properties.zoningCode).toBe("MHP");
    expect(npr?.properties.flu?.code).toBe("HIGH DEN");
    expect(npr?.properties.flu?.source).toBe("new-port-richey-flu");

    const hills = findFeature(pasco.path, (feature) => feature.properties.parcelId === "04-26-21-0000-00100-0020");
    expect(hills?.properties.municipality).toBe("Zephyrhills");
    expect(hills?.properties.zoningCode).toBe("PUD");
    expect(hills?.properties.flu?.code).toBe("R/OS");
    expect(hills?.properties.flu?.source).toBe("zephyrhills-flu");

    const portRichey = findFeature(pasco.path, (feature) => feature.properties.municipality === "Port Richey");
    expect(portRichey?.properties.zoningCode ?? null).toBeNull();

    const guarded = ["NPR", "PR", "SA", "DC", "ZH", "UN"];
    for (const feature of iterateFeatures(pinellas.path).concat(iterateFeatures(pasco.path))) {
      const code = feature.properties.zoningCode?.toUpperCase();
      expect(guarded.includes(code ?? "")).toBe(false);
      if (feature.properties.municipality === "Largo") expect(feature.properties.zoningCode).toBeNull();
      if (feature.properties.municipality === "Gulfport" || feature.properties.municipality === "Belleair Bluffs") {
        expect(feature.properties.zoningCode).toBeNull();
        expect(feature.properties.flu).toBeNull();
      }
      if (feature.properties.municipality === "St. Petersburg" && feature.properties.flu) {
        expect(feature.properties.flu.source).toBe("st-petersburg-flu");
      }
      if (feature.properties.municipality === "Clearwater" && feature.properties.flu) {
        expect(feature.properties.flu.source).toBe("clearwater-flu");
      }
      if (feature.properties.municipality === "Port Richey" || feature.properties.municipality === "Dade City" || feature.properties.municipality === "San Antonio" || feature.properties.municipality === "St. Leo") {
        expect(feature.properties.zoningCode).toBeNull();
      }
    }
  });

  it("returns the Polk upgrade by id when the Orlando extract shares the parcel id", async () => {
    const parcel = await getParcelProvider().getParcel("12105:222601000000021030");
    expect(parcel?.properties.source).toBe("fl-polk-property-appraiser-134");
    expect(parcel?.properties.municipality).toBe("Kathleen");
    expect(parcel?.properties.zoningCode).toBeNull();
    expect(parcel?.properties.flu?.code).toBeTruthy();
    expect(parcel?.properties.marketIds).toEqual(["Tampa"]);
  });
});
