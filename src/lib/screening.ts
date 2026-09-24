import type { MailingAddress } from "./types";

/** Screening overlays default off so existing parcel workflows stay the same. */
export type ScreeningToggles = {
  flood: boolean;
  wetlands: boolean;
  schools: boolean;
  water: boolean;
  sewer: boolean;
  power: boolean;
};

export const DEFAULT_SCREENING_TOGGLES: ScreeningToggles = {
  flood: false,
  wetlands: false,
  schools: false,
  water: false,
  sewer: false,
  power: false,
};

export type ScreeningStatus = "ok" | "none" | "unknown" | "unavailable";

export type FloodAtPoint = {
  status: ScreeningStatus;
  zone: string | null;
  subtype: string | null;
  sfha: boolean | null;
  floodway: boolean;
  /** Feet, only when NFHL publishes a static BFE. -9999 is not a number we keep. */
  staticBfe: number | null;
  depth: number | null;
  datum: string | null;
  /** NFHL political jurisdiction. Not a Community Rating System class. */
  community: string | null;
  cid: string | null;
  summary: string;
  source: string;
  sourceUrl: string;
};

export type WetlandAtPoint = {
  status: ScreeningStatus;
  code: string | null;
  wetlandType: string | null;
  summary: string;
  source: string;
  sourceUrl: string;
};

export type UtilityKind = "water" | "sewer" | "power" | "gas";

export type UtilityAtPoint = {
  kind: UtilityKind;
  status: ScreeningStatus;
  providers: string[];
  summary: string;
  source: string;
  sourceUrl: string;
};

export type SchoolRating = {
  id: string;
  name: string;
  city: string | null;
  state: string | null;
  level: string | null;
  /**
   * A–F letter, a published improvement rating such as Commendable, or a Georgia
   * CCRPI single score. Null means unpublished here. CCRPI is not a letter grade.
   */
  rating: string | null;
  ratingKind: "letter" | "improvement" | "ccrpi" | null;
  year: string | null;
  summary: string;
  source: string | null;
  sourceUrl: string | null;
  reportCardUrl: string | null;
  distanceMiles: number | null;
  lon: number;
  lat: number;
  /** Attendance zone (OCPS or CMS), not merely the nearest campus. */
  zoned?: boolean;
};

export type TractAtPoint = {
  geoid: string | null;
  name: string | null;
  summary: string;
  source: string;
  sourceUrl: string;
};

export type ScreeningPoint = {
  flood: FloodAtPoint;
  wetland: WetlandAtPoint;
  utilities: UtilityAtPoint[];
  schools: SchoolRating[];
  schoolsNote: string;
  /** Mecklenburg County 2020 tract (geoid20). Null outside that county layer. */
  tract: TractAtPoint | null;
};

export const FEMA_NFHL_SERVICE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer";
export const FEMA_FLOOD_LAYER = "28";
/** Political areas. CID is the community identifier. This layer has no CRS class. */
export const FEMA_POLITICAL_LAYER = "22";
export const FEMA_SOURCE = "FEMA National Flood Hazard Layer (effective flood zones)";
export const FEMA_SOURCE_URL = "https://www.fema.gov/flood-maps/national-flood-hazard-layer";

export const NWI_SERVICE =
  "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer";
export const NWI_SOURCE = "U.S. Fish & Wildlife Service National Wetlands Inventory";
export const NWI_SOURCE_URL = "https://www.fws.gov/program/national-wetlands-inventory";

export const ORANGE_OPEN_DATA = "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer";
export const ORANGE_WATER_SERVICE = `${ORANGE_OPEN_DATA}/60`;
export const ORANGE_SEWER_SERVICE = `${ORANGE_OPEN_DATA}/61`;
export const ORANGE_POWER_SERVICE = `${ORANGE_OPEN_DATA}/68`;
export const ORANGE_SCHOOL_POINTS = `${ORANGE_OPEN_DATA}/76`;
export const ORANGE_ELEM_ZONES = `${ORANGE_OPEN_DATA}/91`;
export const ORANGE_HIGH_ZONES = `${ORANGE_OPEN_DATA}/90`;
export const ORANGE_MIDDLE_ZONES =
  "https://ocgis4.ocfl.net/arcgis/rest/services/InfoMap_Public_Layers/MapServer/66";
export const ORANGE_MIDDLE_MAP = "https://ocgis4.ocfl.net/arcgis/rest/services/InfoMap_Public_Layers/MapServer";
export const ORANGE_UTILITY_SOURCE = "Orange County open data — water, wastewater, and electric service areas";
export const ORANGE_UTILITY_SOURCE_URL = "https://www.orangecountyfl.net/PlanningDevelopment/InteractiveMapping.aspx";

/** Orange County service-area polygons. Outside this box the app has no water/sewer layer. */
export const ORANGE_UTILITY_BBOX = [-81.66, 28.34, -80.99, 28.79] as const;

export const MECK_GIS = "https://meckgis.mecklenburgcountync.gov/server/rest/services";
export const CMS_ELEM_ZONES = `${MECK_GIS}/CMSElementarySchoolDistricts/FeatureServer/0`;
export const CMS_MIDDLE_ZONES = `${MECK_GIS}/CMSMiddleSchoolDistricts/FeatureServer/0`;
export const CMS_HIGH_ZONES = `${MECK_GIS}/CMSHighSchoolDistricts/FeatureServer/0`;
export const CMS_SCHOOL_POINTS = `${MECK_GIS}/CMSPublicSchool/FeatureServer/0`;
export const CMS_ELEM_MAP = `${MECK_GIS}/CMSElementarySchoolDistricts/MapServer`;
export const CMS_MIDDLE_MAP = `${MECK_GIS}/CMSMiddleSchoolDistricts/MapServer`;
export const CMS_HIGH_MAP = `${MECK_GIS}/CMSHighSchoolDistricts/MapServer`;
export const MECK_TRACTS = `${MECK_GIS}/2020CensusTracts/FeatureServer/0`;
export const MECK_JURISDICTIONS = `${MECK_GIS}/Jurisdictions/FeatureServer/0`;
/** Mecklenburg County, padded. Used only to skip county queries outside this market. */
export const MECK_BBOX = [-81.08, 34.94, -80.52, 35.54] as const;
export const MECK_JURISDICTION_SOURCE =
  "Mecklenburg County jurisdictions (political limits, not a utility service area)";
export const MECK_JURISDICTION_URL = `${MECK_JURISDICTIONS}`;
export const MECK_TRACT_SOURCE = "Mecklenburg County 2020 census tracts (geoid20)";
export const MECK_TRACT_URL = MECK_TRACTS;
export const CMS_ZONES_SOURCE = "Charlotte-Mecklenburg Schools attendance zones (Mecklenburg County GIS)";
export const CMS_ZONES_URL = CMS_SCHOOL_POINTS;
export const CMS_GRADES_SOURCE =
  "North Carolina DPI School Performance Grades, 2025-26, Charlotte-Mecklenburg Schools (LEA 600), subgroup ALL";
export const CMS_GRADES_URL = "https://accrpt.tops.ncsu.edu/docs/spgdisag_datasets/SPG_Disag_2025-26.zip";

/** Cobb County School District attendance zones. Marietta City has no public zone tile. */
export const CCSD_ZONE_MAP =
  "https://gis.cobbcounty.gov/gisserver/rest/services/cobbpublic/ccsdschoolzonemapwm/MapServer";
export const GOSA_CCRPI_SOURCE =
  "GOSA Georgia School Grades 2025 (CCRPI single score). Georgia does not publish A–F letter grades.";
export const GOSA_CCRPI_URL = "https://download.gosa.ga.gov/SchoolGrades/2025SchoolGrades_data.zip";
export const COBB_UTILITY_SOURCE =
  "Cobb County water service boundaries, septic areas, and sewer-not-anticipated polygons";
export const COBB_UTILITY_URL =
  "https://gis.cobbcounty.gov/gisserver/rest/services/water/waterlivemap_refdatawm/MapServer";
export const COBB_GAS_SOURCE = "Cobb County open GIS — no gas service-area layer";
export const COBB_GAS_URL = "https://gis.cobbcounty.gov/";
export const COBB_SCHOOLS_NOTE =
  "Zoned elementary, middle, and high schools are Cobb County School District attendance zones or Marietta City Schools assignment, not the nearest campus. Scores are GOSA 2025 CCRPI single scores. Georgia does not publish A–F letter grades, and none are invented here.";

export const HIFLD_POWER_SERVICE =
  "https://services3.arcgis.com/OYP7N6mAJJCyH6hd/ArcGIS/rest/services/Electric_Retail_Service_Territories_HIFLD/FeatureServer/0";
export const HIFLD_POWER_SOURCE =
  "HIFLD electric retail service territories (DOE / Oak Ridge National Laboratory)";
export const HIFLD_POWER_SOURCE_URL = "https://hifld-geoplatform.hub.arcgis.com/";

export const NCES_SCHOOLS_SERVICE =
  "https://services1.arcgis.com/Ua5sjt3LWTPigjyD/arcgis/rest/services/Public_School_Locations_Current/FeatureServer/0";
export const NCES_SOURCE = "NCES public school locations (EDGE), current";
export const NCES_SOURCE_URL = "https://nces.ed.gov/programs/edge/Geographic/SchoolLocations";

export const FL_GRADES_SOURCE =
  "Florida Department of Education school grades, 2025-26, via the public Know Your Schools report card";
export const FL_GRADES_URL = "https://edudata.fldoe.org/ReportCards/Schools.html";
export const NC_GRADES_SOURCE =
  "North Carolina DPI School Performance Grades, 2024-25 (School Report Card researcher file)";
export const NC_GRADES_URL =
  "https://www.dpi.nc.gov/data-reports/school-report-cards/school-report-card-resources-researchers";

/** State report-card home pages used when this extract has no letter grade. */
export const STATE_REPORT_CARDS: Record<string, { label: string; url: string }> = {
  FL: { label: "Florida DOE Know Your Schools", url: FL_GRADES_URL },
  GA: { label: "Georgia school report card", url: "https://ccrpi.gadoe.org/" },
  NC: { label: "North Carolina school report cards", url: "https://www.dpi.nc.gov/data-reports/school-report-cards" },
  SC: { label: "South Carolina school report cards", url: "https://screportcards.com/" },
  TN: { label: "Tennessee school report cards", url: "https://tdepublicschools.ondemand.sas.com/" },
  AL: { label: "Alabama school report card", url: "https://reportcard.alsde.edu/" },
};

const SFHA_ZONES = new Set(["A", "AE", "AH", "AO", "AR", "A99", "V", "VE"]);

/** NFHL uses -9999 when a static BFE or depth was not published. That is not an elevation. */
export function publishedFloodMeasure(value: number | string | null | undefined): number | null {
  if (value == null || value === "") return null;
  const number = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(number) || number <= -999) return null;
  return number;
}

export function arcgisExportTileUrl(service: string, layers: string): string {
  const base = service.replace(/\/$/, "");
  return `${base}/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&dpi=96&format=png32&transparent=true&f=image&layers=show:${layers}`;
}

export function pointInBbox(lon: number, lat: number, bbox: readonly [number, number, number, number]): boolean {
  const [west, south, east, north] = bbox;
  return lon >= west && lon <= east && lat >= south && lat <= north;
}

export function bboxesIntersect(
  a: readonly [number, number, number, number],
  b: readonly [number, number, number, number],
): boolean {
  return a[0] <= b[2] && a[2] >= b[0] && a[1] <= b[3] && a[3] >= b[1];
}

/** Degrees on the longer side. School and utility fetches stay off when the view is a whole state. */
export function bboxSpan(bbox: readonly [number, number, number, number]): number {
  return Math.max(bbox[2] - bbox[0], bbox[3] - bbox[1]);
}

function withFloodCommunity(
  point: Omit<FloodAtPoint, "community" | "cid">,
  input: { community?: string | null; cid?: string | null },
): FloodAtPoint {
  const community = input.community?.trim() || null;
  const cid = input.cid?.trim() || null;
  if (!community && !cid) return { ...point, community: null, cid: null };
  const label = [community, cid ? `CID ${cid}` : null].filter(Boolean).join(", ");
  return {
    ...point,
    community,
    cid,
    summary: `${point.summary} NFHL community ${label}. This layer does not publish a Community Rating System class.`,
  };
}

export function describeFloodZone(input: {
  zone?: string | null;
  subtype?: string | null;
  sfhaFlag?: string | null;
  staticBfe?: number | string | null;
  depth?: number | string | null;
  datum?: string | null;
  community?: string | null;
  cid?: string | null;
  featuresFound: boolean;
  failed?: boolean;
}): FloodAtPoint {
  const staticBfe = publishedFloodMeasure(input.staticBfe);
  const depth = publishedFloodMeasure(input.depth);
  const datum = input.datum?.trim() || null;
  if (input.failed) {
    return withFloodCommunity(
      {
        status: "unavailable",
        zone: null,
        subtype: null,
        sfha: null,
        floodway: false,
        staticBfe: null,
        depth: null,
        datum: null,
        summary: "FEMA’s flood service did not respond. Flood zone is unknown — that is not a finding of no hazard.",
        source: FEMA_SOURCE,
        sourceUrl: FEMA_SOURCE_URL,
      },
      input,
    );
  }
  if (!input.featuresFound || !input.zone) {
    return withFloodCommunity(
      {
        status: "unknown",
        zone: null,
        subtype: null,
        sfha: null,
        floodway: false,
        staticBfe: null,
        depth: null,
        datum: null,
        summary:
          "No NFHL flood-hazard polygon at this centroid. That can mean the digital map has no zone here. It is unknown, not Zone X.",
        source: FEMA_SOURCE,
        sourceUrl: FEMA_SOURCE_URL,
      },
      input,
    );
  }
  const zone = input.zone.trim().toUpperCase();
  const subtype = input.subtype?.trim() || null;
  const floodway = Boolean(subtype && /floodway/i.test(subtype));
  const sfha = input.sfhaFlag?.toUpperCase() === "T" || SFHA_ZONES.has(zone);
  const sfhaLine = sfha ? "Special Flood Hazard Area (1% annual chance)." : "Not flagged as SFHA on this polygon.";
  const subtypeLine = subtype ? ` ${subtype}.` : "";
  const bfeLine = staticBfe != null
    ? ` Static BFE ${staticBfe} ft${datum ? ` ${datum}` : ""}.`
    : " No published static base flood elevation on this polygon.";
  const depthLine = depth != null ? ` Depth ${depth} ft.` : "";
  return withFloodCommunity(
    {
      status: "ok",
      zone,
      subtype,
      sfha,
      floodway,
      staticBfe,
      depth,
      datum: staticBfe != null ? datum : null,
      summary: `FEMA zone ${zone} at the parcel centroid.${subtypeLine} ${sfhaLine}${bfeLine}${depthLine} This is not a survey or an insurance determination.`,
      source: FEMA_SOURCE,
      sourceUrl: FEMA_SOURCE_URL,
    },
    input,
  );
}

export function describeWetland(input: {
  code?: string | null;
  wetlandType?: string | null;
  failed?: boolean;
}): WetlandAtPoint {
  if (input.failed) {
    return {
      status: "unavailable",
      code: null,
      wetlandType: null,
      summary: "The National Wetlands Inventory did not respond. Wetlands at this point are unknown, not absent.",
      source: NWI_SOURCE,
      sourceUrl: NWI_SOURCE_URL,
    };
  }
  const code = input.code?.trim() || null;
  const wetlandType = input.wetlandType?.trim() || null;
  if (!code && !wetlandType) {
    return {
      status: "none",
      code: null,
      wetlandType: null,
      summary:
        "No NWI wetland polygon within about 70 feet of this point. Nearby wetlands can still exist — use the overlay. This is not a jurisdictional determination.",
      source: NWI_SOURCE,
      sourceUrl: NWI_SOURCE_URL,
    };
  }
  return {
    status: "ok",
    code,
    wetlandType,
    summary: `NWI ${[code, wetlandType].filter(Boolean).join(" · ")} within about 70 feet of this point. National inventory, including Florida. Not a permit determination.`,
    source: NWI_SOURCE,
    sourceUrl: NWI_SOURCE_URL,
  };
}

/** City of Charlotte, the county name used for unincorporated area, or another municipality. */
export function meckJurisdictionKind(name: string | null | undefined): "charlotte" | "unincorporated" | "other" | null {
  if (!name?.trim()) return null;
  const key = name.trim().toLowerCase();
  if (key === "charlotte") return "charlotte";
  if (key === "mecklenburg") return "unincorporated";
  return "other";
}

/**
 * CMS GIS school numbers are a level prefix plus the 3-digit DPI school code.
 * 4322 (Beverly Woods Elementary) is LEA 600 school 322.
 */
export function cmsAgencyCode(schoolNum: number): string | null {
  if (!Number.isFinite(schoolNum)) return null;
  const number = Math.round(schoolNum);
  if (number < 1000 || number > 9999) return null;
  return `600${String(number % 1000).padStart(3, "0")}`;
}

export function describeMeckTract(input: { geoid?: string | null; name?: string | null; failed?: boolean }): TractAtPoint {
  if (input.failed) {
    return {
      geoid: null,
      name: null,
      summary: "Mecklenburg County’s census-tract service did not respond. The tract id is unknown.",
      source: MECK_TRACT_SOURCE,
      sourceUrl: MECK_TRACT_URL,
    };
  }
  const geoid = input.geoid?.trim() || null;
  const name = input.name?.trim() || null;
  if (!geoid) {
    return {
      geoid: null,
      name: null,
      summary: "No Mecklenburg 2020 census tract contains this point.",
      source: MECK_TRACT_SOURCE,
      sourceUrl: MECK_TRACT_URL,
    };
  }
  const label = name ? `tract ${name}` : "this tract";
  return {
    geoid,
    name,
    summary: `2020 census ${label}, GEOID ${geoid}, from Mecklenburg County GIS (geoid20). This does not change Opportunity Zone designation.`,
    source: MECK_TRACT_SOURCE,
    sourceUrl: MECK_TRACT_URL,
  };
}

export function describeUtility(input: {
  kind: UtilityKind;
  providers: string[];
  covered: boolean;
  failed?: boolean;
  extra?: string | null;
  /** Orange County layer 68, or the national HIFLD retail layer outside that county. */
  powerLayer?: "ocfl" | "hifld";
  /** Political jurisdiction name from Mecklenburg GIS, when the point hits that layer. */
  jurisdictionName?: string | null;
}): UtilityAtPoint {
  const jurisdiction = meckJurisdictionKind(input.jurisdictionName);
  if (input.kind === "gas") {
    if (jurisdiction) {
      return {
        kind: "gas",
        status: "unknown",
        providers: [],
        summary:
          "No public gas service-area polygon is published for Mecklenburg County. Gas availability is unknown — not a finding that gas is unavailable.",
        source: "Mecklenburg County open GIS — no gas service-area layer",
        sourceUrl: MECK_GIS,
      };
    }
    return {
      kind: "gas",
      status: "unknown",
      providers: [],
      summary:
        "No public gas service-area layer is wired. Gas availability is unknown — not a finding that gas is unavailable.",
      source: ORANGE_UTILITY_SOURCE,
      sourceUrl: ORANGE_UTILITY_SOURCE_URL,
    };
  }
  if (jurisdiction && (input.kind === "water" || input.kind === "sewer")) {
    const service = input.kind === "water" ? "Water" : "Sewer";
    const place = input.jurisdictionName?.trim() || "this jurisdiction";
    const summary =
      jurisdiction === "charlotte"
        ? `${service}: no public Charlotte Water service-area polygon. This point is inside the City of Charlotte, so the municipal boundary is only a jurisdiction proxy — not a connection, a capacity check, or a will-serve. Unincorporated Mecklenburg stays unverified.`
        : jurisdiction === "unincorporated"
          ? `${service}: this point is in unincorporated Mecklenburg County. Charlotte Water publishes no service-area polygon, so service here stays unverified.`
          : `${service}: this point is in ${place}. Charlotte Water publishes no service-area polygon, and ${place} service is not verified by a public layer.`;
    return {
      kind: input.kind,
      status: "unknown",
      providers: [],
      summary,
      source: MECK_JURISDICTION_SOURCE,
      sourceUrl: MECK_JURISDICTION_URL,
    };
  }
  const ocflPower = input.kind === "power" && input.powerLayer !== "hifld";
  const source =
    input.kind === "power" && !ocflPower
      ? { name: HIFLD_POWER_SOURCE, url: HIFLD_POWER_SOURCE_URL }
      : { name: ORANGE_UTILITY_SOURCE, url: ORANGE_UTILITY_SOURCE_URL };
  const label = input.kind === "power"
    ? ocflPower
      ? "Electric service area"
      : "Electric retail territory"
    : input.kind === "water"
      ? "Water service area"
      : "Sewer service area";
  if (!input.covered && input.kind !== "power") {
    return {
      kind: input.kind,
      status: "unknown",
      providers: [],
      summary: `No public ${input.kind} service-area layer is wired for this county. Unknown — not a finding that service is unavailable.`,
      source: source.name,
      sourceUrl: source.url,
    };
  }
  if (input.failed) {
    return {
      kind: input.kind,
      status: "unavailable",
      providers: [],
      summary: `${label} lookup failed. Availability is unknown.`,
      source: source.name,
      sourceUrl: source.url,
    };
  }
  if (input.providers.length === 0) {
    return {
      kind: input.kind,
      status: "none",
      providers: [],
      summary:
        input.kind === "power"
          ? ocflPower
            ? "This point is outside the published Orange County electric service-area polygons. It is not a will-serve letter."
            : "No HIFLD electric retail territory contains this point. That is not a finding that power cannot be extended."
          : `This point is outside the published Orange County ${input.kind} service-area polygons. It is not a will-serve letter.`,
      source: source.name,
      sourceUrl: source.url,
    };
  }
  const caveat =
    input.kind === "power"
      ? ocflPower
        ? "Orange County electric service area — not a connection, capacity check, or will-serve."
        : "Retail territory only — not a connection, capacity check, or will-serve."
      : "Service-area provider from county open data — not a connection or will-serve letter.";
  const extra = input.extra ? ` ${input.extra}` : "";
  return {
    kind: input.kind,
    status: "ok",
    providers: input.providers,
    summary: `${label}: ${input.providers.join("; ")}. ${caveat}${extra}`,
    source: source.name,
    sourceUrl: source.url,
  };
}

const LETTERS = new Set(["A", "B", "C", "D", "F"]);

export function schoolSwatch(rating: string | null | undefined): string {
  const letter = rating?.trim().toUpperCase();
  if (letter === "A") return "#1f7a4d";
  if (letter === "B") return "#3f9d74";
  if (letter === "C") return "#e0b15a";
  if (letter === "D") return "#d4783a";
  if (letter === "F") return "#c4473a";
  if (rating && /commend/i.test(rating)) return "#1f7a4d";
  if (rating && /maintain/i.test(rating)) return "#e0b15a";
  if (rating && /unsatisf/i.test(rating)) return "#c4473a";
  return "#8b97a3";
}

export function toSchoolRating(input: {
  id: string;
  name: string;
  city: string | null;
  state: string | null;
  level: string | null;
  rating: string | null;
  ratingKind: "letter" | "improvement" | "ccrpi" | null;
  year: string | null;
  source: string | null;
  sourceUrl: string | null;
  reportCardUrl: string | null;
  lon: number;
  lat: number;
  zoned?: boolean;
}): SchoolRating {
  return {
    ...input,
    distanceMiles: null,
    zoned: input.zoned ?? false,
    summary: describeSchoolRating(input),
  };
}

export function describeSchoolRating(input: {
  state: string | null;
  rating: string | null;
  ratingKind: "letter" | "improvement" | "ccrpi" | null;
  year: string | null;
  source: string | null;
}): string {
  const floridaConfidence =
    input.state === "FL"
      ? " Confidence is medium until the FL DOE School Grades Excel can be ingested."
      : "";
  if (input.rating && input.ratingKind === "ccrpi") {
    return `GOSA CCRPI single score ${input.rating}${input.year ? ` (${input.year})` : ""}. Georgia does not publish A–F letter grades. ${input.source ?? ""}`.trim();
  }
  if (input.rating && input.ratingKind === "letter") {
    return `Public rating ${input.rating}${input.year ? ` (${input.year})` : ""}. ${input.source ?? ""}${floridaConfidence}`.trim();
  }
  if (input.rating && input.ratingKind === "improvement") {
    return `Improvement rating ${input.rating}${input.year ? ` (${input.year})` : ""}, not an A–F grade. ${input.source ?? ""}${floridaConfidence}`.trim();
  }
  const portal = input.state ? STATE_REPORT_CARDS[input.state] : null;
  if (portal) {
    return `No letter grade in this public extract. Open ${portal.label} for the official rating.`;
  }
  return "No letter grade in this public extract.";
}

export function haversineMiles(aLon: number, aLat: number, bLon: number, bLat: number): number {
  const toRad = (value: number) => (value * Math.PI) / 180;
  const dLat = toRad(bLat - aLat);
  const dLon = toRad(bLon - aLon);
  const lat1 = toRad(aLat);
  const lat2 = toRad(bLat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 3958.7613 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

export function nearestSchools(schools: SchoolRating[], lon: number, lat: number, limit = 5, maxMiles = 3): SchoolRating[] {
  return schools
    .map((school) => ({ ...school, distanceMiles: haversineMiles(lon, lat, school.lon, school.lat) }))
    .filter((school) => school.distanceMiles != null && school.distanceMiles <= maxMiles)
    .sort((a, b) => (a.distanceMiles ?? 99) - (b.distanceMiles ?? 99) || a.name.localeCompare(b.name))
    .slice(0, limit);
}

export function normalizeStateCode(state: string | null | undefined): string | null {
  if (!state) return null;
  const key = state.trim().toLowerCase();
  const aliases: Record<string, string> = {
    fl: "FL",
    florida: "FL",
    ga: "GA",
    georgia: "GA",
    nc: "NC",
    "north carolina": "NC",
    sc: "SC",
    "south carolina": "SC",
    tn: "TN",
    tennessee: "TN",
    al: "AL",
    alabama: "AL",
  };
  return aliases[key] ?? null;
}

export function isLetterGrade(rating: string | null | undefined): boolean {
  return Boolean(rating && LETTERS.has(rating.trim().toUpperCase()));
}

export function mailingGap(address: MailingAddress | null | undefined): string | null {
  if (!address) return "Owner mailing address is not in this public parcel extract.";
  const parts = [address.line1, address.line2, address.city, address.state, address.zip].filter((part) => part?.trim());
  return parts.length ? null : "Owner mailing address is not in this public parcel extract.";
}

export const UTILITY_LAYER_NOTE = {
  water:
    "Water polygons are Orange County’s public service-area layer only. Charlotte Water publishes no service-area polygon. Inside the City of Charlotte the drawer uses the municipal boundary as a jurisdiction proxy, and unincorporated Mecklenburg stays unverified. Cobb batch-40 parcels name CCWS or a city service boundary in the drawer; that join is not a county-wide polygon. Every other county is unknown.",
  sewer:
    "Sewer polygons are Orange County’s public wastewater service-area layer only. Charlotte has no public sewer polygon either — same jurisdiction proxy as water, with unincorporated Mecklenburg unverified. Five Cobb batch parcels marked Sewer Not Anticipated stay gaps.",
  power:
    "In Orange County this is open-data electric service areas (layer 68). Outside that county it is the HIFLD retail-territory layer, which in Mecklenburg includes Duke Energy Carolinas and EnergyUnited EMC and can overlap a municipal retailer. Cobb batch-40 parcels join one HIFLD name when territories overlap. Neither layer is a connection or a will-serve. Gas has no public polygon.",
  flood:
    "FEMA NFHL effective flood zones. The drawer reports the zone at the centroid. A static BFE is shown only when NFHL publishes one. The -9999 sentinel is not an elevation. The community id comes from the NFHL political layer. That layer does not include a Community Rating System class.",
  wetlands:
    "National Wetlands Inventory, which covers Florida and the other states in this app. Polygons draw at closer zoom because the service scale limit is about 1:100,000.",
  schools:
    "Orange County draws OCPS attendance zones. Mecklenburg County draws CMS elementary, middle, and high attendance zones, with 2025-26 NCDPI school performance grades for LEA 600. Cobb County draws CCSD attendance zones. Cobb batch-40 parcels show GOSA 2025 CCRPI single scores for the zoned Cobb or Marietta schools — Georgia does not publish A–F letters, and none are invented. Other North Carolina dots stay on the 2024-25 researcher file. Florida letters are the 2025-26 Know Your Schools report card — the School Grades Excel file returns 403 from many hosts, so it is not re-downloaded here. Other states plot NCES locations and link the state report card. No grade is invented.",
} as const;
