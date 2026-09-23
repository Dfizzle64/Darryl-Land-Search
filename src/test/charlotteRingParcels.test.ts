import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import { parcelAppraiserUrl } from "../lib/format";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const ROOT = path.join(process.cwd(), "data/fixtures/market-parcels/counties");

const COUNTIES = [
  {
    fips: "37179",
    source: "nc-union-atlas-37179",
    host: "unionnc.devnetwedge.com/parcel/view/",
    gap: "Hemby Bridge",
    label: "Union",
  },
  {
    fips: "37071",
    source: "nc-gaston-publicgis-37071",
    host: "gastonnc.devnetwedge.com/parcel/view/",
    gap: "High Shoals",
    label: "Gaston",
  },
  {
    fips: "37025",
    source: "nc-cabarrus-tax-parcels-37025",
    host: "tax.cabarruscounty.us",
    gap: "Situs is not on Tax_Parcels",
    label: "Cabarrus",
  },
  {
    fips: "37159",
    source: "nc-rowan-open-data-37159",
    host: "tax.rowancountync.gov",
    gap: "Salisbury",
    label: "Rowan",
  },
  {
    fips: "37109",
    source: "nc-lincoln-operational-37109",
    host: "taxparcelviewer/PropertyReport.aspx?akpar=",
    gap: "Maiden",
    label: "Lincoln",
  },
  {
    fips: "37007",
    source: "nc-anson-vector-37007",
    host: "bttaxpayerportal.com",
    gap: "Peachland",
    label: "Anson",
  },
] as const;

function featuresFor(fips: string): ParcelFeature[] {
  const tiles = path.join(ROOT, fips, "tiles");
  const rows: ParcelFeature[] = [];
  for (const name of readdirSync(tiles)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
    rows.push(...collection.features);
  }
  return rows;
}

describe("Charlotte ring county extracts", () => {
  it("names the six county appraisers", () => {
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "37179" }).label).toContain("Union");
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "37071" }).label).toContain("Gaston");
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "37025" }).label).toContain("Cabarrus");
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "37159" }).label).toContain("Rowan");
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "37109" }).label).toContain("Lincoln");
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "37007" }).label).toContain("Anson");
  });

  for (const county of COUNTIES) {
    it(`keeps ${county.label} 5–150 acre parcels with owner, appraiser, and town zoning`, () => {
      const metaPath = path.join(ROOT, county.fips, "county.json");
      expect(existsSync(metaPath)).toBe(true);
      const meta = JSON.parse(readFileSync(metaPath, "utf8")) as {
        source: string;
        featureCount: number;
        coverage: string;
        gaps: string[];
      };
      expect(meta.source).toBe(county.source);
      expect(meta.coverage).toBe("complete-gte-5ac");
      expect(meta.featureCount).toBeGreaterThan(4000);
      expect(meta.gaps.join(" ")).toContain(county.gap);
      expect(meta.gaps.join(" ").toLowerCase()).toContain("land use");

      const features = featuresFor(county.fips);
      expect(features.length).toBe(meta.featureCount);
      let owners = 0;
      let zoning = 0;
      let flu = 0;
      let situs = 0;
      for (const feature of features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe(county.fips);
        expect(props.source).toBe(county.source);
        expect(props.appraiserUrl || "").toContain(county.host);
        expect(props.marketIds).toContain("Charlotte");
        const code = (props.zoningCode || "").toUpperCase();
        expect(code === "CITY" || code === "MUN." || code === "MUN").toBe(false);
        if (props.ownerName) owners += 1;
        if (props.zoningCode) zoning += 1;
        if (props.flu?.code) flu += 1;
        if (props.situsAddress) situs += 1;
      }
      expect(owners / features.length).toBeGreaterThan(0.7);
      expect(zoning / features.length).toBeGreaterThan(0.45);
      if (county.fips === "37025") expect(situs / features.length).toBeGreaterThan(0.4);
      if (county.fips === "37109" || county.fips === "37007") expect(flu).toBeGreaterThan(50);
      if (county.fips === "37025" || county.fips === "37159") expect(flu).toBeGreaterThan(0);
      if (county.fips === "37179" || county.fips === "37071") expect(flu).toBe(0);
    });
  }
});
