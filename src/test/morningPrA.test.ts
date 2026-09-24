import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { aadtEmptyMessage, aadtFieldLabel, showAadtField } from "../lib/format";

const PRIORITY = [
  "37119",
  "37183",
  "37063",
  "13121",
  "13067",
  "13089",
  "13185",
  "13021",
  "45019",
  "45035",
  "45015",
  "45013",
  "47037",
  "28049",
  "28089",
  "28121",
];

describe("state-agnostic AADT labels", () => {
  it("keeps FDOT wording on Florida and uses Nearest AADT elsewhere", () => {
    expect(aadtFieldLabel("Florida")).toBe("Nearest FDOT AADT");
    expect(aadtFieldLabel("Georgia")).toBe("Nearest AADT");
    expect(aadtFieldLabel("North Carolina")).toBe("Nearest AADT");
    expect(aadtEmptyMessage("Georgia")).not.toMatch(/FDOT/);
    expect(showAadtField("Alabama", false)).toBe(false);
    expect(showAadtField("Florida", false)).toBe(true);
    expect(showAadtField("Georgia", true)).toBe(true);
  });
});

describe("priority county traffic fixture", () => {
  it("joins a positive count for each stamped county and does not label those roads FDOT", () => {
    const meta = JSON.parse(readFileSync("data/fixtures/signals-meta.json", "utf8"));
    const byCounty = meta.stateAadtByCounty as Record<string, number>;
    for (const fips of PRIORITY) {
      expect(byCounty[fips], fips).toBeGreaterThan(0);
    }
    const raw = readFileSync("data/fixtures/aadt-state-dots.geojson", "utf8");
    expect(raw).not.toMatch(/FDOT/);
    expect(raw).toContain('"countyFips":"45019"');
    expect(raw).toContain('"countyFips":"28089"');
    expect(raw).toContain('"countyFips":"13067"');
  });
});

describe("Jefferson County unincorporated zoning", () => {
  it("fills ZNCODE only where the parcel had no city code", () => {
    const summary = JSON.parse(
      readFileSync("data/fixtures/market-parcels/counties/01073/zoning-join.json", "utf8"),
    );
    expect(summary.field).toBe("ZNCODE");
    expect(summary.source).toContain("FutureLandUse/FeatureServer/4");
    expect(summary.cityKept).toBe(2124);
    expect(summary.unincorporatedFilled).toBeGreaterThan(1000);
    const county = JSON.parse(readFileSync("data/fixtures/market-parcels/counties/01073/county.json", "utf8"));
    expect(county.gaps.join("\n")).toContain("ZNCODE");
    expect(county.gaps.join("\n")).not.toContain("No zoning join");
  });
});
