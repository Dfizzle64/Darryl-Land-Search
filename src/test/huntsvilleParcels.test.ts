import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

type CountyRow = {
  name: string;
  fips: string;
  featureCount: number;
  coverage: string;
  source: string;
  queryUrl: string | null;
  gaps: string[];
  zoningJoinedCount?: number;
  zoningByCity?: Record<string, number>;
};

function countyRow(fips: string): CountyRow {
  const file = path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "county.json");
  return JSON.parse(readFileSync(file, "utf8")) as CountyRow;
}

function featuresFor(fips: string): ParcelFeature[] {
  const tiles = path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "tiles");
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(tiles)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Huntsville MSA parcels", () => {
  it("documents Marshall and Decatur as gaps and ships the three usable counties", () => {
    const madison = countyRow("01089");
    const limestone = countyRow("01083");
    const morgan = countyRow("01103");
    const marshall = countyRow("01095");

    expect(madison.coverage).toBe("complete-gte-5ac");
    expect(madison.source).toBe("al-madison-public-isv-185");
    expect(madison.queryUrl).toContain("Madison_Public_ISV/MapServer/185");
    expect(madison.featureCount).toBeGreaterThan(10000);
    expect(madison.gaps.join(" ")).toMatch(/no sale price/i);
    expect(madison.gaps.join(" ")).toContain("Layers/MapServer");

    expect(limestone.coverage).toBe("complete-gte-5ac");
    expect(limestone.source).toBe("al-limestone-remap-1");
    expect(limestone.queryUrl).toContain("Limestone_Parcels/MapServer/1");
    expect(limestone.featureCount).toBeGreaterThan(4000);
    expect(limestone.gaps.join(" ")).toMatch(/No sale/);

    expect(morgan.coverage).toBe("complete-gte-5ac");
    expect(morgan.source).toBe("al-morgan-vam-10");
    expect(morgan.queryUrl).toContain("AL52_VAM_MS/MapServer/10");
    expect(morgan.featureCount).toBeGreaterThan(700);
    expect(morgan.gaps.join(" ")).toMatch(/1516 source rows collapsed/);
    expect(morgan.gaps.join(" ")).toMatch(/Decatur/);
    expect(morgan.gaps.join(" ")).toMatch(/MapGeo/);

    expect(marshall.coverage).toBe("gap");
    expect(marshall.featureCount).toBe(0);
    expect(marshall.gaps.join(" ")).toMatch(/no countywide/i);
    expect(marshall.gaps.join(" ")).toContain("137");
    expect(marshall.queryUrl).toContain("CombinedParcels/MapServer/9");

    expect(madison.zoningByCity?.Huntsville ?? 0).toBeGreaterThan(0);
    expect(madison.zoningByCity?.["City of Madison"] ?? 0).toBeGreaterThan(0);
    expect(limestone.zoningByCity?.Huntsville ?? 0).toBeGreaterThan(0);
    expect(limestone.zoningByCity?.["City of Madison"] ?? 0).toBeGreaterThan(0);
  });

  it("keeps 5–150 acre attributes and city zoning on the tiled parcels", () => {
    const madison = featuresFor("01089");
    const limestone = featuresFor("01083");
    const morgan = featuresFor("01103");

    for (const feature of [...madison, ...limestone, ...morgan]) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.state).toBe("Alabama");
      expect(feature.properties.marketIds).toEqual(["Huntsville"]);
    }

    const madisonOwners = madison.filter((feature) => feature.properties.ownerName).length;
    expect(madisonOwners).toBeGreaterThan(madison.length * 0.9);
    const madisonLinks = madison.filter((feature) =>
      feature.properties.appraiserUrl?.includes("madisonproperty.countygovservices.com/Property/Property/Summary?ppin="),
    );
    expect(madisonLinks.length).toBeGreaterThan(madison.length * 0.9);
    expect(madison.some((feature) => feature.properties.lastSale.instrument?.includes("Book"))).toBe(true);
    expect(madison.some((feature) => feature.properties.tax.marketValue != null)).toBe(true);
    expect(madison.some((feature) => feature.properties.tax.landValue != null)).toBe(true);
    expect(madison.some((feature) => /^\d{4}-\d{2}-\d{2}$/.test(feature.properties.lastSale.date ?? ""))).toBe(true);
    expect(madison.every((feature) => feature.properties.lastSale.price == null)).toBe(true);

    expect(limestone.every((feature) => feature.properties.lastSale.price == null && feature.properties.lastSale.date == null)).toBe(true);
    expect(limestone.filter((feature) => feature.properties.ownerName).length).toBeGreaterThan(limestone.length * 0.9);
    expect(limestone.some((feature) => feature.properties.situsAddress)).toBe(true);
    expect(limestone.every((feature) => !feature.properties.ownerName || feature.properties.ownerName === feature.properties.ownerName.trim())).toBe(true);

    expect(morgan.some((feature) => (feature.properties.lastSale.price ?? 0) > 0)).toBe(true);
    expect(morgan.some((feature) => feature.properties.lastSale.date)).toBe(true);
    expect(morgan.every((feature) => feature.properties.zoningCode == null)).toBe(true);
    expect(morgan.some((feature) => feature.properties.dataGaps?.some((gap) => /Decatur/i.test(gap) && /MapGeo/i.test(gap)))).toBe(true);

    const zoned = [...madison, ...limestone].filter((feature) => feature.properties.zoningCode);
    expect(zoned.length).toBeGreaterThan(0);
    const jurisdictions = new Set(zoned.map((feature) => feature.properties.jurisdictionCode));
    expect(jurisdictions.has("Huntsville")).toBe(true);
    expect(jurisdictions.has("City of Madison")).toBe(true);
    expect([...jurisdictions].every((name) => name === "Huntsville" || name === "City of Madison")).toBe(true);
    expect(madison.some((feature) => feature.properties.jurisdictionCode === "Huntsville" || feature.properties.jurisdictionCode === "City of Madison")).toBe(true);
    expect(limestone.some((feature) => feature.properties.jurisdictionCode === "Huntsville" || feature.properties.jurisdictionCode === "City of Madison")).toBe(true);
  });
});
