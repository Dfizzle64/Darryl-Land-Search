import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { filterEligibleRows, isOtherMarketId, isPrimaryMarket } from "../lib/markets";
import { ELIGIBLE_NOT_DESIGNATED_STATUS, type EligibleMarketsCatalog } from "../lib/types";
import type { MarketParcelIndex } from "../lib/marketParcels";

type MunicipalityCatalog = {
  market: string;
  eligibleStatus: string;
  rejected: { id: string; url?: string; reason: string }[];
  municipalities: { name: string; county: string; role: string; parcelSource: string; municode?: string }[];
};

function loadMunicipalities(): MunicipalityCatalog {
  return JSON.parse(readFileSync("data/swfl-municipalities.json", "utf8")) as MunicipalityCatalog;
}

describe("SWFL public GIS boundaries", () => {
  const catalog = loadMunicipalities();

  it("keeps municipalities first-class and does not use rejected sources", () => {
    expect(catalog.market).toBe("SWFL");
    expect(catalog.eligibleStatus).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
    expect(catalog.rejected.map((item) => item.id).sort()).toEqual(["eagleview-lee-republish", "fgdl-zoning"]);
    const names = catalog.municipalities.map((item) => item.name);
    expect(names).toEqual(
      expect.arrayContaining([
        "Cape Coral",
        "Fort Myers",
        "Bonita Springs",
        "Estero",
        "Fort Myers Beach",
        "Sanibel",
        "Naples",
        "Marco Island",
        "Everglades City",
        "Punta Gorda",
      ]),
    );
    expect(catalog.municipalities.find((item) => item.name === "Fort Myers")?.role).toBe("county-fallback");
    expect(catalog.municipalities.filter((item) => item.role === "county-stub").map((item) => item.name).sort()).toEqual([
      "Bonita Springs",
      "Estero",
      "Fort Myers Beach",
    ]);
    expect(catalog.municipalities.find((item) => item.name === "Sanibel")?.role).toBe("zoning-gap");
    expect(catalog.municipalities.find((item) => item.name === "Punta Gorda")?.role).toBe("partial");
    const sources = catalog.municipalities.map((item) => item.parcelSource).join(" ");
    expect(sources).not.toMatch(/eagleview|fgdl/i);
    expect(JSON.stringify(catalog.rejected).toLowerCase()).not.toMatch(/designated qoz/);
  });

  it("documents Collier sales, Sanibel zoning, Fort Myers TLS, and the county stubs on the parcel rows", () => {
    const lee = JSON.parse(readFileSync("data/fixtures/market-parcels/counties/12071/county.json", "utf8")) as {
      source: string;
      queryUrl: string;
      gaps: string[];
      coverage: string;
    };
    const collier = JSON.parse(readFileSync("data/fixtures/market-parcels/counties/12021/county.json", "utf8")) as {
      source: string;
      queryUrl: string;
      gaps: string[];
    };
    const charlotte = JSON.parse(readFileSync("data/fixtures/market-parcels/counties/12015/county.json", "utf8")) as {
      source: string;
      gaps: string[];
      markets: string[];
    };
    const sarasota = JSON.parse(readFileSync("data/fixtures/market-parcels/counties/12115/county.json", "utf8")) as {
      markets: string[];
      gaps: string[];
      source: string;
    };
    expect(lee.source).toBe("fl-lee-parceladdress");
    expect(lee.coverage).toBe("complete-gte-5ac");
    expect(lee.queryUrl).not.toMatch(/eagleview|fgdl/i);
    expect(lee.gaps.join(" ")).toMatch(/Fort Myers native GIS/);
    expect(lee.gaps.join(" ")).toMatch(/TLS-blocked/);
    expect(lee.gaps.join(" ")).toMatch(/Bonita Springs, Estero, and Fort Myers Beach/);
    expect(lee.gaps.join(" ")).toMatch(/Sanibel zoning/);
    expect(lee.gaps.join(" ")).toMatch(/EagleView/);
    expect(collier.source).toBe("fl-collier-parceljoin");
    expect(collier.queryUrl).toMatch(/Parcels\/FeatureServer\/42/);
    expect(collier.gaps.join(" ")).toMatch(/sales are not on the ParcelJoin/);
    expect(collier.gaps.join(" ")).not.toMatch(/eagleview|fgdl\.org/i);
    expect(charlotte.markets).toContain("SWFL");
    expect(charlotte.gaps.join(" ")).toMatch(/Partial SWFL county/);
    expect(charlotte.source).toBe("fl-doh-ehwaters-12015");
    expect(sarasota.markets).toEqual(["Tampa", "SWFL"]);
    expect(sarasota.source).toBe("fl-doh-ehwaters-12115");
    expect(sarasota.gaps.join(" ")).toMatch(/Optional SWFL county/);
  });

  it("serves SWFL parcels from the market index and keeps eligible tracts undesignated", () => {
    const index = JSON.parse(readFileSync("data/fixtures/market-parcels/index.json", "utf8")) as MarketParcelIndex;
    const swfl = index.markets.SWFL;
    expect(swfl.tier).toBe("other");
    expect(swfl.parcelCount).toBeGreaterThan(0);
    expect(swfl.counties.map((county) => county.name)).toEqual(["Charlotte", "Collier", "Lee", "Sarasota"]);
    const eligible = JSON.parse(readFileSync("data/fixtures/oz2-other-msas.json", "utf8")) as EligibleMarketsCatalog;
    const rows = filterEligibleRows(eligible.rows, "SWFL", null, null);
    expect(isOtherMarketId("SWFL")).toBe(true);
    expect(isPrimaryMarket("SWFL")).toBe(false);
    expect(rows).toHaveLength(75);
    expect(rows.every((row) => row.status === ELIGIBLE_NOT_DESIGNATED_STATUS)).toBe(true);
    expect(rows.every((row) => !/^designated/i.test(row.status))).toBe(true);
  });
});
