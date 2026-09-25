import { describe, expect, it } from "vitest";
import {
  annotateViewportTract,
  buildTigerQuery,
  buildTractAttributeIndex,
  CENSUS_TRACTS_SOURCE,
  maxAllowableOffset,
  mergeTractFeatures,
  normalizeTigerFeature,
  parseTigerCollection,
  stampKnownIncome,
  stateNameFromFips,
  TRACT_MIN_ZOOM,
  TRACT_TILE_DEGREES,
  tractTilesForBbox,
  tractsVisibleAtZoom,
  viewportTractPlace,
  type ViewportTractFeature,
} from "../lib/censusTracts";

function polygon(geoid: string, income?: number): ViewportTractFeature {
  return {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 0],
        ],
      ],
    },
    properties: {
      tractGeoid: geoid,
      name: "Census Tract 1",
      stateName: "Florida",
      county: null,
      state: "Florida",
      ...(income ? { medianHouseholdIncome: income } : {}),
    },
  };
}

describe("census tract viewport", () => {
  it("starts tract outlines at county scale and not at a national zoom", () => {
    expect(TRACT_MIN_ZOOM).toBe(8);
    expect(tractsVisibleAtZoom(7.9)).toBe(false);
    expect(tractsVisibleAtZoom(8)).toBe(true);
    expect(tractTilesForBbox([-125, 24, -67, 49])).toHaveLength(12);
    const orlando = tractTilesForBbox([-81.6, 28.2, -81.1, 28.7]);
    expect(orlando).toHaveLength(1);
    expect(orlando[0][2] - orlando[0][0]).toBeLessThanOrEqual(TRACT_TILE_DEGREES + 0.001);
  });

  it("queries the Census 2020 tract layer by bounding box", () => {
    const url = buildTigerQuery([-81.5, 28.4, -81.2, 28.6], 9);
    expect(url.startsWith(CENSUS_TRACTS_SOURCE)).toBe(true);
    expect(url).toContain("MapServer/6/query");
    expect(url).toContain("geometry=-81.5%2C28.4%2C-81.2%2C28.6");
    expect(url).toContain(`maxAllowableOffset=${maxAllowableOffset(9)}`);
    expect(url).not.toContain("B19013");
    expect(maxAllowableOffset(8)).toBeGreaterThan(maxAllowableOffset(13));
  });

  it("normalizes a TIGER feature and leaves unknown tracts as outlines", () => {
    const feature = normalizeTigerFeature({
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 0],
          ],
        ],
      },
      properties: { GEOID: "12095015204", NAME: "Census Tract 152.04", STATE: "12", COUNTY: "095" },
    });
    expect(feature?.properties.tractGeoid).toBe("12095015204");
    expect(feature?.properties.state).toBe("Florida");
    expect(feature?.properties.rural).toBeUndefined();
    expect(feature?.properties.eligible).toBeUndefined();
    expect(feature?.properties.medianHouseholdIncome).toBeUndefined();
    expect(feature?.properties.designatedQoz).toBeUndefined();
    expect(stateNameFromFips("47")).toBe("Tennessee");
    expect(parseTigerCollection({ features: [] })).toEqual([]);
  });

  it("joins ACS income and OZ attributes only when the GEOID is already known", () => {
    const income = new Map<string, number>([["12095016605", 61234]]);
    const [stamped] = stampKnownIncome([polygon("12095016605"), polygon("12095019999")], income);
    expect(stamped.properties.medianHouseholdIncome).toBe(61234);
    const unknown = stampKnownIncome([polygon("12095019999")], income)[0];
    expect(unknown.properties.medianHouseholdIncome).toBeUndefined();
    expect(stampKnownIncome([polygon("12095016605")], new Map([["12095016605", 0]]))[0].properties.medianHouseholdIncome).toBe(
      undefined,
    );

    const index = buildTractAttributeIndex({
      rural: {
        features: [
          {
            properties: {
              tractGeoid: "12095016605",
              county: "Orange",
              state: "Florida",
              rural: true,
              medianHouseholdIncome: 61234,
            },
          },
        ],
      },
      designated: {
        features: [{ properties: { tractGeoid: "12095017600", county: "Orange", state: "Florida", rural: false } }],
      },
    });
    const joined = annotateViewportTract(polygon("12095016605"), index);
    expect(joined.properties.eligible).toBe(true);
    expect(joined.properties.rural).toBe(true);
    expect(joined.properties.county).toBe("Orange");
    expect(joined.properties.medianHouseholdIncome).toBe(61234);
    expect(viewportTractPlace(joined.properties)).toBe("Orange County, Florida");

    const outline = annotateViewportTract(polygon("06037000100"), index);
    expect(outline.properties.eligible).toBeUndefined();
    expect(outline.properties.rural).toBeUndefined();
    expect(outline.properties.medianHouseholdIncome).toBeUndefined();
    expect(outline.properties.designatedQoz).toBeUndefined();

    const designated = annotateViewportTract(polygon("12095017600"), index);
    expect(designated.properties.designatedQoz).toBe(true);
    expect(designated.properties.eligible).toBeUndefined();
  });

  it("does not paint a non-nominated South Carolina tract as eligible", () => {
    const index = buildTractAttributeIndex({
      eligible: {
        features: [
          {
            properties: {
              tractGeoid: "45019000100",
              county: "Charleston",
              state: "South Carolina",
              rural: false,
            },
          },
        ],
      },
    });
    const feature = annotateViewportTract(
      {
        ...polygon("45019000100"),
        properties: { ...polygon("45019000100").properties, state: "South Carolina", stateName: "South Carolina" },
      },
      index,
    );
    expect(feature.properties.eligible).toBeUndefined();
    expect(feature.properties.rural).toBeUndefined();
    expect(feature.properties.county).toBe("Charleston");
  });

  it("keeps one geometry per GEOID when tiles overlap", () => {
    const merged = mergeTractFeatures([[polygon("12095016605")], [polygon("12095016605"), polygon("12095010400")]]);
    expect(merged.map((feature) => feature.properties.tractGeoid).sort()).toEqual(["12095010400", "12095016605"]);
  });
});
