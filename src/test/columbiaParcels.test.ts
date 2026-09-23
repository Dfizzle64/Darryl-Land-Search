import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { formatParcelPlace, parcelAppraiserUrl } from "../lib/format";
import { marketParcelScopeNotes, showMarketParcels, type MarketParcelIndex } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

describe("Columbia MSA parcel labels", () => {
  it("names the city and the county without calling South Carolina Florida", () => {
    expect(
      formatParcelPlace({
        situsCity: null,
        situsZip: null,
        countyName: "Richland",
        state: "South Carolina",
        jurisdictionCode: "City of Columbia",
      }),
    ).toBe("Richland County, South Carolina · City of Columbia");
    expect(
      formatParcelPlace({
        situsCity: "GILBERT",
        situsZip: "29054",
        countyName: "Lexington",
        state: "South Carolina",
        jurisdictionCode: "Town of Chapin",
      }),
    ).toBe("GILBERT 29054 · Town of Chapin");
    expect(
      formatParcelPlace({
        situsCity: "ORLANDO",
        situsZip: "32801",
        countyName: "Orange",
        state: "Florida",
      }),
    ).toBe("ORLANDO 32801");
    expect(formatParcelPlace({ countyName: "Orange", state: null })).toBe("Orange County, FL");
  });

  it("points Lexington and Richland searches at the public county pages", () => {
    expect(parcelAppraiserUrl({ parcelId: "005200-04-076", countyFips: "45063" })).toEqual({
      href: "https://maps.lex-co.com/OneMap/",
      label: "Open Lexington County property search",
    });
    expect(parcelAppraiserUrl({ parcelId: "04908-01-15", countyFips: "45079" })).toEqual({
      href: "https://property.spatialest.com/sc/richland#/",
      label: "Open Richland County property search",
    });
  });

  it("surfaces the city-only and countywide-gap sentences on the market", () => {
    const notes = marketParcelScopeNotes({
      tier: "other",
      parcelCount: 10,
      completeCountyCount: 1,
      sampleCountyCount: 1,
      gapCountyCount: 8,
      path: "data/fixtures/market-parcels/markets/columbia/meta.json",
      counties: [
        {
          name: "Lexington",
          state: "South Carolina",
          fips: "45063",
          featureCount: 8,
          coverage: "complete-gte-5ac",
          gaps: ["Municipal zoning is joined from public layers: West Columbia, Cayce, Chapin, and City of Columbia."],
        },
        {
          name: "Richland",
          state: "South Carolina",
          fips: "45079",
          featureCount: 2,
          coverage: "sample",
          gaps: [
            "City of Columbia only (CityLimit=Y on the Richland side of LandRecords). Richland County has no public ArcGIS FeatureServer or MapServer for countywide parcels.",
          ],
        },
      ],
    });
    expect(notes.join(" ")).toMatch(/Municipal zoning is joined/);
    expect(notes.join(" ")).toMatch(/City of Columbia only/);
    expect(notes.join(" ")).toMatch(/no public ArcGIS FeatureServer/);
  });

  it("documents the Richland countywide gap in the README", () => {
    const readme = readFileSync(path.join(process.cwd(), "README.md"), "utf8");
    expect(readme).toMatch(/maps\.lex-co\.com\/agstserver\/rest\/services\/Property\/MapServer\/4/);
    expect(readme).toMatch(/LandRecords\/MapServer\/2/);
    expect(readme).toMatch(/CityLimit='Y'/);
    expect(readme).toMatch(/Richland County has no public countywide parcel FeatureServer/);
    expect(readme).toMatch(/Service WFS is disabled/);
    expect(readme).toMatch(/does not use the dataviewer PHP parcel endpoints/);
    expect(readme).not.toMatch(/GetParcelData\.php/);
  });

  it("keeps Lexington on the map and Richland as a City of Columbia sample", () => {
    const root = path.join(process.cwd(), "data/fixtures/market-parcels");
    const lexPath = path.join(root, "counties/45063/county.json");
    const richPath = path.join(root, "counties/45079/county.json");
    expect(existsSync(lexPath)).toBe(true);
    expect(existsSync(richPath)).toBe(true);
    const lex = JSON.parse(readFileSync(lexPath, "utf8")) as {
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      gaps: string[];
      minAcres: number;
      maxAcres: number;
    };
    const rich = JSON.parse(readFileSync(richPath, "utf8")) as {
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      gaps: string[];
    };
    expect(lex.coverage).toBe("complete-gte-5ac");
    expect(lex.featureCount).toBeGreaterThan(1000);
    expect(lex.minAcres).toBe(5);
    expect(lex.maxAcres).toBe(150);
    expect(lex.source).toBe("sc-lexington-property-4");
    expect(lex.queryUrl).toContain("maps.lex-co.com/agstserver/rest/services/Property/MapServer/4");
    const lexGaps = lex.gaps.join(" ");
    expect(lexGaps).toMatch(/West Columbia/);
    expect(lexGaps).toMatch(/Cayce/);
    expect(lexGaps).toMatch(/Chapin/);
    expect(lexGaps).toMatch(/City of Columbia/);
    expect(lexGaps).toMatch(/Zoning join counts/);

    expect(rich.coverage).toBe("sample");
    expect(rich.featureCount).toBeGreaterThan(0);
    expect(rich.source).toBe("sc-columbia-city-landrecords");
    expect(rich.queryUrl).toContain("gis.columbiasc.gov/cola/rest/services/InnercityMap/LandRecords/MapServer/2");
    const richGaps = rich.gaps.join(" ");
    expect(richGaps).toMatch(/City of Columbia only/);
    expect(richGaps).toMatch(/no public ArcGIS FeatureServer/);
    expect(richGaps).toMatch(/WFS is disabled/);
    expect(richGaps.toLowerCase()).not.toMatch(/getparceldata\.php/);

    const index = JSON.parse(readFileSync(path.join(root, "index.json"), "utf8")) as MarketParcelIndex;
    expect(showMarketParcels("Columbia", null, null, index)).toBe(true);
    expect(showMarketParcels("Columbia", "Lexington", "South Carolina", index)).toBe(true);
    expect(showMarketParcels("Columbia", "Richland", "South Carolina", index)).toBe(true);
    expect(marketParcelScopeNotes(index.markets.Columbia).join(" ")).toMatch(/City of Columbia only/);
    expect(marketParcelScopeNotes(index.markets.Columbia).join(" ")).toMatch(/Richland County has no public/);

    const lexTile = readdirSync(path.join(root, "counties/45063/tiles")).find((name) => name.endsWith(".geojson"));
    expect(lexTile).toBeTruthy();
    const lexCollection = JSON.parse(
      readFileSync(path.join(root, "counties/45063/tiles", lexTile as string), "utf8"),
    ) as ParcelCollection;
    const lexFeature = lexCollection.features[0];
    expect(lexFeature.properties.countyFips).toBe("45063");
    expect(lexFeature.properties.marketIds).toContain("Columbia");
    expect(lexFeature.properties.marketIds).not.toContain("Orlando");
    expect(lexFeature.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(lexFeature.properties.acreage).toBeLessThanOrEqual(150);
    expect(lexFeature.properties.source).toBe("sc-lexington-property-4");
    expect(lexFeature.properties.appraiserUrl).toContain("maps.lex-co.com/OneMap");

    const richTile = readdirSync(path.join(root, "counties/45079/tiles")).find((name) => name.endsWith(".geojson"));
    expect(richTile).toBeTruthy();
    const richCollection = JSON.parse(
      readFileSync(path.join(root, "counties/45079/tiles", richTile as string), "utf8"),
    ) as ParcelCollection;
    const cityFeature = richCollection.features[0];
    expect(cityFeature.properties.countyFips).toBe("45079");
    expect(cityFeature.properties.jurisdictionCode).toBe("City of Columbia");
    expect(cityFeature.properties.source).toBe("sc-columbia-city-landrecords");
    expect(cityFeature.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(cityFeature.properties.acreage).toBeLessThanOrEqual(150);
    expect(cityFeature.properties.dataGaps?.join(" ")).toMatch(/City of Columbia only/);
    expect(cityFeature.properties.dataGaps?.join(" ") ?? "").not.toMatch(/sale price or tax value is invented/i);
  });
});
