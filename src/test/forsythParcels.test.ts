import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37067/county.json");

type ForsythCounty = {
  fips: string;
  state: string;
  source: string;
  featureCount: number;
  coverage: string;
  queryUrl: string;
  gaps: string[];
  municipalities?: Array<{
    name: string;
    code?: string;
    independentGis: boolean;
    zoningUrl?: string | null;
    fluUrl?: string | null;
    fluGap?: string | null;
    zoningJoined?: number;
    fluJoined?: number;
  }>;
  unincorporated?: { zoningJoined?: number; fluJoined?: number; note?: string };
  zoningJoinedCount?: number;
  fluJoinedCount?: number;
  salesFilledCount?: number;
  oneMapValueCount?: number;
  rejectedLookalikes?: string[];
  path?: string;
};

describe("Forsyth County NC parcels", () => {
  it("opens NCPTS for a MapForsyth parcel and not a Georgia appraiser", () => {
    const link = parcelAppraiserUrl({
      parcelId: "6836-42-3032.00",
      countyFips: "37067",
      appraiserUrl: "https://lrcpwa.ncptscloud.com/forsyth/parcel-detail/1541",
    });
    expect(link.label).toContain("Forsyth");
    expect(link.href).toContain("ncptscloud.com/forsyth/parcel-detail/1541");
    expect(link.href.toLowerCase()).not.toContain("cumming");
    expect(link.href).not.toContain("13117");
  });

  it("ships MapForsyth 5–150 acre parcels with municipal zoning and documented gaps", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as ForsythCounty;
    expect(county.fips).toBe("37067");
    expect(county.state).toBe("North Carolina");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("nc-mapforsyth-37067");
    expect(county.queryUrl).toContain("Parcels_Hosted/FeatureServer/0");
    expect(county.queryUrl.toLowerCase()).not.toContain("cumming");
    expect(county.featureCount).toBeGreaterThan(7000);
    expect(county.featureCount).toBeLessThan(9000);
    const gapText = county.gaps.join(" ");
    expect(gapText).toMatch(/land\/building split/i);
    expect(gapText).toMatch(/SalesApp/i);
    expect(gapText).toMatch(/Clemmons/);
    expect(gapText).toMatch(/High Point/);
    expect(gapText).toMatch(/Kernersville/);
    expect(gapText).toMatch(/Georgia/);
    expect(county.rejectedLookalikes?.join(" ")).toMatch(/13117/);

    const winston = county.municipalities?.find((item) => item.name === "Winston-Salem");
    expect(winston?.independentGis).toBe(false);
    expect(winston?.zoningUrl).toContain("Zoning_Hosted");
    expect(winston?.fluUrl).toContain("LandUse_PotentialResidentialGrowth");
    expect(winston?.zoningJoined ?? 0).toBeGreaterThan(0);

    const kernersville = county.municipalities?.find((item) => item.name === "Kernersville");
    expect(kernersville?.independentGis).toBe(true);
    expect(kernersville?.zoningUrl).toContain("gis.toknc.com");
    expect(kernersville?.fluUrl).toContain("Land_Use_Plan");

    const clemmons = county.municipalities?.find((item) => item.name === "Clemmons");
    expect(clemmons?.fluUrl ?? null).toBeNull();
    expect(clemmons?.fluGap ?? "").toMatch(/Clemmons/);

    for (const name of ["Lewisville", "Walkertown", "Rural Hall", "Tobaccoville", "Bethania"]) {
      const town = county.municipalities?.find((item) => item.name === name);
      expect(town?.fluUrl ?? null).toBeNull();
      expect(town?.fluGap ?? "").toMatch(/No dedicated/i);
    }

    const highPoint = county.municipalities?.find((item) => item.name === "High Point");
    expect(highPoint?.independentGis).toBe(true);
    expect(highPoint?.zoningUrl).toContain("highpointnc.gov");
    expect(highPoint?.fluUrl).toContain("Planning/MapServer/29");

    expect(county.unincorporated?.note ?? "").toMatch(/FC/);
    expect(county.zoningJoinedCount ?? 0).toBeGreaterThan(1000);
    expect(county.fluJoinedCount ?? 0).toBeGreaterThan(0);

    const tiles = path.join(process.cwd(), county.path ?? "");
    const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
    expect(file).toBeTruthy();
    const collection = JSON.parse(readFileSync(path.join(tiles, file as string), "utf8")) as ParcelCollection;
    expect(collection.features.length).toBeGreaterThan(0);
    let sawOwner = false;
    let sawAssessed = false;
    let sawNcpts = false;
    for (const feature of collection.features.slice(0, 40)) {
      const props = feature.properties;
      expect(props.countyFips).toBe("37067");
      expect(props.state).toBe("North Carolina");
      expect(props.source).toBe("nc-mapforsyth-37067");
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.tax.marketValue).toBeNull();
      expect(props.appraiserUrl ?? "").toContain("ncptscloud.com/forsyth");
      expect(props.appraiserUrl ?? "").not.toContain("13117");
      if (props.ownerName) sawOwner = true;
      if (props.tax.assessedValue) sawAssessed = true;
      if ((props.appraiserUrl ?? "").includes("parcel-detail")) sawNcpts = true;
    }
    expect(sawOwner).toBe(true);
    expect(sawAssessed).toBe(true);
    expect(sawNcpts).toBe(true);
  });
});
