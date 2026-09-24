import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  fluEmptyForMunicipal,
  hollyHillAttributeKeys,
  isBlockedServiceUrl,
  isStubZoningCode,
  layerUrls,
  mostLocalHit,
  partialPlaces,
  placeForCountywideJurisd,
  readOverlayValue,
  resolveFluHit,
  resolveZoningHit,
  wireReadyPlaces,
  zoningEmptyForCounty,
  type MunicipalCatalog,
  type OverlayHit,
} from "../lib/volusiaFlaglerMunicipal";

const catalog = JSON.parse(
  readFileSync(path.join(process.cwd(), "data/volusia-flagler-municipal.json"), "utf8"),
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

describe("Volusia and Flagler municipal catalog", () => {
  it("lists the 14 wire-ready cities with both zoning and future land use", () => {
    const places = wireReadyPlaces(catalog);
    expect(places.map((place) => place.name)).toEqual([
      "Daytona Beach",
      "Port Orange",
      "Ormond Beach",
      "Deltona",
      "DeLand",
      "Edgewater",
      "South Daytona",
      "Holly Hill",
      "Oak Hill",
      "Ponce Inlet",
      "Palm Coast",
      "Flagler Beach",
      "Bunnell",
      "Marineland",
    ]);
    for (const place of places) {
      expect(place.status).toBe("usable");
      expect(place.zoning?.url).toBeTruthy();
      expect(place.flu?.url).toBeTruthy();
      expect(place.fluGap).toBeUndefined();
    }
  });

  it("keeps partial cities honest about future land use", () => {
    const partials = partialPlaces(catalog);
    expect(partials.map((place) => place.id)).toEqual([
      "daytona-beach-shores",
      "beverly-beach",
      "debary",
      "new-smyrna-beach",
      "orange-city",
      "lake-helen",
      "pierson",
    ]);
    for (const place of partials) {
      expect(place.flu).toBeNull();
      expect(place.fluGap).toMatch(/left blank|not a city FLUM|not used/i);
    }
    const shores = partials.find((place) => place.id === "daytona-beach-shores");
    const beverly = partials.find((place) => place.id === "beverly-beach");
    expect(shores?.zoning?.fields).toEqual(["ZoningCode"]);
    expect(beverly?.zoning?.fields).toEqual(["ZONECODE"]);
    for (const id of ["debary", "new-smyrna-beach", "orange-city", "lake-helen", "pierson"]) {
      const place = partials.find((item) => item.id === id);
      expect(place?.join).toBe("countywide");
      expect(place?.zoning).toBeNull();
      expect(place?.countywideJurisd).toBeTruthy();
    }
    expect(catalog.countywideZoning.fields).toEqual(["OriginalZoningCode"]);
    expect(catalog.countywideZoning.filterField).toBe("JURISD");
  });

  it("rejects Seattle, Volusia 999 stubs, and the DeBary county FLU dump", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.stubZoningCodes).toEqual(["999"]);
    const banned = [
      "https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/Future_Land_Use__2035/FeatureServer/0",
      "https://maps5.vcgov.org/arcgis/rest/services/Open_Data/Open_Data_4/FeatureServer/36",
      "https://maps5.vcgov.org/arcgis/rest/services/Debary/MapServer/21",
      "https://services5.arcgis.com/tHety5Dlgpjia0CW/arcgis/rest/services/Zoning/FeatureServer/160/query",
    ];
    for (const url of banned) {
      expect(isBlockedServiceUrl(catalog, url)).toBe(true);
    }
    for (const place of catalog.places) {
      for (const url of layerUrls(place)) {
        expect(isBlockedServiceUrl(catalog, url)).toBe(false);
      }
    }
    expect(catalog.flaglerHost.host).toBe("https://gis.palmcoast.gov");
    expect(catalog.flaglerHost.note).toMatch(/AGISO_FlaglerZoning/);
  });

  it("reads published fields and drops 999 stubs", () => {
    const daytona = wireReadyPlaces(catalog)[0];
    expect(
      readOverlayValue(
        catalog,
        { NewZoningClassification: "SFR-5", ZONECLASS: "OLD" },
        daytona.zoning!.fields,
        daytona.zoning!.labelFields,
      ),
    ).toEqual({ code: "SFR-5", label: null });
    expect(readOverlayValue(catalog, { ZONCODE: "999", ZONECLASS: "R-3" }, ["ZONCODE", "ZONECLASS"])).toEqual({
      code: "R-3",
      label: null,
    });
    expect(readOverlayValue(catalog, { ZONCODE: "999" }, ["ZONCODE"])).toBeNull();
    expect(isStubZoningCode(catalog, "999")).toBe(true);
    const marineland = wireReadyPlaces(catalog).find((place) => place.id === "marineland");
    expect(marineland?.zoning?.fields).toEqual(["FLU"]);
    expect(marineland?.zoning?.url).not.toBe(marineland?.flu?.url);
    expect(readOverlayValue(catalog, { FLU: "Conservation" }, marineland!.zoning!.fields)).toEqual({
      code: "Conservation",
      label: null,
    });
  });

  it("prefers a parcel id join for Holly Hill, then the most local city polygon", () => {
    const holly = catalog.places.find((place) => place.id === "holly-hill");
    expect(holly?.join).toBe("attribute-then-spatial");
    expect(holly?.zoning?.idFields).toEqual(["PID", "ALTKEY"]);
    expect(hollyHillAttributeKeys("000424240320040")).toEqual(["000424240320040", "424240320040"]);

    const attribute = hit({ placeId: "holly-hill", areaSqM: 1, code: "R-2", layerUrl: holly!.zoning!.attributeUrl! });
    const other = hit({ placeId: "daytona-beach", areaSqM: 10, code: "SFR-5" });
    expect(
      resolveZoningHit({
        attributeHit: attribute,
        cityHits: [other],
        unincorporatedHit: null,
        countywideHit: hit({ placeId: "debary", areaSqM: 5, kind: "city", status: "partial", code: "A-2" }),
      })?.code,
    ).toBe("R-2");

    expect(
      resolveZoningHit({
        attributeHit: null,
        cityHits: [
          hit({ placeId: "port-orange", areaSqM: 800, code: "NP" }),
          hit({ placeId: "daytona-beach-shores", areaSqM: 40, status: "partial", rank: 20, code: "GC-1" }),
        ],
        unincorporatedHit: hit({ placeId: "flagler-unincorporated", areaSqM: 5, kind: "unincorporated", code: "AG" }),
        countywideHit: hit({ placeId: "debary", areaSqM: 1, status: "partial", code: "A-2" }),
      })?.placeId,
    ).toBe("daytona-beach-shores");
  });

  it("does not treat CountywideZoning as a substitute for a city that has its own layer", () => {
    expect(placeForCountywideJurisd(catalog, "Daytona Beach")).toBeNull();
    expect(placeForCountywideJurisd(catalog, "DeBary")?.id).toBe("debary");
    expect(placeForCountywideJurisd(catalog, "Daytona Beach Shores")?.countywideFallback).toBe("Daytona Beach Shores");
    expect(placeForCountywideJurisd(catalog, "New Smyrna Beach")?.flu).toBeNull();
    const city = hit({ placeId: "daytona-beach", areaSqM: 100, code: "SFR-5" });
    expect(
      resolveZoningHit({
        attributeHit: null,
        cityHits: [city],
        unincorporatedHit: null,
        countywideHit: hit({ placeId: "daytona-beach", areaSqM: 10, code: "AG" }),
      })?.code,
    ).toBe("SFR-5");
  });

  it("does not borrow future land use across a city gap or from a neighbor", () => {
    const debaryFlu = resolveFluHit(catalog, "debary", [
      hit({ placeId: "daytona-beach", areaSqM: 20, code: "L1 - R" }),
    ]);
    expect(debaryFlu).toBeNull();
    expect(fluEmptyForMunicipal(placeForCountywideJurisd(catalog, "DeBary")?.fluGap)).toMatch(/not used/);

    const shores = resolveFluHit(catalog, "daytona-beach-shores", [
      hit({ placeId: "port-orange", areaSqM: 15, code: "MU" }),
    ]);
    expect(shores).toBeNull();

    const sameCity = resolveFluHit(catalog, "daytona-beach", [
      hit({ placeId: "port-orange", areaSqM: 5, code: "MU" }),
      hit({ placeId: "daytona-beach", areaSqM: 80, code: "L1 - R" }),
    ]);
    expect(sameCity?.code).toBe("L1 - R");

    const fluOnly = resolveFluHit(catalog, null, [
      hit({ placeId: "palm-coast", areaSqM: 400, code: "RES" }),
      hit({ placeId: "flagler-beach", areaSqM: 30, code: "LOW" }),
    ]);
    expect(fluOnly?.placeId).toBe("flagler-beach");
    expect(mostLocalHit([])).toBeNull();
  });

  it("uses Palm Coast as the host for Flagler city and unincorporated layers", () => {
    const flagler = catalog.places.filter((place) => place.countyFips === "12035");
    expect(flagler.map((place) => place.id)).toEqual([
      "palm-coast",
      "flagler-beach",
      "bunnell",
      "marineland",
      "flagler-unincorporated",
      "beverly-beach",
    ]);
    for (const place of flagler) {
      for (const url of layerUrls(place)) {
        expect(url.startsWith("https://gis.palmcoast.gov/")).toBe(true);
      }
    }
    const uninc = catalog.places.find((place) => place.id === "flagler-unincorporated");
    expect(uninc?.zoning?.url).toMatch(/AGISO_FlaglerZoning\/MapServer\/0$/);
    expect(uninc?.flu?.url).toMatch(/AGISO_FlaglerFLU\/MapServer\/0$/);
    expect(zoningEmptyForCounty("12127", "fallback")).toBe("No municipal zoning polygon covers this parcel.");
    expect(zoningEmptyForCounty("12095", "Not on the OCPA parcel")).toBe("Not on the OCPA parcel");
  });
});

describe("joined Volusia parcels", () => {
  const summary = JSON.parse(
    readFileSync(path.join(process.cwd(), "data/fixtures/volusia-flagler-municipal-join.json"), "utf8"),
  ) as {
    opportunityZonesInvented: number;
    rejectedNotUsed: string[];
    baselines: {
      "market-12127": { zoning: number; flu: number };
      "flagler-12035": { present: boolean; parcels: number };
    };
    byPlace: Record<string, { zoning: number; flu: number }>;
  };

  it("stamps city codes and leaves partial future land use blank", () => {
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.baselines["market-12127"].zoning).toBeGreaterThan(2000);
    expect(summary.baselines["market-12127"].flu).toBeGreaterThan(1000);
    expect(summary.baselines["flagler-12035"].present).toBe(false);
    expect(summary.baselines["flagler-12035"].parcels).toBe(0);
    for (const id of [
      "daytona-beach",
      "port-orange",
      "ormond-beach",
      "deltona",
      "deland",
      "edgewater",
      "south-daytona",
      "holly-hill",
      "oak-hill",
      "ponce-inlet",
    ]) {
      expect(summary.byPlace[id]?.zoning).toBeGreaterThan(0);
      expect(summary.byPlace[id]?.flu).toBeGreaterThan(0);
    }
    for (const id of ["daytona-beach-shores", "debary", "new-smyrna-beach", "orange-city", "lake-helen", "pierson"]) {
      expect(summary.byPlace[id]?.zoning).toBeGreaterThan(0);
      expect(summary.byPlace[id]?.flu).toBe(0);
    }
    expect(summary.rejectedNotUsed.some((url) => url.includes("Future_Land_Use__2035"))).toBe(true);
    expect(summary.rejectedNotUsed.some((url) => url.includes("Open_Data_4/FeatureServer/36"))).toBe(true);
    expect(summary.rejectedNotUsed.some((url) => url.includes("Debary/MapServer/21"))).toBe(true);
  });

  it("does not write stub districts, rejected layers, or city FLU for partial places", () => {
    const portOrange = catalog.places.find((place) => place.id === "port-orange");
    expect(portOrange?.zoning?.labelFields).toEqual([]);
    expect(portOrange?.flu?.labelFields).toEqual([]);
    const tiles = readdirSync(path.join(process.cwd(), "data/fixtures/market-parcels/counties/12127/tiles")).filter((name) =>
      name.endsWith(".geojson"),
    );
    let stamped = 0;
    for (const name of tiles) {
      const collection = JSON.parse(
        readFileSync(path.join(process.cwd(), "data/fixtures/market-parcels/counties/12127/tiles", name), "utf8"),
      ) as { features: { properties: Record<string, unknown> }[] };
      for (const feature of collection.features) {
        const props = feature.properties;
        const municipal = props.municipal as
          | { placeId?: string; fluGap?: string | null; zoningLayer?: string | null; fluLayer?: string | null; zoningLabel?: string | null }
          | undefined;
        if (!municipal) continue;
        stamped += 1;
        expect(props.zoningCode).not.toBe("999");
        if (municipal.placeId === "port-orange") expect(municipal.zoningLabel ?? null).toBeNull();
        const flu = props.flu as { code?: string; label?: string; source?: string } | null;
        if (municipal.fluGap) expect(flu?.code ?? null).toBeNull();
        if (municipal.placeId === "port-orange" && flu?.label) {
          expect(flu.label).not.toMatch(/Comprehensive Plan/i);
        }
        for (const layer of [municipal.zoningLayer, municipal.fluLayer, flu?.source]) {
          expect(layer ?? "").not.toContain("Future_Land_Use__2035");
          expect(layer ?? "").not.toContain("Open_Data_4/FeatureServer/36");
          expect(layer ?? "").not.toContain("Debary/MapServer/21");
        }
      }
    }
    expect(stamped).toBeGreaterThan(2000);
  });
});
