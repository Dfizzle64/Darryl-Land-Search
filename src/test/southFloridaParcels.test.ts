import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl, parcelIdLabel } from "../lib/format";
import { MARKET_PARCEL_ACREAGE } from "../lib/marketParcels";
import {
  fluEmptyForSouthFlorida,
  saleEmptyForSouthFlorida,
  southFloridaAppraiserLink,
  southFloridaGisViewer,
  zoningEmptyForSouthFlorida,
} from "../lib/southFlorida";
import { OTHER_MARKETS } from "../lib/types";

const COUNTIES = [
  { fips: "12086", name: "Miami-Dade", source: "fl-miami-dade-landinformation-26", coverage: "complete-gte-5ac" },
  { fips: "12087", name: "Monroe", source: "fl-monroe-apo-parcels-0", coverage: "complete-gte-5ac" },
  { fips: "12011", name: "Broward", source: "fl-broward-bcpa-jan26-16", coverage: "partial" },
  { fips: "12099", name: "Palm Beach", source: "fl-palm-beach-parcel-info-4", coverage: "complete-gte-5ac" },
] as const;

describe("Wave 0 South Florida registration", () => {
  it("keeps the 5–150 acre band and adds no eligible tracts", () => {
    expect(MARKET_PARCEL_ACREAGE).toEqual({ min: 5, max: 150 });
    expect(OTHER_MARKETS[0]).toBe("South Florida");
    expect(OTHER_MARKETS).toContain("South Florida");
  });

  it("builds property-appraiser deep links from the cards", () => {
    expect(parcelIdLabel("12086")).toBe("Folio");
    expect(parcelIdLabel("12011")).toBe("Folio");
    expect(parcelIdLabel("12087")).toBe("RE Number");
    const miami = parcelAppraiserUrl({ parcelId: "30-4131-053-0060", countyFips: "12086" });
    expect(miami.href).toBe("https://apps.miamidadepa.gov/ComparableSales/#/?folio=3041310530060");
    expect(miami.href).not.toContain("papa");
    const monroe = southFloridaAppraiserLink("12087", "00000010-000200", null);
    expect(monroe?.href).toContain("AppID=605");
    expect(monroe?.href).toContain("KeyValue=00000010-000200");
    const stored = parcelAppraiserUrl({
      parcelId: "00000010-000200",
      countyFips: "12087",
      appraiserUrl:
        "https://qpublic.schneidercorp.com/Application.aspx?AppID=605&LayerID=9946&PageTypeID=4&PageID=7635&KeyValue=00000010-000200",
    });
    expect(stored.href).toContain("KeyValue=00000010-000200");
    expect(parcelAppraiserUrl({ parcelId: "474135010090", countyFips: "12011" }).href).toBe(
      "https://bcpa.net/RecInfo.asp?URL_Folio=474135010090",
    );
    const palm = parcelAppraiserUrl({ parcelId: "18424415160010010", countyFips: "12099" });
    expect(palm.href).toBe("https://pbcpao.gov/Property/Details?parcelId=18424415160010010");
    expect(palm.href).not.toContain("pbcgov.org/papa");
  });

  it("opens the jurisdiction GIS layer from the cards", () => {
    const miamiCity = southFloridaGisViewer({
      countyFips: "12086",
      jurisdictionCode: "MIAMI",
      zoningCode: "T6-8-O",
    });
    expect(miamiCity?.href).toBe(
      "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/19",
    );
    expect(miamiCity?.label).toMatch(/municipal zoning/);
    const miamiCounty = southFloridaGisViewer({
      countyFips: "12086",
      jurisdictionCode: "Unincorporated",
      zoningCode: "GU",
    });
    expect(miamiCounty?.href).toMatch(/MapServer\/18$/);
    const miamiMiss = southFloridaGisViewer({ countyFips: "12086", zoningCode: null });
    expect(miamiMiss?.href).toMatch(/MapServer\/26$/);
    const browardCity = southFloridaGisViewer({
      countyFips: "12011",
      jurisdictionCode: "Broward municipal mosaic",
      zoningCode: "CB",
    });
    expect(browardCity?.href).toMatch(/MapServer\/9$/);
    expect(browardCity?.label).toMatch(/not a Fort Lauderdale ordinance/);
    const browardBmsd = southFloridaGisViewer({
      countyFips: "12011",
      jurisdictionCode: "Unincorporated",
      zoningCode: "A-1",
    });
    expect(browardBmsd?.href).toMatch(/Broward_Municipal_Service_District_Zoning\/FeatureServer\/2$/);
    expect(southFloridaGisViewer({ countyFips: "12087", zoningCode: "SC" })?.href).toMatch(/APO_GIS\/MapServer\/19$/);
    expect(southFloridaGisViewer({ countyFips: "12099", zoningCode: "AR" })?.href).toMatch(
      /Planning_Open_Data\/MapServer\/9$/,
    );
    expect(southFloridaGisViewer({ countyFips: "12099", zoningCode: null })?.href).toMatch(/FeatureServer\/4$/);
    const stored = southFloridaGisViewer({
      countyFips: "12099",
      zoningCode: "AR",
      gisViewerUrl: "https://maps.co.palm-beach.fl.us/arcgis/rest/services/OpenData/Planning_Open_Data/MapServer/9",
    });
    expect(stored?.href).toMatch(/MapServer\/9$/);
    expect(southFloridaGisViewer({ countyFips: "12095", zoningCode: "AR" })).toBeNull();
    expect(
      southFloridaGisViewer({
        countyFips: "12099",
        zoningCode: "AR",
        gisViewerUrl: "https://pbcgov.org/papa/PropertyDetail",
      })?.href,
    ).not.toMatch(/papa/);
  });

  it("states the Broward, Monroe, and Palm Beach gaps without inventing screening fields", () => {
    expect(zoningEmptyForSouthFlorida("12086", "fallback")).toMatch(/PRIMARY_ZONE/);
    expect(zoningEmptyForSouthFlorida("12011", "fallback")).toMatch(/BMSD/);
    expect(zoningEmptyForSouthFlorida("12011", "fallback")).toMatch(/not a city ordinance/);
    expect(fluEmptyForSouthFlorida("12011", "fallback")).toMatch(/SLUC1/);
    expect(zoningEmptyForSouthFlorida("12099", "fallback")).toMatch(/does not cover municipalities/);
    expect(saleEmptyForSouthFlorida("12086")).toMatch(/not on the Miami-Dade parcel layer/);
    expect(saleEmptyForSouthFlorida("12011")).toMatch(/FDOR CO_NO=16/);
    expect(saleEmptyForSouthFlorida("12099")).toBeNull();
    const copy = [
      zoningEmptyForSouthFlorida("12086", ""),
      zoningEmptyForSouthFlorida("12087", ""),
      fluEmptyForSouthFlorida("12099", ""),
      saleEmptyForSouthFlorida("12011") ?? "",
    ].join(" ");
    expect(copy).not.toMatch(/school grade|base flood|designated QOZ/i);
  });

  it("registers the four county shelves from the cards when the extract is present", () => {
    const indexPath = path.join("data/fixtures/market-parcels/index.json");
    const index = JSON.parse(readFileSync(indexPath, "utf8")) as {
      markets: Record<string, { tier: string; counties: { fips: string }[] }>;
    };
    const shelf = index.markets["South Florida"];
    expect(shelf?.tier).toBe("shelf");
    expect(shelf?.counties.map((county) => county.fips).sort()).toEqual(["12011", "12086", "12087", "12099"]);
    for (const county of COUNTIES) {
      const file = path.join("data/fixtures/market-parcels/counties", county.fips, "county.json");
      expect(existsSync(file)).toBe(true);
      const row = JSON.parse(readFileSync(file, "utf8")) as {
        name: string;
        source: string;
        coverage: string;
        featureCount: number;
        minAcres: number;
        maxAcres: number;
        queryUrl: string;
        gaps: string[];
        markets: string[];
      };
      expect(row.name).toBe(county.name);
      expect(row.source).toBe(county.source);
      expect(row.coverage).toBe(county.coverage);
      expect(row.featureCount).toBeGreaterThan(0);
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.markets).toContain("South Florida");
      expect(row.queryUrl).not.toMatch(/maps\.monroecounty\.gov|gis\.bcpa\.net|papa|BMSDParcelAddress/);
      const gaps = row.gaps.join(" ");
      if (county.fips === "12011") expect(gaps).toMatch(/CO_NO=16/);
      if (county.fips === "12087") expect(gaps).toMatch(/TLS|certificate/i);
      if (county.fips === "12099") expect(gaps).toMatch(/TLS/);
      if (county.fips === "12086") expect(gaps).toMatch(/PRIMARY_ZONE/);
    }
  });
});
