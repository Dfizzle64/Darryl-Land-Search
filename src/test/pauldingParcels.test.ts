import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13223");
const PAULDING_SEARCH =
  "https://qpublic.schneidercorp.com/Application.aspx?App=PauldingCountyGA&Layer=Parcels&PageType=Search";

describe("Paulding County GA parcels", () => {
  it("opens the Paulding qPublic search instead of Orange County", () => {
    expect(parcelAppraiserUrl({ parcelId: "208.1.1.005.0000", countyFips: "13223" })).toEqual({
      href: PAULDING_SEARCH,
      label: "Open in Paulding County qPublic",
    });
    expect(parcelAppraiserUrl({ parcelId: "208.1.1.005.0000", countyFips: "13223" }).href).not.toContain("ocpafl.org");
  });

  it("keeps DeedAc 5–150 acre parcels inside Paulding, Georgia", () => {
    const countyPath = path.join(COUNTY, "county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      featureCount: number;
      coverage: string;
      source: string;
      queryUrl: string;
      gaps: string[];
      markets: string[];
    };
    expect(county.fips).toBe("13223");
    expect(county.markets).toContain("Atlanta");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("ga-paulding-parcels");
    expect(county.queryUrl).toContain("Paulding_Map_Auto_Updated_WFL3/FeatureServer/25");
    expect(county.featureCount).toBeGreaterThan(4500);
    expect(county.featureCount).toBeLessThan(5600);
    const gapText = county.gaps.join("\n");
    expect(gapText).toMatch(/DeedAc/);
    expect(gapText).toMatch(/CalcAc/);
    expect(gapText).toMatch(/qPublic/);
    expect(gapText).toMatch(/Hiram/);
    expect(gapText).toMatch(/Braswell/);
    expect(gapText).toMatch(/Paulding, Ohio is rejected/);

    const tileDir = path.join(COUNTY, "tiles");
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let zoning = 0;
    let dallas = 0;
    let dallasFlu = 0;
    let hiramOrBraswell = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        seen += 1;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("13223");
        expect(props.marketIds).toContain("Atlanta");
        expect(props.marketIds?.includes("Orlando")).toBe(false);
        expect(props.state).toBe("Georgia");
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-85.2);
        expect(lon).toBeLessThan(-84.55);
        expect(lat).toBeGreaterThan(33.65);
        expect(lat).toBeLessThan(34.2);
        expect(props.ownerName).toBeNull();
        expect(props.tax.marketValue).toBeNull();
        expect(props.tax.assessedValue).toBeNull();
        expect(props.tax.taxableValue).toBeNull();
        expect(props.lastSale.price).toBeNull();
        expect(props.lastSale.date).toBeNull();
        expect(props.appraiserUrl).toBe(PAULDING_SEARCH);
        expect(props.dataGaps?.join(" ")).toMatch(/qPublic was not scraped/);
        if (props.zoningCode) zoning += 1;
        if (props.jurisdictionCode === "Dallas") {
          dallas += 1;
          if (props.flu) {
            dallasFlu += 1;
            expect(props.flu.jurisdiction).toBe("Dallas");
            expect(props.flu.source).toBe("dallas-flu-2017");
          }
        }
        if (props.jurisdictionCode === "Hiram" || props.jurisdictionCode === "Braswell") {
          hiramOrBraswell += 1;
          expect(props.flu).toBeNull();
        }
      }
    }
    expect(seen).toBe(county.featureCount);
    expect(zoning).toBeGreaterThan(seen * 0.8);
    expect(dallas).toBeGreaterThan(0);
    expect(dallasFlu).toBeGreaterThan(0);
    expect(hiramOrBraswell).toBeGreaterThan(0);
  });
});
