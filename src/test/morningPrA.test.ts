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

/** Southeast footprint counties whose state layer has a county field. */
const STATE_FIELD_COUNTIES = [
  "37001", "37007", "37019", "37021", "37025", "37035", "37037", "37045", "37047", "37057",
  "37059", "37061", "37063", "37067", "37069", "37071", "37077", "37081", "37085", "37089",
  "37097", "37101", "37105", "37109", "37119", "37127", "37129", "37133", "37135", "37141",
  "37145", "37151", "37157", "37159", "37163", "37167", "37169", "37171", "37179", "37181",
  "37183", "37185", "37191", "37195", "37197",
  "45001", "45007", "45013", "45015", "45017", "45019", "45023", "45027", "45029", "45035",
  "45039", "45043", "45045", "45047", "45053", "45055", "45057", "45059", "45061", "45063",
  "45071", "45073", "45075", "45077", "45079", "45081", "45083", "45085", "45091",
  "47001", "47003", "47009", "47011", "47013", "47015", "47021", "47029", "47037", "47043",
  "47047", "47057", "47063", "47065", "47081", "47089", "47093", "47097", "47103", "47105",
  "47111", "47113", "47115", "47117", "47119", "47121", "47125", "47129", "47143", "47145",
  "47147", "47149", "47153", "47155", "47157", "47159", "47165", "47167", "47169", "47173",
  "47187", "47189",
  "28009", "28029", "28033", "28039", "28049", "28089", "28093", "28121", "28127", "28137",
  "28143", "28149", "28163",
  "01001", "01003", "01007", "01009", "01021", "01043", "01051", "01053", "01063", "01065",
  "01071", "01073", "01083", "01085", "01089", "01095", "01097", "01101", "01103", "01107",
  "01115", "01117", "01121", "01125", "01127", "01129",
  "05035", "05093",
];

const FL_FOOTPRINT = [
  "12001", "12003", "12005", "12007", "12009", "12015", "12017", "12019", "12021", "12027",
  "12029", "12031", "12033", "12039", "12041", "12043", "12049", "12051", "12053", "12055",
  "12057", "12061", "12065", "12071", "12073", "12075", "12079", "12081", "12085", "12089",
  "12091", "12093", "12095", "12097", "12101", "12103", "12105", "12107", "12109", "12111",
  "12113", "12115", "12119", "12123", "12127", "12129", "12131",
];

const GA_FOOTPRINT = [
  "13011", "13013", "13015", "13021", "13029", "13031", "13035", "13045", "13047", "13051",
  "13057", "13059", "13063", "13067", "13077", "13083", "13085", "13089", "13097", "13103",
  "13113", "13117", "13121", "13129", "13135", "13139", "13143", "13149", "13151", "13157",
  "13159", "13171", "13179", "13185", "13187", "13199", "13207", "13211", "13217", "13223",
  "13227", "13231", "13247", "13251", "13255", "13295", "13297", "13313",
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

describe("footprint county traffic fixture", () => {
  it("joins a positive count for each covered county and does not label those roads FDOT", () => {
    const meta = JSON.parse(readFileSync("data/fixtures/signals-meta.json", "utf8"));
    const byCounty = meta.stateAadtByCounty as Record<string, number>;
    const flByCounty = meta.flAadtByCounty as Record<string, number>;
    const deferred = new Set(
      ((meta.aadtDeferred as { fips?: string }[] | undefined) ?? []).map((row) => row.fips),
    );
    for (const fips of PRIORITY) {
      expect(byCounty[fips], fips).toBeGreaterThan(0);
      expect(deferred.has(fips), fips).toBe(false);
    }
    for (const fips of STATE_FIELD_COUNTIES) {
      expect(byCounty[fips], fips).toBeGreaterThan(0);
    }
    for (const fips of FL_FOOTPRINT) {
      expect(flByCounty[fips], fips).toBeGreaterThan(0);
    }
    for (const fips of GA_FOOTPRINT) {
      expect(byCounty[fips], fips).toBeGreaterThan(0);
      expect(deferred.has(fips), fips).toBe(false);
    }
    const sources = meta.stateAadtSources as Record<
      string,
      {
        field: string;
        year?: number;
        layer?: string;
        vintage?: string;
        url?: string;
        keptLiveField?: string;
        keptLiveYear?: number;
        keptLiveFips?: string[];
      }
    >;
    expect(sources.NC.field).toBe("AADT_2024");
    expect(sources.NC.year).toBe(2024);
    expect(sources.NC.url).toContain("NCDOT__2024_AADT_Stations_published_September_2025");
    expect(sources.NC.keptLiveField).toBe("AADT_2022");
    expect(sources.NC.keptLiveYear).toBe(2022);
    expect(sources.NC.keptLiveFips).toEqual(["37063", "37119", "37183"]);
    expect(byCounty["37063"]).toBe(111);
    expect(byCounty["37119"]).toBe(1793);
    expect(byCounty["37183"]).toBe(217);
    expect(sources.SC.field).toBe("FactoredAA");
    expect(sources.SC.year).toBe(2025);
    expect(sources.GA.field).toBe("aadt");
    expect(sources.GA.url).toContain("GDOT_AADT/FeatureServer/1");
    expect(sources.GA.vintage).toMatch(/unknown/i);
    expect(deferred.size).toBe(0);
    expect(sources.TN.field).toBe("AADT");
    expect(sources.TN.year).toBe(2025);
    expect(sources.MS.field).toBe("ADT_21");
    expect(sources.MS.year).toBe(2021);
    expect(sources.MS.layer).toBe("RC_AADT_2019");
    expect(sources.NC.vintage).toMatch(/AADT_2024/);
    expect(sources.NC.vintage).toMatch(/HPMS 2022/);
    const notes = (meta.notes as string[]).join("\n");
    expect(notes).toMatch(/AADT_2024/);
    expect(notes).toMatch(/HPMS 2022/);
    expect(notes).toMatch(/11,570/);
    expect(notes).toMatch(/HDR AGOL/);
    expect(notes).toMatch(/AADTYEAR 2025/);
    expect(notes).toMatch(/ADT Linear/);
    expect(sources.AL.field).toBe("AADT");
    expect(sources.AL.year).toBe(2024);
    expect(sources.AR.field).toBe("MostRecentADT");
    expect(sources.AR.year).toBe(2025);
    expect(sources.AR.url).toContain("ADTLinear/FeatureServer/0");
    expect(sources.FL.field).toBe("AADT");
    expect(sources.FL.year).toBe(2025);
    expect(meta.aadtSource).toContain("gis.fdot.gov/arcgis/rest/services/RCI_Layers/FeatureServer/0");
    expect(sources.FL.url).toContain("RCI_Layers/FeatureServer/0");
    const raw = readFileSync("data/fixtures/aadt-state-dots.geojson", "utf8");
    expect(raw).not.toMatch(/FDOT/);
    expect(raw).toContain('"countyFips":"45019"');
    expect(raw).toContain('"countyFips":"28089"');
    expect(raw).toContain('"countyFips":"13067"');
    expect(raw).toContain('"countyFips":"01073"');
    expect(raw).toContain('"countyFips":"05035"');
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
