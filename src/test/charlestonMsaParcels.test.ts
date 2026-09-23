import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { formatParcelPlace, parcelAppraiserUrl, showFloridaSunbiz } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

type CountyRow = {
  fips: string;
  coverage: string;
  source: string;
  queryUrl: string | null;
  featureCount: number;
  gaps: string[];
  path: string | null;
};

function loadCounty(fips: string): { county: CountyRow; features: ParcelFeature[] } {
  const root = path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips);
  const county = JSON.parse(readFileSync(path.join(root, "county.json"), "utf8")) as CountyRow;
  const tiles = path.join(root, "tiles");
  const features = readdirSync(tiles)
    .filter((name) => name.endsWith(".geojson"))
    .flatMap((name) => {
      const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
      return collection.features;
    });
  return { county, features };
}

function countWhere(features: ParcelFeature[], pred: (feature: ParcelFeature) => boolean): number {
  return features.reduce((sum, feature) => sum + (pred(feature) ? 1 : 0), 0);
}

describe("Charleston MSA parcel extracts", () => {
  it("points assessor links at the county search and keeps Sunbiz on Florida", () => {
    expect(parcelAppraiserUrl({ parcelId: "4081400001", countyFips: "45019" })).toEqual({
      href: "https://gisccweb.charlestoncounty.org/public_search/",
      label: "Open Charleston County Property Appraiser search",
    });
    expect(parcelAppraiserUrl({ parcelId: "021-00-01-003", countyFips: "45015" }).href).toContain(
      "berkeleycountysc.gov",
    );
    expect(parcelAppraiserUrl({ parcelId: "118-00-00-092", countyFips: "45035" }).href).toContain(
      "dorchestercountysc.gov",
    );
    expect(showFloridaSunbiz("45019", "South Carolina")).toBe(false);
    expect(showFloridaSunbiz("12095", "Florida")).toBe(true);
    expect(showFloridaSunbiz(null, null)).toBe(true);
    expect(
      formatParcelPlace({
        situsCity: null,
        situsZip: null,
        countyName: "Charleston",
        state: "South Carolina",
        countyFips: "45019",
      }),
    ).toBe("Charleston County, SC");
    expect(
      formatParcelPlace({
        situsCity: "NORTH CHARLESTON",
        situsZip: "29418",
        countyName: "Charleston",
        state: "South Carolina",
      }),
    ).toBe("NORTH CHARLESTON 29418");
  });

  it("loads Charleston County outlines with PID, situs, sale, and land appraisal", () => {
    const { county, features } = loadCounty("45019");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("sc-charleston-energov-ent");
    expect(county.queryUrl).toContain("ENERGOV/energov_ent/MapServer/12");
    expect(county.gaps.join(" ")).toMatch(/499/);
    expect(county.gaps.join(" ")).toMatch(/Parcel_Search/);
    expect(county.gaps.join(" ")).toMatch(/Public_Search/);
    expect(features.length).toBe(county.featureCount);
    expect(features.length).toBeGreaterThan(5000);
    const withOwner = countWhere(features, (feature) => Boolean(feature.properties.ownerName));
    const withSitus = countWhere(features, (feature) => Boolean(feature.properties.situsAddress));
    const withLand = countWhere(features, (feature) => (feature.properties.tax.landValue ?? 0) > 0);
    const withSale = countWhere(features, (feature) => Boolean(feature.properties.lastSale.date));
    expect(withOwner).toBeGreaterThan(features.length * 0.9);
    expect(withSitus).toBeGreaterThan(features.length * 0.9);
    expect(withLand).toBeGreaterThan(features.length * 0.5);
    expect(withSale).toBeGreaterThan(features.length * 0.9);
    for (const feature of features) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.countyFips).toBe("45019");
      expect(feature.properties.state).toBe("South Carolina");
      expect(feature.properties.marketIds).toContain("Charleston");
      expect(feature.properties.parcelId).toMatch(/^\d+$/);
      expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
      const [lon, lat] = feature.properties.centroid;
      expect(lon).toBeGreaterThan(-81.3);
      expect(lon).toBeLessThan(-79.2);
      expect(lat).toBeGreaterThan(32.3);
      expect(lat).toBeLessThan(33.3);
      expect(feature.properties.tax.marketValue ?? null).toBeNull();
      const zoning = feature.properties.zoningCode?.toUpperCase();
      expect(zoning === "COUNTY" || zoning === "AWENDAW").toBe(false);
    }
    const townZoned = features.filter((feature) => feature.properties.jurisdictionCode === "MOUNT PLEASANT");
    const townFlu = features.filter((feature) => feature.properties.flu?.source === "sc-mount-pleasant-flu");
    expect(townZoned.length).toBeGreaterThan(20);
    expect(townFlu.length).toBeGreaterThan(20);
    expect(townZoned.every((feature) => Boolean(feature.properties.zoningCode))).toBe(true);
    expect(townFlu.every((feature) => feature.properties.flu?.jurisdiction === "Mount Pleasant" && feature.properties.flu?.code)).toBe(
      true,
    );
    const notes = county.gaps.join(" ");
    expect(notes).toMatch(/MPSC_Zoning_New/);
    expect(notes).toMatch(/MPSC_Land_Use_New/);
    expect(notes).toMatch(/Folly Beach/);
    expect(notes).toMatch(/Isle of Palms/);
    expect(notes).toMatch(/Sullivan/);
    expect(notes).toMatch(/James Island/);
    expect(notes).not.toMatch(/no verified public zoning REST URL/i);
  });

  it("loads Berkeley County outlines with owner, mailing, and tax fields from Addr_muni", () => {
    const { county, features } = loadCounty("45015");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("sc-berkeley-addr-muni");
    expect(county.queryUrl).toContain("custom/Addr_muni/MapServer/1");
    expect(county.gaps.join(" ")).toMatch(/499/);
    expect(county.gaps.join(" ")).toMatch(/parcels_berkeley_county/);
    expect(features.length).toBe(county.featureCount);
    expect(features.length).toBeGreaterThan(5000);
    expect(countWhere(features, (feature) => Boolean(feature.properties.ownerName))).toBeGreaterThan(features.length * 0.9);
    expect(countWhere(features, (feature) => Boolean(feature.properties.situsAddress))).toBeGreaterThan(1000);
    expect(countWhere(features, (feature) => Boolean(feature.properties.mailingAddress.line1))).toBeGreaterThan(
      features.length * 0.5,
    );
    expect(countWhere(features, (feature) => (feature.properties.tax.landValue ?? 0) > 0)).toBeGreaterThan(1000);
    expect(countWhere(features, (feature) => (feature.properties.tax.assessedValue ?? 0) > 0)).toBeGreaterThan(1000);
    for (const feature of features) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.countyFips).toBe("45015");
      expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
      const [lon, lat] = feature.properties.centroid;
      expect(lon).toBeGreaterThan(-80.6);
      expect(lon).toBeLessThan(-79.3);
      expect(lat).toBeGreaterThan(32.8);
      expect(lat).toBeLessThan(33.6);
    }
  });

  it("upgrades Dorchester attributes on the same public parcel layer", () => {
    const { county, features } = loadCounty("45035");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("sc-dorchester-parcels-public");
    expect(county.queryUrl).toContain("Parcels_Public/FeatureServer/0");
    expect(county.gaps.join(" ")).toMatch(/no market, assessed, or land-appraisal/i);
    expect(features.length).toBe(county.featureCount);
    expect(features.length).toBeGreaterThan(5000);
    expect(countWhere(features, (feature) => Boolean(feature.properties.situsAddress))).toBeGreaterThan(features.length * 0.5);
    expect(countWhere(features, (feature) => Boolean(feature.properties.zoningCode))).toBeGreaterThan(1000);
    expect(countWhere(features, (feature) => Boolean(feature.properties.lastSale.date))).toBeGreaterThan(1000);
    expect(countWhere(features, (feature) => Boolean(feature.properties.mailingAddress.city))).toBeGreaterThan(
      features.length * 0.5,
    );
    for (const feature of features) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.countyFips).toBe("45035");
      expect(feature.properties.tax.marketValue ?? null).toBeNull();
      expect(feature.properties.tax.landValue ?? null).toBeNull();
      expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
    }
    const docs = readFileSync(path.join(process.cwd(), "docs/market-parcels.md"), "utf8");
    expect(docs).toMatch(/energov_ent/);
    expect(docs).toMatch(/HTTP 499/);
    expect(docs).toMatch(/Addr_muni/);
  });
});
