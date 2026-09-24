import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13045");

function load(): { features: ParcelFeature[]; county: Record<string, unknown> } {
  const county = JSON.parse(readFileSync(path.join(COUNTY, "county.json"), "utf8")) as Record<string, unknown>;
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(path.join(COUNTY, "tiles"))) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(COUNTY, "tiles", name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return { features, county };
}

describe("Carroll County, Georgia parcel extract", () => {
  it("keeps the OpenAddresses 5–150 acre landbase and does not invent opportunity zones", () => {
    const { features, county } = load();
    const stats = county.stats as {
      sourceRows: number;
      kept: number;
      ownerFilled: number;
      marketValueFilled: number;
      carrolltonZoning: number;
      villaRicaZoning: number;
      zoningUnmatched: number;
      commercialSales: number;
      carrolltonFlu: number;
      villaRicaFlu: number;
    };
    expect(county.fips).toBe("13045");
    expect(county.state).toBe("Georgia");
    expect(county.source).toBe("oa-carroll-ga-910028");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBe(features.length);
    expect(stats.kept).toBe(features.length);
    expect(stats.sourceRows).toBe(55412);
    expect(features.length).toBeGreaterThan(8000);
    expect(features.length).toBeLessThan(11000);

    const gaps = (county.gaps as string[]).join(" ");
    expect(gaps).toContain("910028");
    expect(gaps).toContain("blocked");
    expect(gaps).toContain("PDF");
    expect(gaps).toContain("commercial/industrial");
    expect(gaps).toContain("Temple");
    expect(gaps).toContain("Maryland");
    expect(gaps).toContain("LandPro");
    expect(gaps).not.toMatch(/designated Opportunity Zone/i);

    const ids = new Set<string>();
    let owners = 0;
    let zoned = 0;
    let sales = 0;
    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("13045");
      expect(props.state).toBe("Georgia");
      expect(props.marketIds).toEqual(["Atlanta"]);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.source).toBe("oa-carroll-ga-910028");
      expect(props.appraiserUrl ?? "").toContain("AppID=663");
      expect(props.appraiserUrl ?? "").toContain("LayerID=15076");
      expect(props.appraiserUrl ?? "").not.toContain("LandPro");
      expect(props.appraiserUrl ?? "").not.toContain("ocpa");
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-85.34);
      expect(lon).toBeLessThan(-84.8);
      expect(lat).toBeGreaterThan(33.42);
      expect(lat).toBeLessThan(33.82);
      expect(JSON.stringify(props)).not.toMatch(/FAXNUMBER/i);
      expect(ids.has(props.parcelId)).toBe(false);
      ids.add(props.parcelId);
      if (props.ownerName) owners += 1;
      if (props.zoningCode) zoned += 1;
      if (props.lastSale.price != null || props.lastSale.date) sales += 1;
    }
    expect(owners).toBe(stats.ownerFilled);
    expect(owners).toBeLessThan(features.length * 0.15);
    expect(stats.marketValueFilled).toBeLessThan(features.length * 0.15);
    expect(zoned).toBe(stats.carrolltonZoning + stats.villaRicaZoning);
    expect(stats.zoningUnmatched).toBeGreaterThan(zoned);
    expect(sales).toBe(stats.commercialSales);
    expect(sales).toBeLessThan(features.length * 0.05);
    expect(stats.carrolltonFlu + stats.villaRicaFlu).toBeLessThan(features.length * 0.1);
  });

  it("links Carroll parcels to Georgia qPublic, not Orange County or another Carroll County", () => {
    const linked = parcelAppraiserUrl({
      parcelId: "C06 0230101",
      countyFips: "13045",
      appraiserUrl:
        "https://qpublic.schneidercorp.com/Application.aspx?AppID=663&LayerID=15076&PageTypeID=4&KeyValue=C06%200230101",
    });
    expect(linked.href).toContain("AppID=663");
    expect(linked.href).toContain("LayerID=15076");
    expect(linked.href).not.toContain("ocpa");
    expect(linked.href).not.toContain("LandPro");
    expect(linked.label).toContain("Carroll");

    const fallback = parcelAppraiserUrl({ parcelId: "C06 0230101", countyFips: "13045" });
    expect(fallback.href).toContain("AppID=663");
    expect(fallback.label).toContain("Carroll");
  });
});
