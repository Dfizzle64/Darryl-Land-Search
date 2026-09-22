import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { describeOpportunityZone, describeOz2Eligibility } from "../lib/opportunityZone";
import type { Oz2TractCollection } from "../lib/types";

describe("describeOz2Eligibility", () => {
  it("labels the Orange County rural tract as nomination-eligible and not a 2027 designation", () => {
    const described = describeOz2Eligibility({
      eligible: true,
      rural: true,
      tractGeoid: "12095016605",
      tractName: "Census Tract 166.05",
      designation: "eligible-for-nomination",
      source: "rev-proc-2026-14",
    });
    expect(described.label).toMatch(/rural-eligible/i);
    expect(described.detail).toContain("12095016605");
    expect(described.detail).toMatch(/eligible for nomination/i);
    expect(described.detail).toMatch(/has not been nominated or certified/i);
    expect(described.detail).not.toMatch(/designated as a 2027/i);
    expect(described.detail).not.toMatch(/certified as a 2027 qoz/i);
  });

  it("does not invent a rural flag when the tract is eligible but Rural Status is missing", () => {
    const described = describeOz2Eligibility({
      eligible: true,
      rural: null,
      tractGeoid: "12095010400",
      tractName: null,
      designation: "eligible-for-nomination",
      source: "rev-proc-2026-14",
    });
    expect(described.rural).toBeNull();
    expect(described.label).toBe("OZ 2.0 eligible");
    expect(described.detail).toMatch(/not labeled rural/i);
  });
});

describe("describeOpportunityZone", () => {
  it("keeps Notice 2025-50 rural status on current designations separate from OZ 2.0", () => {
    const described = describeOpportunityZone({
      inOpportunityZone: true,
      tractGeoid: "12095017600",
      tractName: "Census tract 176",
      source: "hud-fs-13",
      designatedRural: false,
    });
    expect(described.detail).toMatch(/current designated QOZ/i);
    expect(described.detail).toMatch(/Notice 2025-50 does not list/i);
    expect(described.detail).toMatch(/not a 2027 designation/i);
  });
});

describe("OZ 2.0 fixture", () => {
  it("overlays Orange County eligible tracts and flags only 12095016605 as rural", () => {
    const collection = JSON.parse(
      readFileSync("data/fixtures/oz2-eligible.geojson", "utf8"),
    ) as Oz2TractCollection;
    const rural = collection.features.filter((feature) => feature.properties.rural === true);
    const nonRural = collection.features.filter((feature) => feature.properties.rural === false);
    expect(rural.map((feature) => feature.properties.tractGeoid)).toEqual(["12095016605"]);
    expect(nonRural.length).toBeGreaterThan(80);
    expect(collection.features.every((feature) => feature.properties.designation === "eligible-for-nomination")).toBe(
      true,
    );
    expect(collection.features.every((feature) => feature.properties.source === "rev-proc-2026-14")).toBe(true);
  });
});
