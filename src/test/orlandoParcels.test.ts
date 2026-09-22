import { readFileSync, existsSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  bboxIntersects,
  fipsForOrlandoCountyFilter,
  fipsIntersectingBbox,
  ORLANDO_SHED_COUNTIES,
  showOrangeCountyPilot,
  showOrlandoParcels,
} from "../lib/orlandoParcels";
import type { OrlandoParcelsMeta, ParcelCollection } from "../lib/types";

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

  it("ships partitioned fixtures for every shed county", () => {
    const meta = JSON.parse(readFileSync("data/fixtures/orlando-parcels/meta.json", "utf8")) as OrlandoParcelsMeta;
    expect(meta.market).toBe("Orlando");
    expect(meta.counties).toHaveLength(9);
    expect(meta.parcelCount).toBeGreaterThan(1000);
    for (const county of meta.counties) {
      expect(existsSync(county.path)).toBe(true);
      const collection = JSON.parse(readFileSync(county.path, "utf8")) as ParcelCollection;
      expect(collection.features.length).toBe(county.featureCount);
      expect(collection.features.length).toBeGreaterThan(0);
      const sample = collection.features[0].properties;
      expect(sample.countyFips).toBe(county.fips);
      expect(sample.countyName).toBe(county.name);
      expect(sample.centroid).toHaveLength(2);
      expect(sample.source).toBeTruthy();
    }
    const orange = meta.counties.find((c) => c.name === "Orange");
    expect(orange?.featureCount).toBeGreaterThan(400);
    const beyondOrange = meta.counties.filter((c) => c.name !== "Orange");
    expect(beyondOrange.every((c) => c.featureCount > 50)).toBe(true);
  });
});
