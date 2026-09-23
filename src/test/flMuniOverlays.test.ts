import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

type CityReport = {
  id: string;
  floridaVerified: boolean;
  rejected: string | null;
  parcelsInside: number;
  zoningJoined: number;
  fluJoined: number;
  polygonCounts: { limits: number; zoning: number; flu: number };
};

type Summary = {
  cities: CityReport[];
  leftNull: string[];
  notUsed: string[];
};

const summary = JSON.parse(readFileSync("data/fixtures/fl-muni-overlays/summary.json", "utf8")) as Summary;

function city(id: string): CityReport {
  const found = summary.cities.find((item) => item.id === id);
  if (!found) throw new Error(`missing ${id}`);
  return found;
}

describe("Florida municipal overlays", () => {
  it("joins only the seven closed cities and leaves Pensacola null", () => {
    expect(summary.cities.map((item) => item.id)).toEqual([
      "sanford",
      "kissimmee",
      "clermont",
      "mount-dora",
      "sanibel",
      "fort-myers",
      "bonita-springs",
    ]);
    expect(summary.cities.some((item) => item.id === "pensacola" || item.id === "edgewood")).toBe(false);
    expect(summary.leftNull.join(" ")).toMatch(/Pensacola/);
    expect(summary.notUsed.join(" ")).toMatch(/Edgewood, Texas/);
  });

  it("geo-verifies every closed city in Florida", () => {
    for (const item of summary.cities) {
      expect(item.floridaVerified).toBe(true);
      expect(item.rejected).toBeNull();
      expect(item.polygonCounts.zoning).toBeGreaterThan(0);
      expect(item.polygonCounts.flu).toBeGreaterThan(0);
    }
  });

  it("stamps Central Florida shelf parcels and leaves Lee at zero until parcels exist", () => {
    expect(city("sanford").zoningJoined).toBeGreaterThan(300);
    expect(city("sanford").fluJoined).toBeGreaterThan(300);
    expect(city("kissimmee").zoningJoined).toBeGreaterThan(300);
    expect(city("clermont").zoningJoined).toBeGreaterThan(150);
    expect(city("mount-dora").zoningJoined).toBeGreaterThan(100);
    for (const id of ["sanibel", "fort-myers", "bonita-springs"]) {
      expect(city(id).parcelsInside).toBe(0);
      expect(city(id).zoningJoined).toBe(0);
      expect(city(id).fluJoined).toBe(0);
    }
  });
});
