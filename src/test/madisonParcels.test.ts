import { describe, expect, it } from "vitest";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { isOtherMarketId, isPrimaryMarket } from "../lib/markets";
import type { ParcelCollection } from "../lib/types";

describe("Jackson, Tennessee market", () => {
  it("is a secondary market and links Madison parcels to TPAD", () => {
    expect(isOtherMarketId("Jackson")).toBe(true);
    expect(isPrimaryMarket("Jackson")).toBe(false);
    const linked = parcelAppraiserUrl({
      parcelId: "057023    00200",
      countyFips: "47113",
      appraiserUrl: "https://assessment.cot.tn.gov/TPAD/Parcel/GIS?GISlink=057023%20%20%20%2000200",
    });
    expect(linked.href).toContain("GISlink=057023%20%20%20%2000200");
    expect(linked.label).toContain("Madison County");
  });
});

describe("Madison County fixture", () => {
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47113/county.json");

  it("records the GeoJobe pull, the acreage band, and the Medon gap", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8"));
    expect(county.fips).toBe("47113");
    expect(county.name).toBe("Madison");
    expect(county.state).toBe("Tennessee");
    expect(county.markets).toContain("Jackson");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(5000);
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    expect(county.source).toBe("tn-impact-47113");
    expect(county.queryUrl).toContain("k6aQP9AQncZQEtBv");
    expect(county.queryUrl).toContain("FeatureServer/45");
    expect(county.queryUrl).not.toContain("cmpdd.org");
    expect(county.queryUrl).not.toContain("maps.cot.tn.gov");
    const gaps = (county.gaps as string[]).join("\n");
    expect(gaps).toMatch(/Medon/);
    expect(gaps).toMatch(/no public zoning or FLU/i);
    expect(gaps).toMatch(/Mississippi/);

    const tiles = path.join(path.dirname(countyPath), "tiles");
    const names = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
    expect(names.length).toBeGreaterThan(0);
    let medon = 0;
    let features = 0;
    let jacksonFlu = 0;
    let jacksonCount = 0;
    let ruralCount = 0;
    for (const name of names) {
      const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        features += 1;
        const acres = feature.properties.acreage ?? 0;
        expect(acres).toBeGreaterThanOrEqual(5);
        expect(acres).toBeLessThanOrEqual(150);
        expect(feature.properties.countyFips).toBe("47113");
        expect(feature.properties.marketIds).toContain("Jackson");
        expect(feature.properties.appraiserUrl || "").toContain("TPAD/Parcel/GIS?GISlink=");
        if (feature.properties.jurisdictionCode === "MEDON") {
          medon += 1;
          expect(feature.properties.flu).toBeNull();
        }
        if (feature.properties.jurisdictionCode === "JACKSON") {
          jacksonCount += 1;
          if (feature.properties.zoningCode) {
            expect(feature.properties.zoningCode).not.toMatch(/^R-[123]$/);
          }
          if (feature.properties.flu) jacksonFlu += 1;
        }
        if (feature.properties.jurisdictionCode === "UNINCORPORATED") ruralCount += 1;
        if (feature.properties.jurisdictionCode !== "JACKSON" && feature.properties.jurisdictionCode !== "THREE WAY") {
          expect(feature.properties.flu).toBeNull();
        }
      }
    }
    expect(features).toBe(county.featureCount);
    expect(gaps).toContain(`Medon parcels ${medon}`);
    expect(ruralCount).toBeGreaterThan(jacksonCount);
    expect(gaps).toMatch(new RegExp(`Jackson zoning \\d+ / FLU ${jacksonFlu}`));
  });
});
