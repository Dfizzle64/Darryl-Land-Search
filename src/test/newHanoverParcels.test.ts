import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37129/county.json");

type NewHanoverCounty = {
  fips: string;
  source: string;
  featureCount: number;
  coverage: string;
  queryUrl: string;
  gaps: string[];
  municipalities?: Array<{
    name: string;
    independentGis: boolean;
    zoningUrl?: string | null;
    fluUrl?: string | null;
    fluGap?: string | null;
    zoningJoined?: number;
    fluJoined?: number;
  }>;
  unincorporated?: { fluUrl?: string | null; fluJoined?: number; note?: string };
  zoningJoinedCount?: number;
  fluJoinedCount?: number;
  oz2EligibleCount?: number;
  designatedOzCount?: number;
  path?: string;
};

describe("New Hanover County parcels", () => {
  it("opens the county property search instead of a Florida appraiser", () => {
    const link = parcelAppraiserUrl({
      parcelId: "3242-35-3445.000",
      countyFips: "37129",
      appraiserUrl: "https://etax.nhcgov.com/pt/main/home.aspx",
    });
    expect(link.label).toContain("New Hanover");
    expect(link.href).toContain("etax.nhcgov.com");
    expect(link.href).not.toContain("ocpafl.org");
  });

  it("ships county parcels with city-first zoning and honest gaps", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as NewHanoverCounty;
    expect(county.fips).toBe("37129");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("nc-new-hanover-parcels-37129");
    expect(county.queryUrl).toContain("Layers/Parcels/FeatureServer/0");
    expect(county.featureCount).toBeGreaterThan(1800);
    expect(county.featureCount).toBeLessThan(2800);
    const gapText = county.gaps.join(" ");
    expect(gapText).toMatch(/Create Wilmington/i);
    expect(gapText).toMatch(/Kure Beach zoning polygons/i);
    expect(gapText).toMatch(/cntyfips='129'/);
    expect(gapText).toMatch(/Eligible is not designated/i);
    expect(gapText).toMatch(/MAPIDKEY/);

    const wilmington = county.municipalities?.find((item) => item.name === "Wilmington");
    expect(wilmington?.independentGis).toBe(true);
    expect(wilmington?.zoningUrl).toContain("gis.wilmingtonnc.gov");
    expect(wilmington?.fluUrl ?? null).toBeNull();
    expect(wilmington?.fluGap ?? "").toMatch(/no feature service/i);
    expect(wilmington?.zoningJoined ?? 0).toBeGreaterThan(0);
    expect(wilmington?.fluJoined ?? 0).toBe(0);

    const carolina = county.municipalities?.find((item) => item.name === "Carolina Beach");
    expect(carolina?.zoningUrl).toContain("GIS_Viewer/MapServer/21");
    expect(carolina?.fluUrl ?? null).toBeNull();

    const wrightsville = county.municipalities?.find((item) => item.name === "Wrightsville Beach");
    expect(wrightsville?.zoningUrl).toContain("WrightsvilleBeachZoning");
    expect(wrightsville?.fluUrl ?? null).toBeNull();

    const kure = county.municipalities?.find((item) => item.name === "Kure Beach");
    expect(kure?.zoningUrl ?? null).toBeNull();
    expect(kure?.zoningJoined ?? 0).toBe(0);
    expect(kure?.fluGap ?? "").toMatch(/Kure Beach/i);

    expect(county.unincorporated?.fluUrl).toContain("PlanNHC_FLUM/MapServer/8");
    expect(county.unincorporated?.fluJoined ?? 0).toBeGreaterThan(0);
    expect(county.zoningJoinedCount ?? 0).toBeGreaterThan(0);
    expect(county.fluJoinedCount ?? 0).toBeGreaterThan(0);
    expect(county.oz2EligibleCount ?? 0).toBeGreaterThan(0);
    expect((county.designatedOzCount ?? 0) >= 0).toBe(true);

    const tiles = path.join(process.cwd(), county.path ?? "");
    const files = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let sawOwner = false;
    let sawAssessed = false;
    let sawCityZoning = false;
    let sawPlaceType = false;
    let sawEligibleNotDesignated = false;
    let checked = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(props.countyFips).toBe("37129");
        expect(props.state).toBe("North Carolina");
        expect(props.source).toBe("nc-new-hanover-parcels-37129");
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.tax.marketValue).toBeNull();
        expect(props.tax.taxes).toBeNull();
        expect(props.appraiserUrl).toContain("etax.nhcgov.com");
        if (props.jurisdictionPrefix === "Wilmington") {
          expect(props.flu).toBeNull();
          expect(props.dataGaps?.join(" ")).toMatch(/Create Wilmington/i);
          if (props.zoningCode) sawCityZoning = true;
        }
        if (props.jurisdictionCode === "KB") {
          expect(props.zoningCode).toBeNull();
          expect(props.dataGaps?.join(" ")).toMatch(/Kure Beach zoning polygons/i);
        }
        if (props.oz2Eligibility?.eligible) {
          expect(props.oz2Eligibility.designation).toBe("eligible-for-nomination");
          if (props.opportunityZone && props.opportunityZone.inOpportunityZone === false) {
            sawEligibleNotDesignated = true;
          }
        }
        if (props.ownerName) sawOwner = true;
        if (props.tax.assessedValue) sawAssessed = true;
        if (props.flu?.source === "plan-nhc-flum-8") sawPlaceType = true;
        checked += 1;
        if (checked >= 400 && sawOwner && sawAssessed && sawCityZoning && sawPlaceType && sawEligibleNotDesignated) {
          break;
        }
      }
    }
    expect(sawOwner).toBe(true);
    expect(sawAssessed).toBe(true);
    expect(sawCityZoning).toBe(true);
    expect(sawPlaceType).toBe(true);
    expect(sawEligibleNotDesignated).toBe(true);
  });
});
