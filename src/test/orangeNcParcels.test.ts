import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const SHELLS = new Set(["CH", "CA", "HI", "ME", "DU"]);

describe("Orange County NC appraiser link", () => {
  it("opens the Spatialest property record instead of the Florida appraiser", () => {
    const search = parcelAppraiserUrl({ parcelId: "0800050553", countyFips: "37135" });
    expect(search.href).toBe("https://property.spatialest.com/nc/orange/#/");
    expect(search.label).toContain("NC");
    expect(search.label).not.toMatch(/Florida|OCPA/i);
    const deep = parcelAppraiserUrl({
      parcelId: "0800050553",
      countyFips: "37135",
      appraiserUrl: "https://property.spatialest.com/nc/orange/#/property/0800050553",
    });
    expect(deep.href).toBe("https://property.spatialest.com/nc/orange/#/property/0800050553");
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "12095" }).href).toContain("ocpafl.org");
  });
});

describe("Orange County NC 5–150 acre fixtures", () => {
  it("ships county GIS parcels with owner, situs join, and city-aware zoning", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37135/county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      source: string;
      featureCount: number;
      coverage: string;
      gaps: string[];
      enrich?: { situsMatched?: number; zoningMatched?: number; fluMatched?: number };
    };
    expect(county.fips).toBe("37135");
    expect(county.source).toBe("nc-orange-webparcel-37135");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(8000);
    expect(county.featureCount).toBeLessThan(12000);
    expect(county.gaps.join(" ")).toMatch(/Carrboro/);
    expect(county.gaps.join(" ")).toMatch(/tax-stamp|STAMPVALUE/);
    expect(county.enrich?.situsMatched ?? 0).toBeGreaterThan(1000);
    expect(county.enrich?.zoningMatched ?? 0).toBeGreaterThan(1000);

    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37135/tiles");
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let withOwner = 0;
    let withMail = 0;
    let withSitus = 0;
    let withZoning = 0;
    let withFlu = 0;
    let carrboro = 0;
    let carrboroFlu = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("37135");
        expect(props.marketIds).toContain("Raleigh-Durham");
        expect(props.source).toBe("nc-orange-webparcel-37135");
        expect(props.appraiserUrl).toContain(`property/${props.parcelId}`);
        const zoning = (props.zoningCode || "").toUpperCase();
        expect(SHELLS.has(zoning)).toBe(false);
        if (props.ownerName) withOwner += 1;
        if (props.mailingAddress?.line1) withMail += 1;
        if (props.situsAddress) withSitus += 1;
        if (props.zoningCode) withZoning += 1;
        if (props.flu?.code) withFlu += 1;
        if (props.jurisdictionCode === "CA") {
          carrboro += 1;
          if (props.flu) carrboroFlu += 1;
        }
        seen += 1;
      }
    }
    expect(seen).toBe(county.featureCount);
    expect(withOwner).toBeGreaterThan(seen * 0.9);
    expect(withMail).toBeGreaterThan(seen * 0.9);
    expect(withSitus).toBeGreaterThan(seen * 0.5);
    expect(withZoning).toBeGreaterThan(seen * 0.5);
    expect(withFlu).toBeGreaterThan(1000);
    expect(carrboro).toBeGreaterThan(0);
    expect(carrboroFlu).toBe(0);
  });
});
