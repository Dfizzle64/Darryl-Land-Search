import { describe, expect, it } from "vitest";
import { entitySearchLink, parcelAppraiserUrl } from "../lib/format";
import fs from "node:fs";
import {
  bboxSpan,
  cmsAgencyCode,
  describeFloodZone,
  describeMeckTract,
  describeSchoolRating,
  describeUtility,
  describeWetland,
  mailingGap,
  nearestSchools,
  pointInBbox,
  publishedFloodMeasure,
  schoolSwatch,
  toSchoolRating,
  type SchoolRating,
} from "../lib/screening";

function school(partial: Partial<SchoolRating> & Pick<SchoolRating, "id" | "name" | "lon" | "lat">): SchoolRating {
  return {
    city: null,
    state: "FL",
    level: null,
    rating: null,
    ratingKind: null,
    year: null,
    summary: "",
    source: null,
    sourceUrl: null,
    reportCardUrl: null,
    distanceMiles: null,
    ...partial,
  };
}

describe("screening layers", () => {
  it("does not treat a missing FEMA polygon as Zone X", () => {
    const flood = describeFloodZone({ featuresFound: false });
    expect(flood.status).toBe("unknown");
    expect(flood.zone).toBeNull();
    expect(flood.summary).toMatch(/not Zone X/);
  });

  it("flags SFHA and floodway from the published zone", () => {
    const flood = describeFloodZone({
      featuresFound: true,
      zone: "AE",
      subtype: "FLOODWAY",
      sfhaFlag: "T",
    });
    expect(flood.status).toBe("ok");
    expect(flood.sfha).toBe(true);
    expect(flood.floodway).toBe(true);
    expect(flood.zone).toBe("AE");
  });

  it("does not treat the NFHL -9999 sentinel as a base flood elevation", () => {
    expect(publishedFloodMeasure(-9999)).toBeNull();
    expect(publishedFloodMeasure("-9999")).toBeNull();
    const missing = describeFloodZone({
      featuresFound: true,
      zone: "X",
      subtype: "AREA OF MINIMAL FLOOD HAZARD",
      sfhaFlag: "F",
      staticBfe: -9999,
      depth: -9999,
      datum: "",
    });
    expect(missing.staticBfe).toBeNull();
    expect(missing.summary).toMatch(/No published static base flood elevation/);
    expect(missing.summary).not.toMatch(/-9999/);
    const published = describeFloodZone({
      featuresFound: true,
      zone: "AE",
      sfhaFlag: "T",
      staticBfe: 89.3,
      datum: "NAVD88",
    });
    expect(published.staticBfe).toBe(89.3);
    expect(published.summary).toMatch(/89\.3 ft NAVD88/);
  });

  it("says a failed flood lookup is unavailable", () => {
    expect(describeFloodZone({ featuresFound: false, failed: true }).status).toBe("unavailable");
  });

  it("separates no wetland polygon from a mapped wetland", () => {
    expect(describeWetland({}).status).toBe("none");
    expect(describeWetland({}).summary).toMatch(/not a jurisdictional/);
    const hit = describeWetland({ code: "PEM1C", wetlandType: "Freshwater Emergent Wetland" });
    expect(hit.status).toBe("ok");
    expect(hit.summary).toMatch(/PEM1C/);
  });

  it("reports an NFHL community id without inventing a CRS class", () => {
    const flood = describeFloodZone({
      featuresFound: true,
      zone: "X",
      subtype: "AREA OF MINIMAL FLOOD HAZARD",
      sfhaFlag: "F",
      staticBfe: -9999,
      community: "CITY OF CHARLOTTE",
      cid: "370159",
    });
    expect(flood.zone).toBe("X");
    expect(flood.cid).toBe("370159");
    expect(flood.summary).toMatch(/CID 370159/);
    expect(flood.summary).toMatch(/does not publish a Community Rating System class/);
    expect(flood.summary).not.toMatch(/CRS class \d/);
  });

  it("uses the Charlotte jurisdiction as a water proxy and leaves unincorporated unverified", () => {
    const city = describeUtility({ kind: "water", providers: [], covered: false, jurisdictionName: "Charlotte" });
    expect(city.status).toBe("unknown");
    expect(city.providers).toEqual([]);
    expect(city.summary).toMatch(/no public Charlotte Water service-area polygon/);
    expect(city.summary).toMatch(/jurisdiction proxy/);
    expect(city.summary).toMatch(/Unincorporated Mecklenburg stays unverified/);
    const county = describeUtility({ kind: "sewer", providers: [], covered: false, jurisdictionName: "Mecklenburg" });
    expect(county.summary).toMatch(/unincorporated Mecklenburg/);
    expect(county.summary).toMatch(/stays unverified/);
    const town = describeUtility({ kind: "water", providers: [], covered: false, jurisdictionName: "Huntersville" });
    expect(town.summary).toMatch(/Huntersville/);
    expect(town.summary).toMatch(/not verified/);
    const gas = describeUtility({ kind: "gas", providers: [], covered: false, jurisdictionName: "Charlotte" });
    expect(gas.providers).toEqual([]);
    expect(gas.summary).toMatch(/No public gas service-area polygon/);
  });

  it("joins CMS GIS school numbers to NCDPI LEA 600 and keeps the 2025-26 letters", () => {
    expect(cmsAgencyCode(4322)).toBe("600322");
    expect(cmsAgencyCode(5333)).toBe("600333");
    expect(cmsAgencyCode(7535)).toBe("600535");
    expect(cmsAgencyCode(12)).toBeNull();
    const cms = JSON.parse(fs.readFileSync("data/fixtures/screening/cms-spg-2025-26.json", "utf8")) as {
      year: string;
      leaCode: string;
      byCode: Record<string, { grade: string; name: string }>;
    };
    expect(cms.year).toBe("2025-26");
    expect(cms.leaCode).toBe("600");
    expect(cms.byCode["600322"]).toMatchObject({ grade: "B", name: "Beverly Woods Elementary" });
    expect(cms.byCode["600333"].grade).toBe("C");
    const tract = describeMeckTract({ geoid: "37119003008", name: "30.08" });
    expect(tract.geoid).toBe("37119003008");
    expect(tract.summary).toMatch(/geoid20/);
    expect(tract.summary).toMatch(/does not change Opportunity Zone/);
    const nc = describeSchoolRating({
      state: "NC",
      rating: "B",
      ratingKind: "letter",
      year: "2025-26",
      source: "North Carolina DPI",
    });
    expect(nc).toMatch(/Public rating B \(2025-26\)/);
    expect(nc).not.toMatch(/medium until the FL DOE/);
  });

  it("keeps water unknown outside the Orange County layer", () => {
    const outside = describeUtility({ kind: "water", providers: [], covered: false });
    expect(outside.status).toBe("unknown");
    expect(outside.summary).toMatch(/not a finding that service is unavailable/);
    expect(pointInBbox(-84.3, 33.7, [-81.66, 28.34, -80.99, 28.79])).toBe(false);
    expect(pointInBbox(-81.379, 28.538, [-81.66, 28.34, -80.99, 28.79])).toBe(true);
  });

  it("leaves gas unknown and keeps Orange electric off the national territory wording", () => {
    const gas = describeUtility({ kind: "gas", providers: [], covered: false });
    expect(gas.status).toBe("unknown");
    expect(gas.summary).toMatch(/No public gas/);
    const orangePower = describeUtility({
      kind: "power",
      providers: ["Duke Energy"],
      covered: true,
      powerLayer: "ocfl",
    });
    expect(orangePower.summary).toMatch(/Orange County electric service area/);
    expect(orangePower.summary).toMatch(/not a connection/);
  });

  it("does not call an empty electric territory a connection", () => {
    const power = describeUtility({ kind: "power", providers: ["ORLANDO UTILITIES COMM"], covered: true });
    expect(power.summary).toMatch(/not a connection/);
    expect(describeUtility({ kind: "power", providers: [], covered: true }).status).toBe("none");
  });

  it("describes missing school grades without inventing one", () => {
    expect(describeSchoolRating({ state: "GA", rating: null, ratingKind: null, year: null, source: null })).toMatch(/Georgia school report card/);
    expect(schoolSwatch(null)).toBe("#8b97a3");
    expect(schoolSwatch("A")).toBe("#1f7a4d");
    const rated = toSchoolRating({
      id: "1",
      name: "Horizon High",
      city: "Winter Garden",
      state: "FL",
      level: "High",
      rating: "A",
      ratingKind: "letter",
      year: "2025-26",
      source: "Florida DOE",
      sourceUrl: "https://edudata.fldoe.org/ReportCards/Schools.html",
      reportCardUrl: "https://edudata.fldoe.org/ReportCards/Schools.html?district=48&school=1471",
      lon: -81.6,
      lat: 28.4,
    });
    expect(rated.summary).toMatch(/Public rating A \(2025-26\)/);
    expect(rated.summary).toMatch(/medium until the FL DOE School Grades Excel/);
  });

  it("keeps the five nearest schools inside 3 miles", () => {
    const origin = { lon: -81.38, lat: 28.54 };
    const nearby = nearestSchools(
      [
        school({ id: "far", name: "Far", lon: -80.5, lat: 28.54 }),
        school({ id: "near", name: "Near", lon: -81.39, lat: 28.54 }),
        school({ id: "mid", name: "Mid", lon: -81.42, lat: 28.54 }),
      ],
      origin.lon,
      origin.lat,
    );
    expect(nearby.map((item) => item.id)).toEqual(["near", "mid"]);
    expect(bboxSpan([-81.5, 28.4, -81.2, 28.6])).toBeLessThan(1.2);
  });
});

describe("public contact links", () => {
  it("does not send a known non-Orange parcel to the Orange appraiser", () => {
    const dekalb = parcelAppraiserUrl({ parcelId: "123", countyFips: "13089" });
    expect(dekalb.href).toBe("https://propertyappraisal.dekalbcountyga.gov/");
    expect(dekalb.href).not.toContain("ocpa");
    expect(dekalb.label).toContain("DeKalb");
    const barrow = parcelAppraiserUrl({ parcelId: "XX125  113", countyFips: "13013" });
    expect(barrow.href).toContain("AppID=635");
    expect(barrow.href).toContain("LayerID=11218");
    expect(barrow.label).toMatch(/Barrow/);
    const barrowParcel = parcelAppraiserUrl({
      parcelId: "XX125  113",
      countyFips: "13013",
      appraiserUrl:
        "https://qpublic.schneidercorp.com/Application.aspx?App=BarrowCountyGA&Layer=Parcels&PageType=Report&KeyValue=XX125%20%20113",
    });
    expect(barrowParcel.href).toContain("KeyValue=");
    expect(barrowParcel.href).not.toContain("ocpafl.org");
    expect(barrowParcel.label).toMatch(/Barrow County qPublic/);
    const uncataloged = parcelAppraiserUrl({ parcelId: "123", countyFips: "01001" });
    expect(uncataloged.href).toBeNull();
    expect(uncataloged.label).toMatch(/No county property-appraiser search is cataloged/);
    const orange = parcelAppraiserUrl({ parcelId: "282312000000000", countyFips: "12095" });
    expect(orange.href).toContain("ocpafl.org");
    expect(orange.href).toContain("282312000000000");
    const pilot = parcelAppraiserUrl({ parcelId: "282312000000000" });
    expect(pilot.href).toContain("ocpafl.org");
  });

  it("uses the state business search and says when the mailing address is missing", () => {
    const florida = entitySearchLink("Florida", "ACME HOLDINGS LLC", "12095");
    expect(florida?.href).toContain("sunbiz.org");
    expect(florida?.prefilled).toBe(true);
    const georgia = entitySearchLink("Georgia", "ACME HOLDINGS LLC", "13089");
    expect(georgia?.href).toContain("sos.ga.gov");
    expect(georgia?.href).not.toContain("sunbiz");
    expect(georgia?.prefilled).toBe(false);
    expect(entitySearchLink(null, "ACME LLC", "13089")).toBeNull();
    expect(entitySearchLink(null, "ACME LLC", null)?.href).toContain("sunbiz.org");
    expect(mailingGap(null)).toMatch(/not in this public parcel extract/);
    expect(mailingGap({ line1: "1 MAIN ST", line2: null, city: "ORLANDO", state: "FL", zip: "32801" })).toBeNull();
  });
});
