import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY_CHARACTER = new Set([
  "Suburban",
  "Neighborhood Residential",
  "Conservation",
  "Rural Residential and Agriculture",
  "Highway Corridor",
  "Employment Center",
  "Village Center",
]);

const FLU_JURISDICTIONS = new Set(["Walton County", "Monroe", "Loganville", "Social Circle", "Walnut Grove"]);

function loadWaltonFeatures(): { features: ParcelFeature[]; county: Record<string, unknown> } {
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13297/county.json");
  const county = JSON.parse(readFileSync(countyPath, "utf8")) as Record<string, unknown>;
  const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13297/tiles");
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(tileDir)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tileDir, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return { features, county };
}

describe("Walton County, Georgia parcel extract", () => {
  it("keeps a public 5–150 GIS-acre county extract and does not invent opportunity zones", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13297/county.json");
    expect(existsSync(countyPath)).toBe(true);
    const { features, county } = loadWaltonFeatures();
    const stats = county.stats as {
      sourceBandCount: number;
      kept: number;
      monroeCamaLayerCount: number;
      monroeCamaMatched: number;
      monroeOwnerFilled: number;
      monroeMarketValueFilled: number;
      downloadedRows: number;
      blankParcelRows: number;
      utilityRows: number;
      geometryDropped: number;
      outsideBand: number;
      outsideGeorgia: number;
      duplicateExtraRings: number;
      zoningMonroe: number;
      zoningLoganville: number;
      zoningSocialCircle: number;
      zoningMonroeCamaFallback: number;
      zoningUnmatched: number;
      fluCounty: number;
      fluMonroeCharacter: number;
      fluLoganville: number;
      fluSocialCircle: number;
      fluWalnutGrove: number;
      fluMissing: number;
    };

    expect(county.fips).toBe("13297");
    expect(county.state).toBe("Georgia");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("ga-walton-choosewalton-parcels");
    expect(county.featureCount).toBe(features.length);
    expect(stats.kept).toBe(features.length);
    expect(stats.sourceBandCount).toBeGreaterThan(6000);
    expect(features.length).toBeGreaterThan(5000);
    expect(stats.monroeCamaLayerCount).toBeGreaterThan(5000);
    expect(stats.downloadedRows).toBe(stats.sourceBandCount);
    expect(
      stats.blankParcelRows +
        stats.utilityRows +
        stats.geometryDropped +
        stats.outsideBand +
        stats.outsideGeorgia +
        stats.duplicateExtraRings +
        stats.kept,
    ).toBe(stats.downloadedRows);

    const gaps = (county.gaps as string[]).join(" ");
    expect(gaps).toContain("character area");
    expect(gaps).toContain("499/403");
    expect(gaps).toContain("qPublic");
    expect(gaps).toContain("Monroe City Parcels");
    expect(gaps).toContain("AppID=835");
    expect(gaps).not.toContain("inOpportunityZone");

    const ids = new Set<string>();
    let owners = 0;
    let marketValues = 0;
    let camaMatched = 0;
    const zoning = { MONROE: 0, LOGANVILLE: 0, SOCIALCIRCLE: 0, none: 0 };
    const flu = { county: 0, Monroe: 0, Loganville: 0, "Social Circle": 0, "Walnut Grove": 0, missing: 0 };

    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("13297");
      expect(props.state).toBe("Georgia");
      expect(props.marketIds).toEqual(["Atlanta"]);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.lastSale.price).toBeNull();
      expect(props.lastSale.date).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.tax.taxes).toBeNull();
      expect(ids.has(props.parcelId)).toBe(false);
      ids.add(props.parcelId);
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-84.05);
      expect(lon).toBeLessThan(-83.4);
      expect(lat).toBeGreaterThan(33.5);
      expect(lat).toBeLessThan(34.05);
      expect(COUNTY_CHARACTER.has(props.zoningCode ?? "")).toBe(false);
      expect(props.appraiserUrl ?? "").toContain("App=waltonCountyGA");
      expect(props.appraiserUrl ?? "").not.toContain("AppID=835");
      expect(props.appraiserUrl ?? "").toContain(encodeURIComponent(props.parcelId));
      if (props.ownerName) owners += 1;
      if (props.tax.marketValue != null) marketValues += 1;
      const matchedMonroe = (props.dataGaps ?? []).some((gap) => gap.includes("Monroe city CAMA only"));
      if (matchedMonroe) camaMatched += 1;
      if (!props.zoningCode) zoning.none += 1;
      else if (props.jurisdictionPrefix === "LOGANVILLE") zoning.LOGANVILLE += 1;
      else if (props.jurisdictionPrefix === "SOCIALCIRCLE") zoning.SOCIALCIRCLE += 1;
      else if (props.jurisdictionPrefix === "MONROE") zoning.MONROE += 1;
      else zoning.none += 1;

      const fluJurisdiction = props.flu?.jurisdiction ?? null;
      expect(fluJurisdiction == null || FLU_JURISDICTIONS.has(fluJurisdiction)).toBe(true);
      if (!props.flu?.code) flu.missing += 1;
      else if (fluJurisdiction === "Walton County") flu.county += 1;
      else if (fluJurisdiction === "Monroe") flu.Monroe += 1;
      else if (fluJurisdiction === "Loganville") flu.Loganville += 1;
      else if (fluJurisdiction === "Social Circle") flu["Social Circle"] += 1;
      else if (fluJurisdiction === "Walnut Grove") flu["Walnut Grove"] += 1;
    }

    expect(owners).toBe(stats.monroeOwnerFilled);
    expect(marketValues).toBe(stats.monroeMarketValueFilled);
    expect(camaMatched).toBe(stats.monroeCamaMatched);
    expect(camaMatched).toBeLessThan(features.length);
    expect(stats.monroeCamaMatched).toBeLessThan(stats.monroeCamaLayerCount);
    expect(zoning.MONROE + zoning.LOGANVILLE + zoning.SOCIALCIRCLE + zoning.none).toBe(features.length);
    expect(zoning.MONROE).toBe(stats.zoningMonroe + stats.zoningMonroeCamaFallback);
    expect(zoning.LOGANVILLE).toBe(stats.zoningLoganville);
    expect(zoning.SOCIALCIRCLE).toBe(stats.zoningSocialCircle);
    expect(zoning.none).toBe(stats.zoningUnmatched);
    expect(flu.county).toBe(stats.fluCounty);
    expect(flu.Monroe).toBe(stats.fluMonroeCharacter);
    expect(flu.Loganville).toBe(stats.fluLoganville);
    expect(flu["Social Circle"]).toBe(stats.fluSocialCircle);
    expect(flu["Walnut Grove"]).toBe(stats.fluWalnutGrove);
    expect(flu.missing).toBe(stats.fluMissing);
    expect(flu.county + flu.Monroe + flu.Loganville + flu["Social Circle"] + flu["Walnut Grove"] + flu.missing).toBe(
      features.length,
    );
  });

  it("links Walton parcels to the Georgia qPublic app, not Orange County or Walton Florida", () => {
    const linked = parcelAppraiserUrl({
      parcelId: "C0920002",
      countyFips: "13297",
      appraiserUrl:
        "https://qpublic.schneidercorp.com/Application.aspx?App=waltonCountyGA&Layer=Parcels&PageType=Report&KeyValue=C0920002",
    });
    expect(linked.href).toContain("App=waltonCountyGA");
    expect(linked.href).not.toContain("ocpa");
    expect(linked.href).not.toContain("835");
    expect(linked.label).toContain("Walton");

    const fallback = parcelAppraiserUrl({ parcelId: "C0920002", countyFips: "13297" });
    expect(fallback.href).toContain("App=waltonCountyGA");
    expect(fallback.label).toContain("Walton");
  });
});
