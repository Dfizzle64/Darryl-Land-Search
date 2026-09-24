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
import { signedArea } from "../lib/parcelGeometry";
import { parcelAppraiserUrl } from "../lib/format";
import type { OrlandoParcelsMeta, ParcelCollection, ParcelFeature } from "../lib/types";

const FULL_MINIMUMS: Record<string, number> = {
  Lake: 15000,
  Orange: 9000,
  Osceola: 5500,
  Polk: 18000,
  Seminole: 4000,
  Sumter: 5000,
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
    expect(isFull5AcCounty("Sumter")).toBe(true);
    expect(isFull5AcCounty("Brevard")).toBe(false);
    expect([...ORLANDO_FULL_5AC_COUNTIES]).toEqual(["Lake", "Orange", "Osceola", "Polk", "Seminole", "Sumter"]);
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

  it("ships complete 5–150 acre fixtures for the complete counties and samples for the rest", () => {
    const meta = JSON.parse(readFileSync("data/fixtures/orlando-parcels/meta.json", "utf8")) as OrlandoParcelsMeta;
    expect(meta.market).toBe("Orlando");
    expect(meta.counties).toHaveLength(9);
    expect(meta.coreMinAcres).toBe(5);
    expect(meta.coreMaxAcres).toBe(150);
    expect(meta.tile).toEqual(ORLANDO_PARCEL_TILE);
    expect(meta.parcelCount).toBe(meta.counties.reduce((sum, county) => sum + county.featureCount, 0));
    let clockwiseOuters = 0;
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
        for (const feature of features) {
          const geometry = feature.geometry;
          const outers =
            geometry.type === "Polygon"
              ? [geometry.coordinates[0]]
              : geometry.type === "MultiPolygon"
                ? geometry.coordinates.map((poly) => poly[0])
                : [];
          for (const ring of outers) {
            if (signedArea(ring) < 0) clockwiseOuters += 1;
          }
        }
      } else {
        expect(county.coverage).toBe("sample");
        expect(county.partition).toBe("file");
        expect(features.length).toBeGreaterThan(50);
        expect(features.length).toBeLessThan(500);
      }
    }
    expect(clockwiseOuters).toBe(0);
    const osceola = meta.counties.find((county) => county.name === "Osceola");
    const lake = meta.counties.find((county) => county.name === "Lake");
    expect(osceola?.source).toBe("osceola-parcels");
    expect(lake?.source).toBe("lakecounty-tax-parcels");
    expect(osceola?.zoningJoinedCount ?? 0).toBeGreaterThan(1000);
    expect(osceola?.fluJoinedCount ?? 0).toBeGreaterThan(1000);
    expect(lake?.zoningJoinedCount ?? 0).toBeGreaterThan(1000);
    expect(lake?.fluJoinedCount ?? 0).toBeGreaterThan(1000);
    const osceolaFeatures = featuresForCounty(osceola!);
    const lakeFeatures = featuresForCounty(lake!);
    expect(osceolaFeatures.filter((feature) => feature.properties.ownerName).length).toBeGreaterThan(osceolaFeatures.length * 0.9);
    expect(lakeFeatures.filter((feature) => feature.properties.ownerName).length).toBeGreaterThan(lakeFeatures.length * 0.9);
    expect(osceolaFeatures.filter((feature) => feature.properties.tax.marketValue != null).length).toBeGreaterThan(
      osceolaFeatures.length * 0.9,
    );
    expect(lakeFeatures.filter((feature) => feature.properties.tax.marketValue != null).length).toBeGreaterThan(
      lakeFeatures.length * 0.9,
    );
    expect(osceolaFeatures.filter((feature) => feature.properties.zoningCode).length).toBeGreaterThan(1000);
    expect(lakeFeatures.filter((feature) => feature.properties.zoningCode).length).toBeGreaterThan(1000);
    expect(osceolaFeatures.filter((feature) => feature.properties.flu?.code).length).toBeGreaterThan(1000);
    expect(lakeFeatures.filter((feature) => feature.properties.flu?.code).length).toBeGreaterThan(1000);
    expect(osceolaFeatures.some((feature) => feature.properties.appraiserUrl?.includes("Pin="))).toBe(true);
    expect(lakeFeatures.some((feature) => feature.properties.appraiserUrl?.includes("AltKey="))).toBe(true);
    expect(osceolaFeatures.every((feature) => feature.properties.source === "osceola-parcels-12097")).toBe(true);
    expect(lakeFeatures.every((feature) => feature.properties.source === "lakecounty-tax-parcels-12069")).toBe(true);
    expect(
      osceolaFeatures.some(
        (feature) => feature.properties.zoningDistrict === "St. Cloud" || feature.properties.flu?.source === "st-cloud-flu-98",
      ),
    ).toBe(true);
    const seminole = meta.counties.find((county) => county.name === "Seminole");
    const sumter = meta.counties.find((county) => county.name === "Sumter");
    expect(seminole?.source).toBe("doh-ehwaters+seminole-land-use");
    expect(sumter?.source).toBe("swfwmd-sumter-parcels");
    expect(seminole?.zoningJoinedCount ?? 0).toBeGreaterThan(1000);
    expect(seminole?.fluJoinedCount ?? 0).toBeGreaterThan(1000);
    expect(sumter?.zoningJoinedCount ?? 0).toBeGreaterThan(1000);
    expect(sumter?.fluJoinedCount ?? 0).toBeGreaterThan(1000);
    const seminoleFeatures = featuresForCounty(seminole!);
    const sumterFeatures = featuresForCounty(sumter!);
    expect(seminoleFeatures.every((feature) => feature.properties.source?.includes("seminole-land-use"))).toBe(true);
    expect(sumterFeatures.every((feature) => feature.properties.source === "swfwmd-sumter-parcels-12119")).toBe(true);
    expect(sumterFeatures.filter((feature) => feature.properties.ownerName).length).toBeGreaterThan(sumterFeatures.length * 0.9);
    expect(sumterFeatures.filter((feature) => feature.properties.tax.marketValue != null).length).toBeGreaterThan(
      sumterFeatures.length * 0.9,
    );
    expect(sumterFeatures.some((feature) => feature.properties.appraiserUrl?.includes("sumterpa.com"))).toBe(true);
    expect(seminoleFeatures.some((feature) => feature.properties.flu?.jurisdiction === "Oviedo")).toBe(true);
    expect(seminoleFeatures.some((feature) => feature.properties.flu?.jurisdiction === "Altamonte Springs")).toBe(true);
    for (const feature of [...seminoleFeatures, ...sumterFeatures]) {
      const [lon, lat] = feature.properties.centroid ?? [];
      expect(lon).toBeGreaterThan(-88);
      expect(lon).toBeLessThan(-79);
      expect(lat).toBeGreaterThan(24);
      expect(lat).toBeLessThan(31.5);
    }
    expect(
      parcelAppraiserUrl({
        parcelId: "A02-002",
        countyFips: "12119",
        appraiserUrl: "https://app.sumterpa.com/gis/D_ShowDetail.html?KEY=A02-002&PIN=A02-002",
      }).href,
    ).toBe("https://app.sumterpa.com/gis/D_ShowDetail.html?KEY=A02-002&PIN=A02-002");
    expect(
      parcelAppraiserUrl({ parcelId: "012527000000140000", countyFips: "12097" }).href,
    ).toBe("https://maps.property-appraiser.org/?Pin=012527000000140000");
    expect(
      parcelAppraiserUrl({
        parcelId: "331828000300004500",
        countyFips: "12069",
        appraiserUrl: "http://www.lakecopropappr.com/property-details.aspx?AltKey=2668024",
      }).href,
    ).toBe("https://www.lakecopropappr.com/property-details.aspx?AltKey=2668024");
    const orange = meta.counties.find((county) => county.name === "Orange");
    expect(orange?.zoningJoinedCount ?? 0).toBeGreaterThan(7000);
    expect(orange?.fluJoinedCount ?? 0).toBeGreaterThan(1000);
    const orangeFeatures = featuresForCounty(orange!);
    const withOwner = orangeFeatures.filter((feature) => feature.properties.ownerName).length;
    const withZoning = orangeFeatures.filter((feature) => feature.properties.zoningCode).length;
    expect(withOwner).toBe(orangeFeatures.length);
    expect(withZoning).toBeGreaterThan(7000);
    let clockwise = 0;
    let collapsed = 0;
    for (const feature of orangeFeatures) {
      const geometry = feature.geometry;
      const outers =
        geometry.type === "Polygon" ? [geometry.coordinates[0]] : geometry.type === "MultiPolygon" ? geometry.coordinates.map((poly) => poly[0]) : [];
      for (const ring of outers) {
        if (signedArea(ring) < 0) clockwise += 1;
        if (ring.length <= 4) collapsed += 1;
      }
    }
    expect(clockwise).toBe(0);
    expect(collapsed).toBeLessThan(50);
    const dean = orangeFeatures.find((feature) => feature.properties.parcelId === "302230851500010");
    expect(dean?.properties.ownerName).toContain("DEAN DAIRY");
    expect(dean?.properties.zoningCode).toBe("ORL-PD/AN");
    expect(dean?.properties.situsAddress).toBe("315 N BUMBY AVE");
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
