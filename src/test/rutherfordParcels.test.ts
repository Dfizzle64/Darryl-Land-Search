import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { loadZoningConfig } from "../lib/data/loadFixtures";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import { zoningAllowsMultifamily } from "../lib/zoning";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47149");
const APPRAISER = "https://secured.rutherfordcountytn.gov/OFS/WP/PropertySearch/QuickSearch";

describe("Rutherford County parcel enrich", () => {
  it("scores only the multifamily districts named for Rutherford", async () => {
    const zoning = await loadZoningConfig();
    expect(zoningAllowsMultifamily("MUR-RM-12", "RM-12", zoning, false, false)).toBe(true);
    expect(zoningAllowsMultifamily("MUR-RM-16", "RM-16", zoning, false, false)).toBe(true);
    expect(zoningAllowsMultifamily("SMY-R-5", "R-5", zoning, false, false)).toBe(true);
    expect(zoningAllowsMultifamily("SMY-R-6", "R-6", zoning, false, false)).toBe(true);
    expect(zoningAllowsMultifamily("RUT-RMF", "RMF", zoning, false, false)).toBe(true);
    expect(zoningAllowsMultifamily("SMY-R-1", "R-1", zoning, false, false)).toBe(false);
    expect(zoningAllowsMultifamily("LVG-R-3", "R-3", zoning, false, false)).toBe(false);
    expect(zoningAllowsMultifamily("EAG-R-1", "R-1", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("RUT-RM", "RM", zoning, false, false)).toBe(false);
  });

  it("points the appraiser link at WebPro Quick Search", () => {
    const link = parcelAppraiserUrl({ parcelId: "140-015.02-000", countyFips: "47149" });
    expect(link.href).toBe(APPRAISER);
    expect(link.label).toContain("Rutherford");
  });

  it("ships 5–150 acre Rutherford parcels on the Nashville market", () => {
    const countyPath = path.join(COUNTY, "county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      source: string;
      coverage: string;
      featureCount: number;
      queryUrl: string;
      gaps: string[];
      markets: string[];
    };
    expect(county.fips).toBe("47149");
    expect(county.markets).toContain("Nashville");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("tn-rutherford-agol-parcels");
    expect(county.queryUrl).toContain("Parcel_Data/FeatureServer/1");
    expect(county.queryUrl).not.toContain("/Assessor");
    expect(county.featureCount).toBeGreaterThan(9000);
    const gapText = county.gaps.join("\n");
    expect(gapText).toMatch(/not an IMPACT county/i);
    expect(gapText).toMatch(/La Vergne/);
    expect(gapText).toMatch(/Eagleville/);
    expect(gapText).toMatch(/Smyrna/);
    expect(gapText).toMatch(/Character Areas/);
    expect(gapText).not.toMatch(/tn-impact/);

    const tiles = path.join(COUNTY, "tiles");
    const files = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let owners = 0;
    let mailing = 0;
    let situs = 0;
    let tax = 0;
    let sale = 0;
    let gis = 0;
    const cityCodes = new Set<string>();
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties as ParcelFeature["properties"];
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("47149");
        expect(props.state).toBe("Tennessee");
        expect(props.marketIds).toContain("Nashville");
        expect(props.parcelId.length).toBeGreaterThan(0);
        expect(props.appraiserUrl).toBe(APPRAISER);
        expect(props.source).toBe("tn-rutherford-agol-parcels");
        if (props.ownerName) owners += 1;
        if (props.mailingAddress?.line1) mailing += 1;
        if (props.situsAddress) situs += 1;
        if (props.tax.marketValue != null || props.tax.assessedValue != null) tax += 1;
        if (props.lastSale.date || props.lastSale.price != null) sale += 1;
        if (props.gisLink) gis += 1;
        if (props.cityCode) cityCodes.add(props.cityCode);
        if (props.cityCode === "515") {
          expect(props.jurisdictionPrefix).toBe("MUR");
          if (props.flu) expect(props.flu.source).toBe("murfreesboro-rsa-flu-2023");
          expect(props.zoningSource === "rutherford-county-zoning").toBe(false);
        }
        if (props.cityCode === "674" || props.cityCode === "400" || props.cityCode === "227") {
          expect(props.flu).toBeNull();
        }
        if (props.cityCode === "000" && props.flu) {
          expect(props.flu.source).toBe("rutherford-character-areas");
        }
        if (props.cityCode === "400" && props.zoningCode) {
          expect(props.zoningCode.startsWith("LVG-")).toBe(true);
        }
        seen += 1;
      }
    }
    expect(seen).toBe(county.featureCount);
    expect(owners).toBeGreaterThan(seen * 0.9);
    expect(mailing).toBeGreaterThan(seen * 0.8);
    expect(situs).toBeGreaterThan(seen * 0.5);
    expect(tax).toBeGreaterThan(seen * 0.9);
    expect(sale).toBeGreaterThan(seen * 0.5);
    expect(gis).toBe(seen);
    expect(cityCodes.has("515")).toBe(true);
    expect(cityCodes.has("000")).toBe(true);
    expect(cityCodes.has("674")).toBe(true);
    expect(cityCodes.has("400")).toBe(true);
  });
});
