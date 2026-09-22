import { describe, expect, it } from "vitest";
import { queryOrlandoFixtureParcels } from "../lib/data/orlandoParcelStore";
import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import path from "node:path";
import {
  bboxIntersects,
  fipsForOrlandoCountyFilter,
  fipsIntersectingBbox,
  isFull5AcCounty,
  ORLANDO_FULL_5AC_COUNTIES,
  ORLANDO_PARCEL_TILE,
  ORLANDO_SHED_COUNTIES,
  showOrangeCountyPilot,
  showOrlandoParcels,
  spatiallyThinFeatures,
  tileIndicesForBbox,
} from "../lib/orlandoParcels";
import type { OrlandoParcelsMeta, ParcelCollection, ParcelFeature } from "../lib/types";

const FULL_MINIMUMS: Record<string, number> = {
  Lake: 15000,
  Orange: 12000,
  Osceola: 5500,
  Polk: 18000,
  Seminole: 4000,
};

function featuresForCounty(county: OrlandoParcelsMeta["counties"][number]): ParcelFeature[] {
  if (county.partition === "tiles") {
    const dir = county.path;
    const names = readdirSync(dir).filter((name) => name.endsWith(".geojson"));
    return names.flatMap((name) => {
      const collection = JSON.parse(readFileSync(path.join(dir, name), "utf8")) as ParcelCollection;
      return collection.features;
    });
  }
  const collection = JSON.parse(readFileSync(county.path, "utf8")) as ParcelCollection;
  return collection.features;
}

describe("Orlando shed parcels", () => {
  it("lists all nine authoritative shed counties", () => {
    expect(ORLANDO_SHED_COUNTIES.map((c) => c.name).sort()).toEqual(
      ["Brevard", "Lake", "Marion", "Orange", "Osceola", "Polk", "Seminole", "Sumter", "Volusia"].sort(),
    );
  });

  it("shows parcels for Orlando shed counties and keeps Orange pilot helpers", () => {
    expect(showOrlandoParcels("Orlando", null, null)).toBe(true);
    expect(showOrlandoParcels("Orlando", "Polk", "Florida")).toBe(true);
    expect(showOrlandoParcels("Orlando", "Seminole", "Florida")).toBe(true);
    expect(showOrlandoParcels("Atlanta", null, null)).toBe(false);
    expect(showOrangeCountyPilot("Orlando", "Polk", "Florida")).toBe(false);
    expect(showOrangeCountyPilot("Orlando", "Orange", "Florida")).toBe(true);
  });

  it("routes FIPS for county filter and bbox intersection", () => {
    expect(fipsForOrlandoCountyFilter("Lake", "Florida")).toEqual(["12069"]);
    expect(fipsForOrlandoCountyFilter(null, null)).toHaveLength(9);
    expect(bboxIntersects([-81.5, 28.4, -81.2, 28.6], [-81.4, 28.5, -81.3, 28.7])).toBe(true);
    expect(fipsIntersectingBbox([-81.4, 28.5, -81.2, 28.7], ["12095", "12009"])).toEqual(["12095"]);
  });

  it("keeps the tile grid aligned with the seed script", () => {
    expect(ORLANDO_PARCEL_TILE).toEqual({ originLon: -83, originLat: 27, tileDeg: 0.25 });
    expect(tileIndicesForBbox([-81.5, 28.4, -81.2, 28.7])).toEqual({ ix0: 6, ix1: 7, iy0: 5, iy1: 6 });
    expect(isFull5AcCounty("Polk")).toBe(true);
    expect(isFull5AcCounty("Brevard")).toBe(false);
    expect([...ORLANDO_FULL_5AC_COUNTIES]).toEqual(["Lake", "Orange", "Osceola", "Polk", "Seminole"]);
    const thinned = spatiallyThinFeatures(
      [
        { properties: { centroid: [-81.5, 28.5] as [number, number], acreage: 9 } },
        { properties: { centroid: [-81.5, 28.5] as [number, number], acreage: 4 } },
        { properties: { centroid: [-81.2, 28.7] as [number, number], acreage: 6 } },
      ],
      2,
    );
    expect(thinned).toHaveLength(2);
    expect(thinned.map((item) => item.properties.acreage).sort()).toEqual([6, 9]);
  });

  it("ships complete 5–150 acre fixtures for the five core counties and samples for the rest", () => {
    const meta = JSON.parse(readFileSync("data/fixtures/orlando-parcels/meta.json", "utf8")) as OrlandoParcelsMeta;
    expect(meta.market).toBe("Orlando");
    expect(meta.counties).toHaveLength(9);
    expect(meta.coreMinAcres).toBe(5);
    expect(meta.coreMaxAcres).toBe(150);
    expect(meta.tile).toEqual(ORLANDO_PARCEL_TILE);
    expect(meta.parcelCount).toBe(meta.counties.reduce((sum, county) => sum + county.featureCount, 0));
    for (const county of meta.counties) {
      expect(existsSync(county.path)).toBe(true);
      expect(statSync(county.path).isDirectory()).toBe(county.partition === "tiles");
      const features = featuresForCounty(county);
      expect(features.length).toBe(county.featureCount);
      expect(features.length).toBeGreaterThan(0);
      const sample = features[0].properties;
      expect(sample.countyFips).toBe(county.fips);
      expect(sample.countyName).toBe(county.name);
      expect(sample.centroid).toHaveLength(2);
      expect(sample.source).toBeTruthy();
      if (county.coverage === "complete-gte-5ac") {
        expect(FULL_MINIMUMS[county.name]).toBeGreaterThan(0);
        expect(features.length).toBeGreaterThanOrEqual(FULL_MINIMUMS[county.name]);
        expect(
          features.every((feature) => {
            const acres = feature.properties.acreage ?? 0;
            return acres >= 5 && acres <= 150;
          }),
        ).toBe(true);
        expect(county.maxAcres).toBe(150);
        expect(county.partition).toBe("tiles");
        expect(existsSync(path.join("data/fixtures/orlando-parcels/lookup", `${county.fips}.json`))).toBe(true);
      } else {
        expect(county.coverage).toBe("sample");
        expect(county.partition).toBe("file");
        expect(features.length).toBeGreaterThan(50);
        expect(features.length).toBeLessThan(500);
      }
    }
    const orange = meta.counties.find((county) => county.name === "Orange");
    expect(orange?.zoningJoinedCount ?? 0).toBeGreaterThan(1000);
    expect(orange?.fluJoinedCount ?? 0).toBeGreaterThan(1000);
  });

  it("returns only centroids inside an area-of-interest bbox", async () => {
    const bbox = [-81.45, 28.45, -81.3, 28.55] as [number, number, number, number];
    const page = await queryOrlandoFixtureParcels({
      bbox,
      county: "Orange",
      state: "Florida",
      limit: 8000,
    });
    expect(page.totalInBbox).toBeGreaterThan(0);
    expect(page.collection.features.length).toBeGreaterThan(0);
    expect(page.collection.features.length).toBeLessThanOrEqual(page.totalInBbox);
    for (const feature of page.collection.features) {
      const [lon, lat] = feature.properties.centroid;
      expect(lon).toBeGreaterThanOrEqual(bbox[0]);
      expect(lon).toBeLessThanOrEqual(bbox[2]);
      expect(lat).toBeGreaterThanOrEqual(bbox[1]);
      expect(lat).toBeLessThanOrEqual(bbox[3]);
      expect(feature.properties.acreage ?? 0).toBeGreaterThanOrEqual(5);
      expect(feature.properties.acreage ?? 0).toBeLessThanOrEqual(150);
    }
  });
});
