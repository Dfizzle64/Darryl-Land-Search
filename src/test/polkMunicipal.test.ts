import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  fluEmptyForPolk,
  isBlockedServiceUrl,
  isPolkParcelKey,
  isStubCode,
  layerUrls,
  readOverlayValue,
  resolvePolkFlu,
  resolvePolkHit,
  wireReadyPlaces,
  zoningEmptyForPolk,
  type PolkCatalog,
  type PolkOverlayHit,
} from "../lib/polkMunicipal";

const catalog = JSON.parse(readFileSync(path.join(process.cwd(), "data/polk-municipal.json"), "utf8")) as PolkCatalog;

function hit(partial: Partial<PolkOverlayHit> & Pick<PolkOverlayHit, "placeId" | "areaSqM" | "code">): PolkOverlayHit {
  return {
    rank: 1,
    label: null,
    layerUrl: "https://example.test/layer",
    ...partial,
  };
}

describe("Polk municipal zoning and future land use", () => {
  it("wires only the five usable cities", () => {
    const places = wireReadyPlaces(catalog);
    expect(places.map((place) => place.name)).toEqual([
      "Lakeland",
      "Bartow",
      "Auburndale",
      "Lake Alfred",
      "Lake Hamilton",
    ]);
    expect(places.map((place) => place.zoning.url)).toEqual([
      "https://services1.arcgis.com/mcbQY5xNGGGM1vBX/arcgis/rest/services/Zoning/FeatureServer/0",
      "https://services8.arcgis.com/1wJDvJrOmH0GVxt1/arcgis/rest/services/Bartow_Zoning_8_25_2026/FeatureServer/1",
      "https://services3.arcgis.com/o0eokD8valYePyMB/arcgis/rest/services/Auburndale_Zoning/FeatureServer/3",
      "https://services3.arcgis.com/VaAx8WnigGGWjIPd/arcgis/rest/services/Lake_Alfred_Zoning/FeatureServer/0",
      "https://services5.arcgis.com/gutFqkMq9XlLck8D/arcgis/rest/services/Lake_Hamilton_Zoning/FeatureServer/0",
    ]);
    expect(places.map((place) => place.flu.url)).toEqual([
      "https://services1.arcgis.com/mcbQY5xNGGGM1vBX/arcgis/rest/services/Future_Land_Use/FeatureServer/0",
      "https://services8.arcgis.com/1wJDvJrOmH0GVxt1/arcgis/rest/services/Bartow_Future_Land_Use_8_25_2026/FeatureServer/2",
      "https://services3.arcgis.com/o0eokD8valYePyMB/arcgis/rest/services/Auburndale_FLU/FeatureServer/0",
      "https://services3.arcgis.com/VaAx8WnigGGWjIPd/arcgis/rest/services/Lake_Alfred_Zoning/FeatureServer/0",
      "https://services5.arcgis.com/gutFqkMq9XlLck8D/arcgis/rest/services/Lake_Hamilton_Future_Land_Use/FeatureServer/0",
    ]);
    expect(places.map((place) => place.zoning.fields)).toEqual([["LABEL"], ["ZON"], ["ZN_ABREV"], ["ZON"], ["ZON"]]);
    expect(places.map((place) => place.flu.fields)).toEqual([
      ["LABEL"],
      ["FLU"],
      ["FLU_ABREV"],
      ["FLU"],
      ["FLU"],
    ]);
    const alfred = places.find((place) => place.id === "lake-alfred");
    expect(alfred?.notWired?.[0].url).toMatch(/Planning_WFL1/);
    expect(layerUrls(alfred!)).not.toEqual(expect.arrayContaining([expect.stringMatching(/Planning_WFL1/)]));
  });

  it("keeps the other Polk cities as gaps and rejects namesakes", () => {
    expect(catalog.doNotInventOpportunityZones).toBe(true);
    expect(catalog.doNotInventCountyLdcZoning).toBe(true);
    expect(catalog.countyLdcZoning.status).toBe("gap");
    expect(catalog.countyLdcZoning.note).toMatch(/FLUNAME is not copied/);
    expect(catalog.countyFluNotStamped.url).toMatch(/Map_Land_Use_and_Zoning\/MapServer\/9/);
    expect(catalog.gaps.map((gap) => gap.name)).toEqual([
      "Winter Haven",
      "Haines City",
      "Davenport",
      "Fort Meade",
      "Dundee",
      "Eagle Lake",
      "Frostproof",
      "Mulberry",
      "Polk City",
      "Hillcrest Heights",
      "Highland Park",
      "Lake Wales",
    ]);
    expect(catalog.gaps.find((gap) => gap.id === "lake-wales")?.status).toBe("blocked");
    expect(catalog.gaps.find((gap) => gap.id === "winter-haven")?.reason).toMatch(/Gridics/);
    const banned = [
      "https://www.bartowgis.org/arcgis/rest/services/BartowZoning/FeatureServer/0",
      "https://services.example/Polk_City_Zoning_VIEW/FeatureServer/0",
      "https://services.example/HP_Zoning/FeatureServer/0",
      "https://services.example/City_of_Mulberry_Zoning/FeatureServer/0",
      "https://services.example/dundee-lez/FeatureServer/0",
      "https://services7.arcgis.com/1PZmkk2mSW5b055Q/ArcGIS/rest/services/Polk_County_Parcels/FeatureServer/0",
    ];
    for (const url of banned) {
      expect(isBlockedServiceUrl(catalog, url)).toBe(true);
    }
    for (const place of catalog.places) {
      for (const url of layerUrls(place)) {
        expect(isBlockedServiceUrl(catalog, url)).toBe(false);
      }
    }
    const script = readFileSync(path.join(process.cwd(), "scripts/join_polk_municipal.py"), "utf8");
    expect(script).not.toMatch(/bartowgis\.org/);
    expect(script).not.toMatch(/Planning_WFL1/);
    expect(script).toMatch(/doNotInventCountyLdcZoning/);
  });

  it("drops POLK_FLU stubs and short parcel ids", () => {
    const auburndale = wireReadyPlaces(catalog).find((place) => place.id === "auburndale");
    expect(readOverlayValue(catalog, { FLU_ABREV: "POLK_FLU" }, auburndale!.flu.fields)).toBeNull();
    expect(readOverlayValue(catalog, { FLU_ABREV: "RAC" }, auburndale!.flu.fields)).toEqual({
      code: "RAC",
      label: null,
    });
    expect(readOverlayValue(catalog, { LABEL: "O-1", DESIGNATIO: "Office" }, ["LABEL"], ["DESIGNATIO"])).toEqual({
      code: "O-1",
      label: "Office",
    });
    expect(readOverlayValue(catalog, { ZON: "NA" }, ["ZON"])).toEqual({ code: "NA", label: null });
    expect(isStubCode(catalog, "POLK_FLU")).toBe(true);
    expect(isStubCode(catalog, "NO ZONING INSIDE CITY")).toBe(true);
    expect(readOverlayValue(catalog, { ZN_ABREV: "NO ZONING INSIDE CITY" }, ["ZN_ABREV"])).toBeNull();
    expect(isPolkParcelKey("10")).toBe(false);
    expect(isPolkParcelKey("252733301800000100")).toBe(true);
    expect(isPolkParcelKey("262901663565001300")).toBe(true);
  });

  it("prefers a parcel-id hit and keeps future land use on that city", () => {
    const attribute = hit({ placeId: "bartow", areaSqM: 0, code: "C-3", rank: 2 });
    const spatial = hit({ placeId: "lakeland", areaSqM: 10, code: "C-1", rank: 1 });
    expect(resolvePolkHit(attribute, [spatial])?.code).toBe("C-3");
    expect(resolvePolkHit(null, [spatial, hit({ placeId: "bartow", areaSqM: 50, code: "R-1", rank: 2 })])?.code).toBe(
      "C-1",
    );
    const fluBartow = hit({ placeId: "bartow", areaSqM: 20, code: "COM", rank: 2 });
    const fluLakeland = hit({ placeId: "lakeland", areaSqM: 5, code: "MCC", rank: 1 });
    expect(resolvePolkFlu("bartow", null, [fluLakeland, fluBartow])?.code).toBe("COM");
    expect(resolvePolkFlu("lakeland", fluBartow, [fluLakeland])?.placeId).toBe("lakeland");
    expect(resolvePolkFlu(null, fluBartow, [fluLakeland])?.placeId).toBe("bartow");
  });

  it("stamps the five cities onto the existing shelf without a county zoning layer", () => {
    const summary = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/fixtures/polk-municipal-join.json"), "utf8"),
    ) as {
      parcels: number;
      zoning: number;
      flu: number;
      byPlace: Record<string, { zoning: number; flu: number }>;
      examples: Record<string, { parcelId: string; tile: string; zoningCode: string; flu: string }>;
      opportunityZonesInvented: number;
      countyLdcZoning: string;
      countyFluStamped: boolean;
      notWired: string[];
    };
    expect(summary.parcels).toBe(19734);
    expect(summary.zoning).toBe(1696);
    expect(summary.flu).toBe(1735);
    expect(summary.opportunityZonesInvented).toBe(0);
    expect(summary.countyLdcZoning).toBe("gap");
    expect(summary.countyFluStamped).toBe(false);
    expect(summary.byPlace).toEqual({
      lakeland: { zoning: 795, flu: 815 },
      bartow: { zoning: 318, flu: 318 },
      auburndale: { zoning: 262, flu: 281 },
      "lake-alfred": { zoning: 173, flu: 173 },
      "lake-hamilton": { zoning: 148, flu: 148 },
    });
    expect(summary.notWired).toEqual(catalog.gaps.map((gap) => gap.id));
    const places = new Map(wireReadyPlaces(catalog).map((place) => [place.id, place]));
    for (const [placeId, example] of Object.entries(summary.examples)) {
      const tile = JSON.parse(
        readFileSync(
          path.join(process.cwd(), "data/fixtures/orlando-parcels/tiles/12105", example.tile),
          "utf8",
        ),
      ) as { features: { properties: Record<string, unknown> }[] };
      const feature = tile.features.find((item) => item.properties.parcelId === example.parcelId);
      expect(feature?.properties.zoningCode).toBe(example.zoningCode);
      const flu = feature?.properties.flu as { code?: string; source?: string } | null;
      expect(flu?.code).toBe(example.flu);
      const municipal = feature?.properties.municipal as { placeId?: string; zoningLayer?: string };
      expect(municipal.placeId).toBe(placeId);
      expect(example.zoningCode).not.toBe("POLK_FLU");
      expect(example.zoningCode).not.toBe("NO ZONING INSIDE CITY");
      const place = places.get(placeId);
      expect(municipal.zoningLayer).toBe(place?.zoning.url);
      expect(flu?.source).toBe(place?.flu.url);
    }
  });

  it("tells the drawer the county zoning gap without inventing a code", () => {
    expect(zoningEmptyForPolk("12105", "fallback")).toMatch(/does not publish an LDC zoning-district layer/);
    expect(zoningEmptyForPolk("12095", "Not on the OCPA parcel")).toBe("Not on the OCPA parcel");
    expect(fluEmptyForPolk("12105", null, "Not joined for this county")).toMatch(/not copied in as a zoning code/);
    expect(fluEmptyForPolk("13089", null, "No future land use joined for this parcel")).toBe(
      "No future land use joined for this parcel",
    );
  });
});
