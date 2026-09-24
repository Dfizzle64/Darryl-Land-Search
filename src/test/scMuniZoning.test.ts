import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const reportPath = path.join(process.cwd(), "data/fixtures/market-parcels/sc-muni-zoning.json");
const countyRoot = path.join(process.cwd(), "data/fixtures/market-parcels/counties");

type CityRow = { joined: number; status: string; note: string };
type CountyReport = {
  fips: string;
  parcels: number;
  zoningJoined: number;
  fluJoined: number;
  bySource: Record<string, number>;
  cities: Record<string, CityRow>;
  samples: { source: string; parcelId: string; zoningCode: string; acreage: number }[];
  codes: Record<string, string[]>;
  queried: string[];
  gaps: string[];
};
type Report = {
  band: { min: number; max: number; inclusive: boolean };
  opportunityZones: string;
  rejected: { name: string; reason: string }[];
  honestGaps: string[];
  counties: Record<string, CountyReport>;
};

const BANNED = [
  "ZoningFireSewer",
  "SimpsonvilleZoning",
  "xKvDQ9PmaqgzOpn2",
  "New_FI_Zoning_Swipe",
  "City_of_Folly_Beach_Zoning",
  "Greenville_Base_Data",
  "/PDD/",
  "Zoning_2025",
];

function loadReport(): Report {
  expect(existsSync(reportPath)).toBe(true);
  return JSON.parse(readFileSync(reportPath, "utf8")) as Report;
}

describe("South Carolina municipal zoning joins", () => {
  it("documents rejected traps and the remaining municipal gaps", () => {
    const report = loadReport();
    expect(report.band).toEqual({ min: 5, max: 150, inclusive: true });
    expect(report.opportunityZones).toMatch(/not designated/i);
    const rejected = report.rejected.map((item) => `${item.name} ${item.reason}`).join("\n");
    expect(rejected).toMatch(/Shelby/i);
    expect(rejected).toMatch(/ZoningFireSewer/);
    expect(rejected).toMatch(/Sullivan/i);
    const gaps = report.honestGaps.join("\n");
    expect(gaps).toMatch(/James Island/);
    expect(gaps).toMatch(/Mauldin/);
    expect(gaps).toMatch(/Simpsonville/);
    expect(gaps).toMatch(/Travelers Rest/);
    expect(gaps).not.toMatch(/designated Opportunity Zones are/i);
    for (const county of Object.values(report.counties)) {
      for (const url of county.queried) {
        for (const fragment of BANNED) {
          expect(url.includes(fragment)).toBe(false);
        }
      }
    }
  });

  it("joins usable city layers and leaves Sullivan's Island, James Island, and IOP PDD empty", () => {
    const report = loadReport();
    const greenville = report.counties["45045"];
    const charleston = report.counties["45019"];
    const berkeley = report.counties["45015"];
    const dorchester = report.counties["45035"];
    expect(greenville.parcels).toBeGreaterThan(1570);
    expect(greenville.cities["Fountain Inn"].joined).toBeGreaterThan(0);
    expect(greenville.cities["Fountain Inn"].status).toBe("usable");
    expect(greenville.cities["City of Greenville"].joined).toBeGreaterThan(0);
    expect(greenville.cities["Greer"].joined).toBeGreaterThan(0);
    expect(greenville.cities.Mauldin.status).toBe("no-city-rest");
    expect(greenville.cities.Simpsonville.status).toBe("no-city-rest");
    expect(greenville.cities["Travelers Rest"].status).toBe("no-city-rest");
    expect(greenville.codes["fountain-inn"] ?? []).not.toContain("R-7.5");
    expect(greenville.codes["fountain-inn"] ?? []).not.toContain("R-20");
    expect(greenville.fluJoined).toBeGreaterThan(0);

    expect(charleston.cities["Folly Beach"].joined).toBeGreaterThan(0);
    expect(charleston.cities["Isle of Palms"].status).toBe("partial");
    expect(charleston.cities["Isle of Palms"].joined).toBeGreaterThan(0);
    expect(charleston.cities.Summerville.joined).toBeGreaterThan(0);
    expect(charleston.cities["City of Charleston"].joined).toBeGreaterThan(0);
    expect(charleston.cities["Sullivan's Island"].joined).toBe(0);
    expect(charleston.cities["Sullivan's Island"].status).toBe("gap");
    expect(charleston.cities["James Island"].joined).toBe(0);
    expect(JSON.stringify(charleston.bySource)).not.toMatch(/PDD/);
    expect(charleston.fluJoined).toBeGreaterThan(0);

    expect(berkeley.cities["Goose Creek"].joined).toBeGreaterThan(0);
    expect(berkeley.cities.Hanahan.joined).toBeGreaterThan(0);
    expect(berkeley.cities["Moncks Corner"].joined).toBeGreaterThan(0);
    expect(berkeley.fluJoined).toBe(0);

    expect(dorchester.parcels).toBe(6774);
    expect(dorchester.cities.Summerville.joined).toBeGreaterThan(0);
    expect(dorchester.cities["Dorchester County"].joined).toBeGreaterThan(0);
    expect(dorchester.zoningJoined).toBeGreaterThan(6000);
    expect(dorchester.fluJoined).toBe(0);
  });

  it("keeps the inclusive acreage band and does not invent opportunity zones", () => {
    const report = loadReport();
    for (const fips of ["45015", "45019", "45035", "45045"]) {
      const tiles = path.join(countyRoot, fips, "tiles");
      const files = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
      expect(files.length).toBeGreaterThan(0);
      let seen = 0;
      for (const file of files) {
        const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as ParcelCollection;
        for (const feature of collection.features) {
          expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
          expect(feature.properties.countyFips).toBe(fips);
          expect(feature.properties.opportunityZone).toBeNull();
          expect(feature.properties.oz2Eligibility).toBeNull();
          expect(feature.properties.marketIds?.includes("Orlando")).toBe(false);
          seen += 1;
        }
      }
      expect(seen).toBe(report.counties[fips].parcels);
    }

    const lookup = JSON.parse(readFileSync(path.join(countyRoot, "45035/lookup.json"), "utf8")) as Record<string, string>;
    const tile = lookup["118-00-00-092"];
    const collection = JSON.parse(
      readFileSync(path.join(countyRoot, "45035/tiles", `${tile}.geojson`), "utf8"),
    ) as ParcelCollection;
    const kept = collection.features.find((feature) => feature.properties.parcelId === "118-00-00-092");
    expect(kept?.properties.acreage).toBe(149.9458);

    const greenville = JSON.parse(readFileSync(path.join(countyRoot, "45045/county.json"), "utf8")) as { source: string; coverage: string };
    expect(greenville.source).toBe("sc-greenville-county-tax-parcels");
    expect(greenville.coverage).toBe("complete-gte-5ac");
    const charleston = JSON.parse(readFileSync(path.join(countyRoot, "45019/county.json"), "utf8")) as { source: string; coverage: string };
    expect(charleston.source).toBe("sc-charleston-energov-ent");
    expect(charleston.coverage).toBe("complete-gte-5ac");
  });
});
