import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadFluConfig, loadZoningConfig } from "../lib/data/loadFixtures";
import { fluAllowsMultifamily } from "../lib/flu";
import { formatParcelPlace, parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";
import { zoningAllowsMultifamily } from "../lib/zoning";

const CITY_GAPS = ["Senoia", "Grantville", "Moreland", "Turin", "Sharpsburg", "Haralson", "Palmetto", "Chattahoochee Hills"];

describe("Coweta place line and assessor link", () => {
  it("names Georgia and qPublic AppID 704, not Orange County", () => {
    expect(formatParcelPlace({ countyName: "Coweta", state: "Georgia", situsCity: null, situsZip: null })).toBe(
      "Coweta County, Georgia",
    );
    expect(formatParcelPlace({ countyName: "Orange", state: "Florida", situsCity: null, situsZip: null })).toBe(
      "Orange County, FL",
    );
    const link = parcelAppraiserUrl({ parcelId: "001  4161 001", countyFips: "13077" });
    expect(link.href).toContain("AppID=704");
    expect(link.href).toContain("LayerID=11412");
    expect(link.label).toContain("Coweta");
    expect(link.href).not.toContain("ocpa");
  });

  it("does not score Coweta or Newnan districts as Orange County multifamily", async () => {
    const zoning = await loadZoningConfig();
    const flu = await loadFluConfig();
    expect(zoningAllowsMultifamily("C-2", "Coweta:C-2", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("RC", "Coweta:RC", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("RU-7", "Newnan:RU-7", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("PD", "PD", zoning, true, true)).toBe(true);
    expect(
      fluAllowsMultifamily(
        { code: "Industrial", label: "Industrial", jurisdiction: "Newnan", source: "newnan-flu" },
        flu,
      ),
    ).toBeNull();
  });
});

describe("Coweta County 5–150 acre extract", () => {
  it("keeps WinGap parcels enriched with acres, county zoning, and Newnan FLU only", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13077/county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      gaps: string[];
      state: string;
    };
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(1000);
    expect(county.state).toBe("Georgia");
    expect(county.source).toBe("ga-coweta-wingap-parcels");
    expect(county.queryUrl).toContain("WinGapParcels/MapServer/0");
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/ParcelPropertyValues/);
    expect(gaps).toMatch(/lastSale is left null/);
    expect(gaps).toMatch(/Newnan/);
    expect(gaps).toMatch(/AppID 704/);
    for (const city of CITY_GAPS) {
      expect(gaps).toContain(city);
    }

    const tilesDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13077/tiles");
    const files = readdirSync(tilesDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let checked = 0;
    let zoning = 0;
    let cowetaZoning = 0;
    let newnanZoning = 0;
    let flu = 0;
    let newnanCity = 0;
    let seenOwner = false;
    let seenValue = false;
    const fluJurisdictions = new Set<string>();
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tilesDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("13077");
        expect(props.state).toBe("Georgia");
        expect(props.source).toBe("ga-coweta-wingap-parcels");
        expect(props.marketIds).toContain("Atlanta");
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-85.05);
        expect(lon).toBeLessThan(-84.45);
        expect(lat).toBeGreaterThan(33.15);
        expect(lat).toBeLessThan(33.55);
        expect(props.lastSale.date).toBeNull();
        expect(props.lastSale.price).toBeNull();
        expect(props.lastSale.qualified).toBeNull();
        expect(props.tax.assessedValue).toBeNull();
        expect(props.appraiserUrl).toContain("AppID=704");
        if (props.ownerName) seenOwner = true;
        if (props.tax.marketValue != null) seenValue = true;
        if (props.jurisdictionCode === "NEWNAN") newnanCity += 1;
        if (props.zoningCode) {
          zoning += 1;
          expect(props.zoningDistrict).toBe(
            props.zoningDistrict?.startsWith("Newnan:") ? `Newnan:${props.zoningCode}` : `Coweta:${props.zoningCode}`,
          );
          if (props.zoningDistrict?.startsWith("Newnan:")) newnanZoning += 1;
          if (props.zoningDistrict?.startsWith("Coweta:")) cowetaZoning += 1;
        }
        if (props.flu?.code) {
          flu += 1;
          expect(props.flu.jurisdiction).toBe("Newnan");
          fluJurisdictions.add(props.flu.jurisdiction || "");
          expect(props.flu.label).toBe(props.flu.code);
        }
        if (props.jurisdictionCode && props.jurisdictionCode !== "NEWNAN" && props.jurisdictionCode !== "COUNTY") {
          expect(props.flu?.code ?? null).toBeNull();
          expect(props.zoningDistrict?.startsWith("Newnan:") ?? false).toBe(false);
        }
        checked += 1;
      }
    }
    expect(checked).toBe(county.featureCount);
    expect(seenOwner).toBe(true);
    expect(seenValue).toBe(true);
    expect(cowetaZoning).toBeGreaterThan(0);
    expect(newnanZoning).toBeGreaterThan(0);
    expect(flu).toBeGreaterThan(0);
    expect(newnanCity).toBeGreaterThan(0);
    expect(flu).toBeLessThan(checked);
    expect(zoning).toBeLessThan(checked);
    expect([...fluJurisdictions]).toEqual(["Newnan"]);
  });
});
