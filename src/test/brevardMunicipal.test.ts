import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  brevardFluEmpty,
  brevardFluReason,
  centroidInBrevard,
  formatJoinedZoning,
  isBlockedServiceUrl,
  layerUrls,
  mostLocalHit,
  parcelAttributeKeys,
  partialPlaces,
  placeById,
  readOverlayValue,
  resolveFluHit,
  resolveZoningHit,
  wireReadyPlaces,
  type MunicipalCatalog,
  type OverlayHit,
} from "../lib/brevardMunicipal";

const catalog = JSON.parse(
  readFileSync(path.join(process.cwd(), "data/brevard-municipal.json"), "utf8"),
) as MunicipalCatalog;

function hit(partial: Partial<OverlayHit> & Pick<OverlayHit, "placeId" | "areaSqM">): OverlayHit {
  return {
    kind: "city",
    status: "usable",
    rank: 1,
    code: "R-1",
    label: null,
    layerUrl: "https://example.test/layer",
    ...partial,
  };
}

describe("Brevard municipal catalog", () => {
  it("lists the five wire-ready cities, including the Cocoa FLU close", () => {
    const places = wireReadyPlaces(catalog);
    expect(places.map((place) => place.name)).toEqual([
      "Melbourne",
      "West Melbourne",
      "Rockledge",
      "Satellite Beach",
      "Cocoa",
    ]);
    for (const place of places) {
      expect(place.status).toBe("usable");
      expect(place.countyFips).toBe("12009");
      expect(place.zoning?.url).toBeTruthy();
      expect(place.flu?.url).toBeTruthy();
      expect(place.fluGap).toBeUndefined();
    }
    const melbourne = places[0];
    expect(melbourne.join).toBe("spatial");
    expect(melbourne.zoning?.url).toMatch(/MapServer\/109$/);
    expect(melbourne.flu?.url).toMatch(/MapServer\/108$/);
    expect(melbourne.flu?.where).toBe("Status='Active / Current'");
    expect(melbourne.zoning?.fields).toEqual(["ZONING", "ZONE_ALL"]);
    expect(melbourne.flu?.fields).toEqual(["FLUM"]);

    const cocoa = places.find((place) => place.id === "cocoa");
    expect(cocoa?.fluClose).toBe(true);
    expect(cocoa?.zoning?.alreadyCarded).toBe(true);
    expect(cocoa?.zoning?.url).toMatch(/FeatureServer\/1$/);
    expect(cocoa?.flu?.url).toMatch(/FLU_Public_View\/FeatureServer\/6$/);
    expect(cocoa?.flu?.fields).toEqual(["FLUCity"]);
    expect(cocoa?.join).toBe("attribute-then-spatial");
    expect(cocoa?.zoning?.idFields).toEqual(["TaxAcct", "Name"]);
  });

  it("keeps partial cities honest", () => {
    const partials = partialPlaces(catalog);
    expect(partials.map((place) => place.id)).toEqual(["indian-harbour-beach", "cocoa-beach"]);
    const ihb = partials[0];
    expect(ihb.zoning?.url).toMatch(/IHB_Zoning_LandUse_AGOL\/FeatureServer\/1$/);
    expect(ihb.flu).toBeNull();
    expect(ihb.fluGap).toMatch(/land cover|not a future land use/i);
    expect(ihb.zoning?.fields).toEqual(["Zoning"]);
    expect(ihb.zoning?.fields.join(" ")).not.toMatch(/FLU/);

    const cocoaBeach = partials[1];
    expect(cocoaBeach.unofficial).toBe(true);
    expect(cocoaBeach.vintage).toBe("2021");
    expect(cocoaBeach.zoning?.url).toMatch(/CBParcelsMaster2021\/FeatureServer\/0$/);
    expect(cocoaBeach.flu?.url).toBe(cocoaBeach.zoning?.url);
    expect(cocoaBeach.flu?.fields).toEqual(["FLU"]);
  });

  it("does not wire Palm Bay, Titusville, gap cities, county layers, or school zones", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.doNotInventSchoolGrades).toBe(true);
    expect(catalog.doNotInventBaseFloodElevations).toBe(true);
    expect(catalog.skippedAlreadyCarded.map((place) => place.id)).toEqual(["palm-bay", "titusville"]);
    expect(catalog.gaps.map((place) => place.id)).toEqual([
      "cape-canaveral",
      "indialantic",
      "melbourne-beach",
      "grant-valkaria",
      "palm-shores",
      "melbourne-village",
      "malabar",
    ]);
    const wired = new Set(catalog.places.map((place) => place.id));
    for (const skipped of [...catalog.skippedAlreadyCarded, ...catalog.gaps]) {
      expect(wired.has(skipped.id)).toBe(false);
    }
    const banned = [
      "https://gis.brevardfl.gov/gissrv/rest/services/Planning_Development/Zoning_WKID2881/MapServer/0",
      "https://gis.brevardfl.gov/gissrv/rest/services/Planning_Development/FLU_WKID2881/MapServer/0",
      "https://gis.brevardfl.gov/gissrv/rest/services/Accela/AccelaGIS_Layers_WKID2881/MapServer/7",
      "https://cwm-gis.westmelbourne.org/server/rest/services/Hosted/County_FLU_Areas/FeatureServer/0",
      "https://cwm-gis.westmelbourne.org/server/rest/services/Hosted/High_School_Zones_View/FeatureServer/0",
      "https://gis.melbourneflorida.org/arcgis/rest/services/Zoning/MapServer/0",
    ];
    for (const url of banned) {
      expect(isBlockedServiceUrl(catalog, url)).toBe(true);
    }
    for (const place of catalog.places) {
      for (const url of layerUrls(place)) {
        expect(isBlockedServiceUrl(catalog, url)).toBe(false);
        expect(url.toLowerCase()).not.toContain("melbourneflorida.org");
      }
    }
    expect(catalog.namesakes.map((item) => item.id)).toContain("melbourne-au");
  });

  it("rejects Melbourne, Australia and keeps the card centroids in Brevard", () => {
    expect(centroidInBrevard(catalog, 144.96, -37.81)).toBe(false);
    expect(centroidInBrevard(catalog, -80.621, 28.099)).toBe(true);
    expect(centroidInBrevard(catalog, -80.705, 28.085)).toBe(true);
    expect(centroidInBrevard(catalog, -80.734, 28.311)).toBe(true);
    expect(centroidInBrevard(catalog, -80.587, 28.158)).toBe(true);
    expect(centroidInBrevard(catalog, -80.763, 28.375)).toBe(true);
    expect(centroidInBrevard(catalog, -95.88, 32.68)).toBe(false);
  });

  it("reads published fields and builds TaxAcct keys", () => {
    const melbourne = wireReadyPlaces(catalog)[0];
    expect(readOverlayValue({ ZONING: "CP", ZONE_ALL: "CP-OLD" }, melbourne.zoning!.fields)).toEqual({
      code: "CP",
      label: null,
    });
    expect(readOverlayValue({ FLUM: "General Commercial", Status: "Pending" }, melbourne.flu!.fields)).toEqual({
      code: "General Commercial",
      label: null,
    });
    const west = placeById(catalog, "west-melbourne");
    expect(
      readOverlayValue({ zoningnew: "R-3", zoningdesc: "Multiple-Family Dwelling" }, west!.zoning!.fields, west!.zoning!.labelFields),
    ).toEqual({ code: "R-3", label: "Multiple-Family Dwelling" });
    expect(parcelAttributeKeys(2865461)).toEqual(["2865461"]);
    expect(parcelAttributeKeys("27 3701-50-4-12")).toContain("27370150412");
    expect(parcelAttributeKeys("  ")).toEqual([]);
  });

  it("prefers an attribute match over a neighbor polygon", () => {
    const west = placeById(catalog, "west-melbourne");
    const attribute = hit({
      placeId: "west-melbourne",
      areaSqM: 1,
      rank: west!.rank,
      code: "R-3",
      layerUrl: west!.zoning!.url,
    });
    const melbourne = hit({ placeId: "melbourne", areaSqM: 10, code: "CP" });
    expect(resolveZoningHit({ attributeHit: attribute, cityHits: [melbourne] })?.code).toBe("R-3");
    expect(
      resolveZoningHit({
        attributeHit: null,
        cityHits: [
          hit({ placeId: "melbourne", areaSqM: 900, code: "C1" }),
          hit({ placeId: "satellite-beach", areaSqM: 40, rank: 4, code: "RM1" }),
        ],
      })?.placeId,
    ).toBe("satellite-beach");
    expect(mostLocalHit([])).toBeNull();
  });

  it("does not borrow future land use across a city gap or from the county", () => {
    const ihb = resolveFluHit(catalog, "indian-harbour-beach", [
      hit({ placeId: "melbourne", areaSqM: 20, code: "General Commercial" }),
    ]);
    expect(ihb).toBeNull();
    expect(brevardFluEmpty(placeById(catalog, "indian-harbour-beach")?.fluGap)).toMatch(/land cover|not a future land use/i);

    const sameCity = resolveFluHit(catalog, "melbourne", [
      hit({ placeId: "west-melbourne", areaSqM: 5, code: "UD-RES" }),
      hit({ placeId: "melbourne", areaSqM: 80, code: "General Commercial" }),
    ]);
    expect(sameCity?.code).toBe("General Commercial");

    const cocoaFlu = resolveFluHit(
      catalog,
      "cocoa",
      [hit({ placeId: "rockledge", areaSqM: 4, code: "MDR" })],
      hit({ placeId: "cocoa", areaSqM: 0, code: "LDR", layerUrl: placeById(catalog, "cocoa")!.flu!.url }),
    );
    expect(cocoaFlu?.code).toBe("LDR");
    expect(cocoaFlu?.layerUrl).toMatch(/FeatureServer\/6$/);

    const fluOnly = resolveFluHit(catalog, null, [
      hit({ placeId: "melbourne", areaSqM: 400, code: "Conservation" }),
      hit({ placeId: "satellite-beach", areaSqM: 30, code: "RM" }),
    ]);
    expect(fluOnly?.placeId).toBe("satellite-beach");
  });

  it("flags Cocoa Beach as unofficial 2021 and leaves other cities unmarked", () => {
    expect(
      formatJoinedZoning("RS-1", { placeName: "Cocoa Beach", unofficial: true, vintage: "2021" }),
    ).toBe("RS-1 · Cocoa Beach · unofficial 2021");
    expect(formatJoinedZoning("CP", { placeName: "Melbourne" })).toBe("CP · Melbourne");
    expect(formatJoinedZoning(null, { placeName: "Melbourne" })).toBeNull();
    expect(
      brevardFluReason("FLU LDR supports a published category.", "LDR", { unofficial: true, vintage: "2021" }, "12009"),
    ).toMatch(/unofficial \(2021\)/);
    expect(brevardFluReason("kept", null, { fluGap: "zoning only" }, "12009")).toBe("zoning only");
    expect(brevardFluReason("Orange text", null, null, "12095")).toBe("Orange text");
  });

  it("stamps the existing Brevard DOH shelf and does not invent an Opportunity Zone", () => {
    const summary = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/fixtures/brevard-municipal-join.json"), "utf8"),
    ) as {
      opportunityZonesInvented: number;
      schoolGradesInvented: number;
      baseFloodElevationsInvented: number;
      byPlace: Record<string, { zoning: number; flu: number; unofficial: number }>;
    };
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.schoolGradesInvented).toBe(0);
    expect(summary.baseFloodElevationsInvented).toBe(0);
    expect(summary.byPlace.melbourne).toMatchObject({ zoning: 409, flu: 409, unofficial: 0 });
    expect(summary.byPlace.cocoa).toMatchObject({ zoning: 206, flu: 215 });
    expect(summary.byPlace["indian-harbour-beach"]).toMatchObject({ zoning: 12, flu: 0 });
    expect(summary.byPlace["cocoa-beach"]).toMatchObject({ zoning: 24, flu: 24, unofficial: 24 });

    const folder = path.join(process.cwd(), "data/fixtures/market-parcels/counties/12009/tiles");
    let parcels = 0;
    let zoning = 0;
    let flu = 0;
    let oz = 0;
    let cocoaBeach = 0;
    for (const name of readdirSync(folder)) {
      if (!name.endsWith(".geojson")) continue;
      const collection = JSON.parse(readFileSync(path.join(folder, name), "utf8")) as {
        features: {
          properties: {
            source?: string;
            zoningCode?: string | null;
            flu?: { code?: string | null } | null;
            opportunityZone?: unknown;
            municipal?: { unofficial?: boolean; vintage?: string | null; placeId?: string } | null;
          };
        }[];
      };
      for (const feature of collection.features) {
        const row = feature.properties;
        parcels += 1;
        expect(row.source).toBe("fl-brevard-accela-12009");
        if (row.zoningCode) zoning += 1;
        if (row.flu?.code) flu += 1;
        if (row.opportunityZone) oz += 1;
        if (row.municipal?.placeId === "cocoa-beach") {
          cocoaBeach += 1;
          expect(row.municipal.unofficial).toBe(true);
          expect(row.municipal.vintage).toBe("2021");
        }
      }
    }
    const county = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/fixtures/market-parcels/counties/12009/county.json"), "utf8"),
    ) as { featureCount: number };
    expect(parcels).toBe(county.featureCount);
    expect(parcels).toBeGreaterThan(5746);
    expect(zoning).toBeGreaterThan(0);
    expect(flu).toBeGreaterThan(0);
    expect(oz).toBe(0);
    expect(cocoaBeach).toBeGreaterThan(0);
  });
});
