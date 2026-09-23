import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describeFluMatch } from "../lib/flu";
import {
  davidsonParcelViewerUrl,
  formatParcelPlace,
  parcelAppraiserUrl,
  parcelPublicLinks,
} from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { FluConfig, ParcelCollection } from "../lib/types";

const fluConfig: FluConfig = {
  version: 1,
  updatedAt: "2026-09-23",
  notes: "",
  sources: [],
  categories: [
    {
      code: "MD",
      jurisdiction: "ORG",
      label: "Medium Density Residential",
      allowsMultifamily: true,
      status: "yes",
      why: "test",
    },
  ],
};

describe("Davidson assessor links and place labels", () => {
  it("opens the Metro Parcel Viewer and WebPro instead of the Orange County appraiser", () => {
    const viewer = davidsonParcelViewerUrl("01100012200");
    expect(viewer).toBe("https://maps.nashville.gov/ParcelViewer/?parcelID=01100012200");
    const primary = parcelAppraiserUrl({ parcelId: "01100012200", countyFips: "47037" });
    expect(primary.href).toBe(viewer);
    expect(primary.label).toMatch(/Metro Nashville Parcel Viewer/);
    expect(primary.href).not.toMatch(/ocpafl/);
    const links = parcelPublicLinks({
      parcelId: "01100012200",
      countyFips: "47037",
      appraiserUrl: viewer,
    });
    expect(links.map((link) => link.href)).toEqual([
      viewer,
      "https://portal.padctn.org/OFS/WP/PropertySearch/QuickSearch",
    ]);
  });

  it("keeps Florida place lines and names Tennessee for Davidson", () => {
    expect(formatParcelPlace({ situsCity: "Orlando", situsZip: "32801", countyName: "Orange", state: "Florida" })).toBe(
      "Orlando 32801",
    );
    expect(formatParcelPlace({ countyName: "Orange", state: "Florida" })).toBe("Orange County, FL");
    expect(
      formatParcelPlace({
        situsCity: "GOODLETTSVILLE",
        situsZip: "37072",
        countyName: "Davidson",
        state: "Tennessee",
      }),
    ).toBe("GOODLETTSVILLE 37072 · Davidson County, Tennessee");
  });

  it("describes NashvilleNext policy as guidance", () => {
    const described = describeFluMatch(
      {
        code: "T4 MU",
        label: "Urban Mixed Use Neighborhood",
        jurisdiction: "NashvilleNext",
        source: "nashville-next-ccm",
      },
      fluConfig,
    );
    expect(described.allows).toBeNull();
    expect(described.category).toBeNull();
    expect(described.reason).toMatch(/community character policy/i);
    expect(described.reason).toMatch(/not a zoning entitlement/i);
  });
});

describe("Davidson Metro parcel fixtures", () => {
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47037/county.json");

  it("replaces the IMPACT extract with Metro cadastral parcels", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      source: string;
      queryUrl: string;
      coverage: string;
      featureCount: number;
      gaps: string[];
    };
    expect(county.source).toBe("tn-metro-davidson-parcels");
    expect(county.queryUrl).toContain("Cadastral/Parcels/MapServer/0/query");
    expect(county.queryUrl).not.toContain("IMPACT");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(5000);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/not a Tennessee Comptroller IMPACT county/i);
    expect(gaps).toMatch(/community character policy/i);
    expect(gaps).toMatch(/not a zoning entitlement/i);
    expect(gaps).toMatch(/satellite cities/i);
    expect(gaps).toMatch(/Goodlettsville/);
    expect(gaps).toMatch(/Belle Meade/);
    expect(gaps).toMatch(/ZONECLASS/);
    expect(gaps).toMatch(/Property Date/i);
    expect(gaps).toMatch(/code 500/i);
    expect(gaps).toMatch(/Satellite parcels are blank/i);

    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47037/tiles");
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    const gapCities = new Set(["Belle Meade", "Berry Hill", "Forest Hills", "Oak Hill", "Ridgetop"]);
    let sawOwner = false;
    let sawZoning = false;
    let sawMail = false;
    let sawSale = false;
    let sawTax = false;
    let sawPolicy = false;
    let sawGoodlettsvilleZone = false;
    let sawGapCity = false;
    let checked = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("47037");
        expect(props.state).toBe("Tennessee");
        expect(props.source).toBe("tn-metro-davidson-parcels");
        expect(props.marketIds).toContain("Nashville");
        expect(props.appraiserUrl).toContain(`parcelID=${encodeURIComponent(props.parcelId)}`);
        expect(["Polygon", "MultiPolygon"]).toContain(feature.geometry.type);
        expect(props.jurisdictionCode).toBeTruthy();
        const satellite = props.jurisdictionCode !== "Metro Nashville";
        if (satellite) {
          expect(props.flu).toBeNull();
        }
        if (props.jurisdictionCode === "Goodlettsville") {
          expect(["goodlettsville-zoningargismap-2", "goodlettsville-unmatched"]).toContain(props.zoningSource);
          if (props.zoningSource === "goodlettsville-zoningargismap-2") {
            expect(props.zoningCode).toBeTruthy();
            sawGoodlettsvilleZone = true;
          }
        } else if (props.jurisdictionCode && gapCities.has(props.jurisdictionCode)) {
          expect(props.zoningCode).toBeNull();
          expect(props.zoningSource).toBe("satellite-zoning-rest-gap");
          sawGapCity = true;
        } else {
          expect(props.jurisdictionCode).toBe("Metro Nashville");
          expect(props.zoningSource).toBe("metro-parcel-attribute");
          if (props.flu) {
            expect(props.flu.source).toBe("nashville-next-ccm");
            expect(props.flu.jurisdiction).toBe("NashvilleNext");
            expect(props.flu.code).toBeTruthy();
            sawPolicy = true;
          }
        }
        if (props.ownerName) sawOwner = true;
        if (props.zoningCode) sawZoning = true;
        if (props.mailingAddress?.line1) sawMail = true;
        if (props.lastSale?.price != null || props.lastSale?.date) sawSale = true;
        if (props.tax.marketValue != null && props.tax.assessedValue != null) sawTax = true;
        checked += 1;
      }
    }
    expect(checked).toBe(county.featureCount);
    expect(sawOwner).toBe(true);
    expect(sawZoning).toBe(true);
    expect(sawMail).toBe(true);
    expect(sawSale).toBe(true);
    expect(sawTax).toBe(true);
    expect(sawPolicy).toBe(true);
    expect(sawGoodlettsvilleZone).toBe(true);
    expect(sawGapCity).toBe(true);
  });
});
