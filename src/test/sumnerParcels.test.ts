import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47165/county.json");

describe("Sumner County property search", () => {
  it("points FIPS 47165 at the public county search, not a Florida appraiser", () => {
    expect(parcelAppraiserUrl({ parcelId: "001    01700 000", countyFips: "47165" })).toEqual({
      href: "https://tn.sumner.geopowered.com/",
      label: "Open Sumner County property search",
    });
  });
});

describe("Sumner County parcel extract", () => {
  const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
    source: string;
    queryUrl: string;
    coverage: string;
    featureCount: number;
    gaps: string[];
    zoningJoinedCount: number;
    fluJoinedCount: number;
    municipalities: Array<{
      name: string;
      zoningUrl: string | null;
      fluUrl: string | null;
      zoningJoined: number;
      fluJoined: number;
      zoningGap: string | null;
      fluGap: string | null;
    }>;
    unincorporated: { parcels: number; zoningUrl: null; note: string };
    siblingsNotUsed: Array<{ role: string; url: string }>;
  };

  it("uses Sumner 911 ParcelsCAMA instead of Comptroller IMPACT", () => {
    expect(county.source).toBe("tn-sumner-911-parcels-cama");
    expect(county.queryUrl).toContain("/ParcelsCAMA/FeatureServer/0/query");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(15000);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/ParcelsCAMA/);
    expect(gaps).toMatch(/PARCEL_TYP=1/);
    expect(gaps).toMatch(/not used/i);
    expect(gaps).toMatch(/IMPACT/);
    expect(gaps).toMatch(/Dec-2023/);
    expect(gaps).not.toMatch(/tn-impact-47165/);
    expect(county.siblingsNotUsed.map((item) => item.role).join(" ")).toMatch(/IMPACT/);
    expect(county.siblingsNotUsed.map((item) => item.role).join(" ")).toMatch(/Dec-2023/);
    expect(gaps).toMatch(/not a designated Qualified Opportunity Zone/i);
  });

  it("documents city zoning and the honest FLU gaps", () => {
    const byName = Object.fromEntries(county.municipalities.map((city) => [city.name, city]));
    for (const name of ["Gallatin", "Hendersonville", "Portland", "White House", "Millersville", "Goodlettsville"]) {
      expect(byName[name].zoningUrl, name).toBeTruthy();
      expect(byName[name].zoningJoined, name).toBeGreaterThan(0);
    }
    expect(byName.Hendersonville.zoningUrl).toContain("HvilleTN_Zoning_UPDATED/MapServer/3");
    expect(byName.Portland.zoningUrl).toContain("Planimetric_Parcels/FeatureServer/0");
    expect(byName.Goodlettsville.zoningUrl).toContain("Zoning_District_2025");
    expect(byName["White House"].zoningUrl).toContain("WhiteHouseTN_Zoning/FeatureServer/3");
    expect(byName.Millersville.zoningUrl).toContain("Millersville_Zoning_view/FeatureServer/5");
    expect(byName.Gallatin.fluUrl).toContain("Community_Character");
    expect(byName["White House"].fluUrl).toContain("WhiteHouseTN_CompPlan/FeatureServer/2");
    expect(byName.Gallatin.fluJoined).toBeGreaterThan(0);
    expect(byName["White House"].fluJoined).toBeGreaterThan(0);
    for (const name of ["Hendersonville", "Portland", "Millersville", "Goodlettsville", "Westmoreland", "Mitchellville"]) {
      expect(byName[name].fluUrl, name).toBeNull();
      expect(byName[name].fluGap, name).toMatch(/no public future land use/i);
      expect(byName[name].fluJoined, name).toBe(0);
    }
    for (const name of ["Westmoreland", "Mitchellville"]) {
      expect(byName[name].zoningUrl, name).toBeNull();
      expect(byName[name].zoningGap, name).toMatch(/no public zoning REST/i);
      expect(byName[name].zoningJoined, name).toBe(0);
    }
    expect(county.unincorporated.zoningUrl).toBeNull();
    expect(county.unincorporated.note).toMatch(/unincorporated zoning REST/i);
    expect(county.unincorporated.parcels).toBeGreaterThan(0);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/Westmoreland/);
    expect(gaps).toMatch(/Mitchellville/);
    expect(gaps).toMatch(/MFR/);
    expect(gaps).toMatch(/RM-1/);
    expect(gaps).toMatch(/Community Character/);
    expect(gaps).toMatch(/Future_LU/);
  });

  it("keeps 5–150 acre outlines and does not treat eligibility as a designated QOZ", () => {
    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47165/tiles");
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let owners = 0;
    let mailing = 0;
    let sales = 0;
    let appraisals = 0;
    const cities = new Set<string>();
    let mfr = 0;
    let rm1 = 0;
    let gallatinFlu = 0;
    let whiteHouseFlu = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("47165");
        expect(props.state).toBe("Tennessee");
        expect(props.source).toBe("tn-sumner-911-parcels-cama");
        expect(props.marketIds).toContain("Nashville");
        expect(props.opportunityZone ?? null).toBeNull();
        expect(props.oz2Eligibility ?? null).toBeNull();
        expect(props.appraiserUrl).toBe("https://tn.sumner.geopowered.com/");
        expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
        const ring =
          feature.geometry.type === "Polygon" ? feature.geometry.coordinates[0] : feature.geometry.coordinates[0][0];
        expect(ring.length).toBeGreaterThanOrEqual(4);
        expect(ring[0][0]).toBeGreaterThan(-87.2);
        expect(ring[0][0]).toBeLessThan(-85.7);
        expect(ring[0][1]).toBeGreaterThan(35.9);
        expect(ring[0][1]).toBeLessThan(36.9);
        if (props.ownerName) owners += 1;
        if (props.mailingAddress?.line1) mailing += 1;
        if (props.lastSale?.price || props.lastSale?.date) sales += 1;
        if (props.tax.marketValue) appraisals += 1;
        const city = props.jurisdictionPrefix;
        if (city) cities.add(city);
        if (city === "Hendersonville" && props.zoningCode === "MFR") mfr += 1;
        if (city === "Portland" && props.zoningCode === "RM-1") rm1 += 1;
        if (city === "Westmoreland" || city === "Mitchellville") {
          expect(props.zoningCode ?? null).toBeNull();
          expect(props.flu?.code ?? null).toBeNull();
          expect(props.dataGaps?.join(" ") ?? "").toMatch(/no public zoning REST/i);
        }
        if (!city) {
          expect(props.zoningCode ?? null).toBeNull();
          expect(props.flu?.code ?? null).toBeNull();
          expect(props.dataGaps?.join(" ") ?? "").toMatch(/unincorporated zoning REST/i);
        }
        if (props.flu?.code) {
          expect(city === "Gallatin" || city === "White House").toBe(true);
          if (city === "Gallatin") {
            gallatinFlu += 1;
            expect(props.flu.jurisdiction).toBe("Gallatin");
            expect(props.flu.source).toContain("Community_Character");
          }
          if (city === "White House") {
            whiteHouseFlu += 1;
            expect(props.flu.jurisdiction).toBe("White House");
            expect(props.flu.source).toContain("WhiteHouseTN_CompPlan");
          }
        } else if (city && city !== "Gallatin" && city !== "White House") {
          expect(props.dataGaps?.join(" ") ?? "").toMatch(/future land use/i);
        }
        seen += 1;
      }
    }
    expect(seen).toBe(county.featureCount);
    expect(owners).toBeGreaterThan(10000);
    expect(mailing).toBeGreaterThan(10000);
    expect(sales).toBeGreaterThan(1000);
    expect(appraisals).toBeGreaterThan(1000);
    expect(mfr).toBeGreaterThan(0);
    expect(rm1).toBeGreaterThan(0);
    expect(gallatinFlu).toBeGreaterThan(0);
    expect(whiteHouseFlu).toBeGreaterThan(0);
    for (const name of ["Gallatin", "Hendersonville", "Portland", "White House", "Millersville", "Goodlettsville"]) {
      expect(cities.has(name), name).toBe(true);
    }
    const sample = JSON.parse(readFileSync(path.join(tileDir, files[0]), "utf8")) as ParcelCollection;
    const rich = sample.features.find((feature: ParcelFeature) => feature.properties.ownerName && feature.properties.mailingAddress.line1);
    expect(rich?.properties.tax.marketValue == null || typeof rich.properties.tax.marketValue === "number").toBe(true);
  });
});
