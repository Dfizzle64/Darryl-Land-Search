import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { DEFAULT_FILTERS, RURAL_ELIGIBLE_STATUS_CHIP, type FilterState, type ParcelFeature } from "../lib/types";
import { describeOz2Eligibility } from "../lib/opportunityZone";
import {
  OZ2_NOT_JOINED,
  SITE_PDF_DISCLAIMER,
  assembleSiteSummary,
  chooseScaleBar,
  contextBbox,
  eligibleTractIsVisible,
  googleMapsUrl,
  ozPdfStatus,
  pdfScreeningLine,
  sitePdfFileName,
  type TractGeometryRecord,
} from "../lib/sitePdf";
import { buildSitePdfBytes, factRowHeight } from "../lib/sitePdfDocument";
import type { ScreeningPoint } from "../lib/screening";

const SQUARE: GeoJSON.Polygon = {
  type: "Polygon",
  coordinates: [
    [
      [-81.38, 28.54],
      [-81.37, 28.54],
      [-81.37, 28.55],
      [-81.38, 28.55],
      [-81.38, 28.54],
    ],
  ],
};

const TINY_PNG =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

function parcel(overrides: Partial<ParcelFeature["properties"]> = {}): ParcelFeature {
  return {
    type: "Feature",
    geometry: SQUARE,
    properties: {
      id: "12095:282312817612000",
      parcelId: "282312817612000",
      countyFips: "12095",
      countyName: "Orange",
      state: "Florida",
      situsAddress: "1234 BUFORD ST",
      situsCity: "Orlando",
      situsZip: "32801",
      jurisdictionCode: null,
      ownerName: "QUARTERPATH LLC",
      ownerName2: null,
      propertyName: null,
      zoningCode: "R-3",
      zoningDistrict: null,
      jurisdictionPrefix: null,
      dorCode: "9600",
      acreage: 12.4,
      centroid: [-81.375, 28.545],
      lastSale: { date: "2020-03-01", price: 1250000, qualified: null },
      tax: { marketValue: 900000, assessedValue: 700000, taxableValue: 650000, taxes: 12000 },
      mailingAddress: { line1: null, line2: null, city: null, state: null, zip: null },
      incomeTract: {
        geoid: "12095016702",
        name: "Census Tract 167.02",
        medianHouseholdIncome: 54210,
        medianHouseholdIncomeMoe: 1200,
        vintage: "acs5_2020_2024",
      },
      incomeBlockGroup: null,
      nearestRoad: { aadt: 18500, year: 2024, roadwayId: null, from: "SR 50", to: "SR 436", distanceMeters: 240 },
      flu: { code: "MF", label: "Multifamily", jurisdiction: "Orlando", source: null },
      opportunityZone: null,
      oz2Eligibility: {
        eligible: true,
        rural: false,
        tractGeoid: "12095016702",
        tractName: null,
        designation: "eligible-for-nomination",
        source: "rev-proc-2026-14",
      },
      source: "ocpa-fixture",
      ...overrides,
    },
  };
}

const TRACT: TractGeometryRecord = {
  geometry: SQUARE,
  rural: false,
  medianHouseholdIncome: 54210,
};

function filters(overrides: Partial<FilterState> = {}): FilterState {
  return { ...DEFAULT_FILTERS, ...overrides };
}

describe("site PDF assembly", () => {
  it("names the file from the county and parcel id", () => {
    expect(sitePdfFileName("Orange", "282312817612000")).toBe("CDP-site-orange-282312817612000.pdf");
    expect(sitePdfFileName("Miami-Dade", "28/23 12")).toBe("CDP-site-miami-dade-28-23-12.pdf");
  });

  it("copies OZ 2.0 status from the parcel panel and does not invent a designation", () => {
    const feature = parcel();
    const model = assembleSiteSummary({
      parcel: feature,
      zoningLine: "R-3",
      fluLine: "Multifamily · Orlando",
      filters: filters(),
      rent: null,
      eligibleTract: TRACT,
      generatedAt: new Date("2026-10-02T15:00:00Z"),
      timeZone: "UTC",
    });
    const described = describeOz2Eligibility(feature.properties.oz2Eligibility);
    const oz = model.tractFacts.find((fact) => fact.label === "OZ 2.0");
    expect(oz?.value).toBe(ozPdfStatus(described));
    expect(oz?.value).toBe("Eligible, not rural");
    expect(oz?.value).not.toContain("12095016702");
    expect(oz?.value).not.toContain("designated QOZ");
    expect(model.tractFacts.find((fact) => fact.label === "Rural")?.value).toBe("Non-rural");
    expect(model.tractFacts.find((fact) => fact.label === "2020 GEOID")?.value).toBe("12095016702");
    expect(model.generatedOn).toBe("October 2, 2026");
    expect(model.fileName).toBe("CDP-site-orange-282312817612000.pdf");
    expect(model.disclaimer).toBe(SITE_PDF_DISCLAIMER);
  });

  it("uses the rural chip exactly and leaves missing rent as dashes", () => {
    const feature = parcel({
      oz2Eligibility: {
        eligible: true,
        rural: true,
        tractGeoid: "01001020100",
        tractName: null,
        designation: "eligible-for-nomination",
        source: "rev-proc-2026-14",
      },
      countyName: "Autauga",
      state: "Alabama",
      countyFips: "01001",
    });
    const model = assembleSiteSummary({
      parcel: feature,
      zoningLine: null,
      fluLine: null,
      filters: filters(),
      rent: { safmr2Br: 980 },
      generatedAt: new Date("2026-10-02T15:00:00Z"),
      timeZone: "UTC",
    });
    expect(model.tractFacts.find((fact) => fact.label === "OZ 2.0")?.value).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(model.tractFacts.find((fact) => fact.label === "OZ 2.0")?.value).not.toContain("01001020100");
    expect(model.tractFacts.find((fact) => fact.label === "Rural")?.value).toBe("Rural");
    expect(model.tractFacts.find((fact) => fact.label === "Zoning")).toBeUndefined();
    expect(model.tractFacts.find((fact) => fact.label === "Future land use")).toBeUndefined();
    const rents = model.tractFacts.filter((fact) =>
      ["ACS median gross rent", "HUD SAFMR 2BR", "Zillow MF 5+ (metro)", "Zillow all homes (ZIP)", "Apartment List"].includes(
        fact.label,
      ),
    );
    expect(rents.map((fact) => fact.label)).toEqual([
      "ACS median gross rent",
      "HUD SAFMR 2BR",
      "Zillow MF 5+ (metro)",
      "Zillow all homes (ZIP)",
      "Apartment List",
    ]);
    expect(rents.find((fact) => fact.label === "HUD SAFMR 2BR")?.value).toContain("$980");
    for (const fact of rents) {
      if (fact.label !== "HUD SAFMR 2BR") expect(fact.value.startsWith("—")).toBe(true);
    }
  });

  it("says the join is missing instead of calling an unjoined parcel eligible", () => {
    const feature = parcel({ oz2Eligibility: null, incomeTract: null });
    const model = assembleSiteSummary({
      parcel: feature,
      zoningLine: null,
      fluLine: null,
      filters: filters(),
      generatedAt: new Date("2026-10-02T12:00:00Z"),
      timeZone: "UTC",
    });
    const oz = model.tractFacts.find((fact) => fact.label === "OZ 2.0")?.value ?? "";
    expect(oz).toBe(OZ2_NOT_JOINED);
    expect(oz.toLowerCase()).not.toContain("eligible");
    expect(model.tractFacts.find((fact) => fact.label === "Rural")).toBeUndefined();
    expect(model.tractFacts.find((fact) => fact.label === "2020 GEOID")).toBeUndefined();
    expect(model.eligibleTract).toBeNull();
  });

  it("omits empty money fields, owner contact, and a land-use decoding", () => {
    const feature = parcel({
      ownerName: null,
      ownerName2: null,
      dorCode: null,
      tax: { marketValue: null, assessedValue: null, taxableValue: null, taxes: null },
      lastSale: { date: null, price: null, qualified: null },
    });
    const dirty = parcel({
      ...feature.properties,
      ownerName: "QUARTERPATH LLC",
    });
    (dirty.properties as ParcelFeature["properties"] & { ownerPhone?: string; ownerEmail?: string }).ownerPhone =
      "555-0100";
    (dirty.properties as ParcelFeature["properties"] & { ownerEmail?: string }).ownerEmail = "owner@example.com";
    const model = assembleSiteSummary({
      parcel: dirty,
      zoningLine: null,
      fluLine: null,
      filters: filters(),
      generatedAt: new Date("2026-10-02T12:00:00Z"),
      timeZone: "UTC",
    });
    const labels = model.parcelFacts.map((fact) => fact.label);
    expect(labels).not.toContain("Market value");
    expect(labels).not.toContain("Assessed value");
    expect(labels).not.toContain("Taxes");
    expect(labels).not.toContain("Last sale");
    expect(labels).not.toContain("Land use");
    const packed = JSON.stringify(model);
    expect(packed).not.toContain("555-0100");
    expect(packed).not.toContain("owner@example.com");
    expect(packed).not.toContain("ownerPhone");
    expect(model.parcelFacts.find((fact) => fact.label === "Owner")?.value).toBe("QUARTERPATH LLC");
    expect(model.links.map((link) => link.label)).toContain("Google Maps");
    expect(model.links.find((link) => link.label === "Google Maps")?.href).toBe(googleMapsUrl(28.545, -81.375));
  });

  it("keeps flood and school text that the panel already has", () => {
    const point = {
      flood: {
        status: "ok",
        zone: "X",
        subtype: null,
        sfha: false,
        floodway: false,
        staticBfe: null,
        depth: null,
        datum: null,
        community: null,
        cid: null,
        summary: "Zone X. Outside the SFHA.",
        source: "FEMA NFHL",
        sourceUrl: "https://www.fema.gov/flood-maps",
      },
      wetland: {
        status: "none",
        code: null,
        wetlandType: null,
        summary: "No NWI wetland at this point.",
        source: "NWI",
        sourceUrl: "https://www.fws.gov/program/national-wetlands-inventory",
      },
      utilities: [],
      schools: [
        {
          id: "s1",
          name: "Lake Elementary",
          city: "Orlando",
          state: "FL",
          level: "Elementary",
          rating: null,
          ratingKind: null,
          year: null,
          summary: "No published grade.",
          source: "NCES",
          sourceUrl: "https://nces.ed.gov/",
          reportCardUrl: null,
          distanceMiles: 1.2,
          lon: -81.37,
          lat: 28.54,
        },
      ],
      schoolsNote: "Grades are only shown when the extract has them.",
      tract: null,
    } satisfies ScreeningPoint;
    const model = assembleSiteSummary({
      parcel: parcel(),
      zoningLine: "R-3",
      fluLine: null,
      screeningPoint: point,
      screeningStatus: "idle",
      filters: filters(),
      generatedAt: new Date("2026-10-02T12:00:00Z"),
      timeZone: "UTC",
    });
    const flood = model.screeningFacts.find((fact) => fact.label === "Flood zone")?.value ?? "";
    expect(flood).toBe("Zone X. Outside the SFHA.");
    expect(flood).not.toMatch(/BFE|base flood/i);
    const schools = model.screeningFacts.find((fact) => fact.label === "Schools")?.value ?? "";
    expect(schools).toContain("No grade");
    expect(schools).toContain("Lake Elementary");
    expect(schools).not.toMatch(/\bGrade [A-F]\b/);
    expect(model.screeningFacts.find((fact) => fact.label === "Nearest FDOT AADT")?.value).toContain("18,500");
    expect(model.sources).toContain("FEMA NFHL");
    expect(model.disclaimer).toBe("Public data; verify before relying on it.");
  });

  it("shortens screening to a finished clause and caps schools at three", () => {
    const flood = pdfScreeningLine(
      "flood",
      "FEMA zone X at the parcel centroid. AREA OF MINIMAL FLOOD HAZARD. Not flagged as SFHA on this polygon. No published static base flood elevation on this polygon.",
    );
    expect(flood).toBe("FEMA zone X at the parcel centroid (minimal flood hazard).");
    expect(flood).not.toMatch(/\.\.\.|BFE|base flood/i);
    expect(pdfScreeningLine("wetland", "No NWI wetland polygon within about 70 feet of this point. Nearby wetlands can still exist.")).toBe(
      "No NWI wetland polygon within ~70 ft.",
    );
    const water = pdfScreeningLine(
      "utility",
      "Water service area: Orange County. Service-area provider from county open data — not a connection or will-serve letter.",
    );
    expect(water).toBe("Orange County service area. Not a will-serve.");
    expect(water).not.toContain("...");
    const schools = Array.from({ length: 8 }, (_, index) => ({
      id: `s${index}`,
      name: `School ${index + 1}`,
      city: null,
      state: "FL",
      level: "Elementary",
      rating: null,
      ratingKind: null as const,
      year: null,
      summary: "No letter grade in this public extract.",
      source: "NCES",
      sourceUrl: "https://nces.ed.gov/",
      reportCardUrl: null,
      distanceMiles: index + 1,
      lon: -81.37,
      lat: 28.54,
    }));
    const model = assembleSiteSummary({
      parcel: parcel(),
      zoningLine: "R-3",
      fluLine: "Multifamily",
      screeningPoint: {
        flood: {
          status: "ok",
          zone: "X",
          subtype: null,
          sfha: false,
          floodway: false,
          staticBfe: null,
          depth: null,
          datum: null,
          community: null,
          cid: null,
          summary:
            "FEMA zone X at the parcel centroid. AREA OF MINIMAL FLOOD HAZARD. Not flagged as SFHA on this polygon. No published static base flood elevation on this polygon.",
          source: "FEMA",
          sourceUrl: "https://www.fema.gov/flood-maps",
        },
        wetland: {
          status: "none",
          code: null,
          wetlandType: null,
          summary: "No NWI wetland polygon within about 70 feet of this point. Nearby wetlands can still exist.",
          source: "NWI",
          sourceUrl: "https://www.fws.gov/",
        },
        utilities: [
          {
            kind: "water",
            status: "ok",
            providers: ["Orange County"],
            summary:
              "Water service area: Orange County. Service-area provider from county open data — not a connection or will-serve letter.",
            source: "Orange County open data",
            sourceUrl: "https://www.ocfl.net/",
          },
        ],
        schools,
        schoolsNote: "Grades are only shown when the extract has them.",
        tract: null,
      },
      screeningStatus: "idle",
      filters: filters(),
      generatedAt: new Date("2026-10-02T12:00:00Z"),
      timeZone: "UTC",
    });
    const schoolFact = model.screeningFacts.find((fact) => fact.label === "Schools")?.value ?? "";
    expect(schoolFact).toContain("School 1");
    expect(schoolFact).toContain("School 3");
    expect(schoolFact).not.toContain("School 4");
    expect(schoolFact).toContain("+5 more");
    expect(model.screeningFacts.find((fact) => fact.label === "Flood zone")?.value).toBe(flood);
    const bytes = buildSitePdfBytes(model, {
      main: TINY_PNG,
      locator: TINY_PNG,
      scaleLabel: "0.5 mi",
      logo: TINY_PNG,
    });
    const text = new TextDecoder().decode(bytes);
    expect(text).not.toContain("/Count 2");
    expect(text).toContain("Eligible, not rural");
    expect(text).toContain("+5 more");
    expect(text).toContain(SITE_PDF_DISCLAIMER);
    expect(text).not.toContain("School 4");
  });

  it("gives a wrapped value a taller row than a single line", () => {
    expect(factRowHeight(3, 1)).toBeGreaterThan(factRowHeight(1, 1) + 8 * 1.15);
    expect(factRowHeight(1, 2)).toBeGreaterThan(factRowHeight(1, 1));
  });

  it("hides AADT outside Florida when no count was joined and hides screening when idle", () => {
    const feature = parcel({
      state: "Alabama",
      countyName: "Autauga",
      nearestRoad: null,
    });
    const model = assembleSiteSummary({
      parcel: feature,
      zoningLine: null,
      fluLine: null,
      screeningPoint: null,
      screeningStatus: "idle",
      filters: filters(),
      generatedAt: new Date("2026-10-02T12:00:00Z"),
      timeZone: "UTC",
    });
    expect(model.screeningFacts).toEqual([]);
  });

  it("tints an eligible tract only while that overlay would be on the map", () => {
    const described = describeOz2Eligibility(parcel().properties.oz2Eligibility);
    expect(
      eligibleTractIsVisible({
        showTracts: true,
        eligible: described.eligible,
        shown: described.shown,
        rural: described.rural,
        tractClass: "both",
        filters: filters(),
        medianHouseholdIncome: 54210,
        rent: null,
        hasGeometry: true,
      }),
    ).toBe(true);
    expect(
      eligibleTractIsVisible({
        showTracts: false,
        eligible: true,
        shown: true,
        rural: false,
        tractClass: "both",
        filters: filters(),
        medianHouseholdIncome: null,
        rent: null,
        hasGeometry: true,
      }),
    ).toBe(false);
    expect(
      eligibleTractIsVisible({
        showTracts: true,
        eligible: true,
        shown: false,
        rural: true,
        tractClass: "both",
        filters: filters(),
        medianHouseholdIncome: null,
        rent: null,
        hasGeometry: true,
      }),
    ).toBe(false);
    const hidden = assembleSiteSummary({
      parcel: parcel(),
      zoningLine: null,
      fluLine: null,
      filters: filters(),
      eligibleTract: { ...TRACT, rural: false },
      showTracts: false,
      generatedAt: new Date("2026-10-02T12:00:00Z"),
      timeZone: "UTC",
    });
    expect(hidden.eligibleTract).toBeNull();
    const shown = assembleSiteSummary({
      parcel: parcel(),
      zoningLine: null,
      fluLine: null,
      filters: filters(),
      eligibleTract: TRACT,
      showTracts: true,
      generatedAt: new Date("2026-10-02T12:00:00Z"),
      timeZone: "UTC",
    });
    expect(shown.eligibleTract?.geometry.type).toBe("Polygon");
  });

  it("picks a readable scale and keeps the parcel inside a wider frame", () => {
    const scale = chooseScaleBar(0.5);
    expect(scale.label).toBe("200 ft");
    expect(scale.pixels).toBeGreaterThan(64);
    expect(scale.pixels).toBeLessThan(180);
    const frame = contextBbox(SQUARE);
    expect(frame).not.toBeNull();
    const [west, south, east, north] = frame!;
    expect(west).toBeLessThan(-81.38);
    expect(east).toBeGreaterThan(-81.37);
    expect(south).toBeLessThan(28.54);
    expect(north).toBeGreaterThan(28.55);
  });

  it("builds a single-page PDF that names the site and the disclaimer", () => {
    const model = assembleSiteSummary({
      parcel: parcel({ oz2Eligibility: null }),
      zoningLine: "R-3",
      fluLine: null,
      filters: filters(),
      generatedAt: new Date("2026-10-02T12:00:00Z"),
      timeZone: "UTC",
    });
    const bytes = buildSitePdfBytes(model, {
      main: TINY_PNG,
      locator: TINY_PNG,
      scaleLabel: "500 ft",
      logo: TINY_PNG,
    });
    const text = new TextDecoder().decode(bytes);
    expect(text.startsWith("%PDF")).toBe(true);
    expect(text).toContain("Site summary");
    expect(text).toContain("282312817612000");
    expect(text).toContain(SITE_PDF_DISCLAIMER);
    expect(text).toContain("October 2, 2026");
    expect(text).toContain("SR 50 to SR 436");
    expect(text).not.toContain("\u2192");
    expect(text).not.toContain("/Count 2");
    const drawer = readFileSync(new URL("../components/ParcelDrawer.tsx", import.meta.url), "utf8");
    expect(drawer).toContain("Export PDF");
    expect(drawer).toContain('import("@/lib/sitePdfExport")');
  });
});
