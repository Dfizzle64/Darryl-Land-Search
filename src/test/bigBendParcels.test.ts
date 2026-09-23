import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { leonParcelUrl, parcelAppraiserUrl } from "../lib/format";
import { ELIGIBLE_NOT_DESIGNATED_STATUS } from "../lib/types";

describe("Leon property appraiser link", () => {
  it("opens the TAXID record and does not call the tract designated", () => {
    const href = leonParcelUrl("2612204050000");
    expect(href).toBe("https://search.leonpa.gov/Property/Details/2612204050000");
    expect(href).not.toMatch(/designated/i);
    const linked = parcelAppraiserUrl({
      parcelId: "2612204050000",
      countyFips: "12073",
      appraiserUrl: href,
    });
    expect(linked.href).toBe(href);
    expect(linked.label).toBe("Open Leon County Property Appraiser");
    expect(linked.label).not.toMatch(/^designated/i);
  });
});

describe("Big Bend parcel fixtures", () => {
  it("keeps Leon usable, three counties partial, and three counties as gaps", () => {
    const index = JSON.parse(readFileSync("data/fixtures/market-parcels/index.json", "utf8")) as {
      markets: Record<
        string,
        {
          parcelCount: number;
          completeCountyCount: number;
          sampleCountyCount: number;
          gapCountyCount: number;
          counties: Array<{ name: string; fips: string; coverage: string; featureCount: number; gaps?: string[] }>;
        }
      >;
    };
    const market = index.markets["Big Bend"];
    expect(market).toBeTruthy();
    expect(market.completeCountyCount).toBe(1);
    expect(market.sampleCountyCount).toBe(3);
    expect(market.gapCountyCount).toBe(3);
    expect(market.parcelCount).toBeGreaterThan(0);
    const byName = Object.fromEntries(market.counties.map((county) => [county.name, county]));
    expect(byName.Leon.coverage).toBe("complete-gte-5ac");
    expect(byName.Leon.fips).toBe("12073");
    expect(byName.Leon.featureCount).toBeGreaterThan(1000);
    expect(byName.Leon.gaps?.join(" ")).toMatch(/TLC_OverlayParcel_D_WM/);
    expect(byName.Leon.gaps?.join(" ")).toMatch(/not designated/i);
    expect(byName.Leon.gaps?.join(" ")).not.toMatch(/^designated/i);
    for (const name of ["Wakulla", "Jefferson", "Gadsden"]) {
      expect(byName[name].coverage).toBe("sample");
      expect(byName[name].featureCount).toBeGreaterThan(0);
      expect(byName[name].gaps?.join(" ")).toMatch(/Partial/);
    }
    expect(byName.Gadsden.gaps?.join(" ")).toMatch(/Quincy/);
    expect(byName.Gadsden.gaps?.join(" ")).toMatch(/PDF/);
    for (const name of ["Madison", "Taylor", "Dixie"]) {
      expect(byName[name].coverage).toBe("gap");
      expect(byName[name].featureCount).toBe(0);
      expect(byName[name].gaps?.join(" ")).toMatch(/not designated/i);
    }
    const leon = JSON.parse(readFileSync("data/fixtures/market-parcels/counties/12073/county.json", "utf8")) as {
      source: string;
      queryUrl: string;
    };
    expect(leon.source).toBe("fl-leon-overlay-parcel-12073");
    expect(leon.queryUrl).toMatch(/TLC_OverlayParcel_D_WM\/MapServer\/0/);
    const tile = JSON.parse(
      readFileSync("data/fixtures/market-parcels/counties/12073/tiles/" + firstLeonTile(), "utf8"),
    ) as { features: Array<{ properties: { acreage: number; appraiserUrl: string; marketIds: string[] } }> };
    const parcel = tile.features[0].properties;
    expect(parcel.acreage).toBeGreaterThanOrEqual(5);
    expect(parcel.acreage).toBeLessThanOrEqual(150);
    expect(parcel.appraiserUrl).toMatch(/^https:\/\/search\.leonpa\.gov\/Property\/Details\//);
    expect(parcel.marketIds).toContain("Big Bend");
    expect(parcel.marketIds).not.toContain("Orlando");
    expect(ELIGIBLE_NOT_DESIGNATED_STATUS).toBe("Eligible — not designated");
  });
});

function firstLeonTile(): string {
  const lookup = JSON.parse(readFileSync("data/fixtures/market-parcels/counties/12073/lookup.json", "utf8")) as Record<
    string,
    string
  >;
  const tile = Object.values(lookup)[0];
  return `${tile}.geojson`;
}
