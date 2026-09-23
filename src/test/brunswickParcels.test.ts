import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { findFluCategory } from "../lib/flu";
import { inMarketAcreageBand } from "../lib/marketParcels";
import { parcelAppraiserUrl } from "../lib/format";
import { findZoningHit } from "../lib/zoning";
import type { FluConfig, ParcelCollection, ParcelFeature, ZoningConfig } from "../lib/types";

const zoningConfig = JSON.parse(readFileSync(path.join(process.cwd(), "data/zoning-config.json"), "utf8")) as ZoningConfig;
const fluConfig = JSON.parse(readFileSync(path.join(process.cwd(), "data/flu-config.json"), "utf8")) as FluConfig;
const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37019/county.json");

function loadBrunswick(): { features: ParcelFeature[]; county: Record<string, unknown> } {
  const county = JSON.parse(readFileSync(countyPath, "utf8")) as Record<string, unknown>;
  const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37019/tiles");
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(tileDir)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tileDir, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return { features, county };
}

describe("Brunswick County NC parcels", () => {
  it("opens the Brunswick tax card instead of the Orange County appraiser", () => {
    const link = parcelAppraiserUrl({
      parcelId: "2140005702",
      countyFips: "37019",
      appraiserUrl: "https://tax.brunsco.net/ITSNet/AppraisalCard.aspx?parcel=2140005702",
    });
    expect(link.href).toContain("tax.brunsco.net");
    expect(link.href).not.toContain("ocpafl.org");
    expect(link.label).toBe("Open Brunswick County tax card");
  });

  it("keeps the 5–150 acre county extract honest about price, zoning, and opportunity zones", () => {
    const { features, county } = loadBrunswick();
    expect(county.fips).toBe("37019");
    expect(county.state).toBe("North Carolina");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("bcgis-seamless-37019");
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    expect(county.featureCount).toBe(features.length);
    expect(features.length).toBeGreaterThan(7000);
    const gaps = county.gaps as string[];
    expect(gaps.some((gap) => /sale price/i.test(gap) && /DeedDate/i.test(gap))).toBe(true);
    expect(gaps.some((gap) => /not designated/i.test(gap))).toBe(true);
    expect(gaps.some((gap) => /MuniZoning/i.test(gap))).toBe(true);

    const lookup = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/fixtures/market-parcels/counties/37019/lookup.json"), "utf8"),
    ) as Record<string, string>;
    expect(Object.keys(lookup)).toHaveLength(features.length);

    let municipal = 0;
    let eligible = 0;
    let designated = 0;
    let eligibleAndDesignated = 0;
    let flu = 0;
    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("37019");
      expect(props.state).toBe("North Carolina");
      expect(props.marketIds).toEqual(["Wilmington"]);
      expect(props.lastSale.price).toBeNull();
      expect(props.lastSale.qualified).toBeNull();
      expect(props.tax.taxes).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      if (props.lastSale.date) expect(props.lastSale.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(props.dataGaps?.some((gap) => /DeedDate/i.test(gap))).toBe(true);
      expect(props.appraiserUrl || "").toContain("tax.brunsco.net");
      expect(lookup[props.parcelId]).toBeTruthy();

      expect(findZoningHit(props.zoningCode, props.zoningDistrict, zoningConfig)).toBeNull();
      if (props.flu) {
        flu += 1;
        expect(findFluCategory(props.flu, fluConfig)).toBeNull();
        expect(props.flu.jurisdiction).toBe("Brunswick County");
      }

      const oz = props.opportunityZone;
      const oz2 = props.oz2Eligibility;
      expect(oz?.source).toBe("hud-fs-13");
      expect(oz2?.source).toBe("rev-proc-2026-14");
      expect(typeof oz?.inOpportunityZone).toBe("boolean");
      if (oz?.inOpportunityZone) designated += 1;
      if (oz2?.eligible) {
        eligible += 1;
        expect(oz2.designation).toBe("eligible-for-nomination");
        expect(oz2.designation).not.toBe("designated");
      } else {
        expect(oz2?.designation).toBe("not-eligible");
        expect(oz2?.eligible).toBe(false);
      }
      if (oz?.inOpportunityZone && oz2?.eligible) eligibleAndDesignated += 1;
      if (props.jurisdictionCode && props.jurisdictionCode !== "Brunswick County" && props.zoningCode?.includes("-")) {
        municipal += 1;
      }
    }

    expect(municipal).toBeGreaterThan(0);
    expect(flu).toBeGreaterThan(0);
    expect(eligible).toBeGreaterThan(0);
    expect(designated).toBe(county.designatedOzCount);
    expect(eligible).toBe(county.oz2EligibleCount);
    expect(eligibleAndDesignated).toBe(county.eligibleAlsoDesignatedCount);
    expect(flu).toBe(county.fluJoinedCount);
  });
});
