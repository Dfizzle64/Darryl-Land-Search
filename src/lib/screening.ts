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

export type UtilityKind = "water" | "sewer" | "power";

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
  /** A–F, or a published improvement rating such as Commendable. Null means unpublished here. */
  rating: string | null;
  ratingKind: "letter" | "improvement" | null;
  year: string | null;
  summary: string;
  source: string | null;
  sourceUrl: string | null;
  reportCardUrl: string | null;
  distanceMiles: number | null;
  lon: number;
  lat: number;
};

export type ScreeningPoint = {
  flood: FloodAtPoint;
  wetland: WetlandAtPoint;
  utilities: UtilityAtPoint[];
  schools: SchoolRating[];
  schoolsNote: string;
};

export const FEMA_NFHL_SERVICE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer";
export const FEMA_FLOOD_LAYER = "28";
export const FEMA_SOURCE = "FEMA National Flood Hazard Layer (effective flood zones)";
export const FEMA_SOURCE_URL = "https://www.fema.gov/flood-maps/national-flood-hazard-layer";

export const NWI_SERVICE =
  "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer";
export const NWI_SOURCE = "U.S. Fish & Wildlife Service National Wetlands Inventory";
export const NWI_SOURCE_URL = "https://www.fws.gov/program/national-wetlands-inventory";

export const ORANGE_WATER_SERVICE =
  "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/60";
export const ORANGE_SEWER_SERVICE =
  "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/61";
export const ORANGE_UTILITY_SOURCE = "Orange County open data — water and wastewater service providers";
export const ORANGE_UTILITY_SOURCE_URL = "https://www.orangecountyfl.net/PlanningDevelopment/InteractiveMapping.aspx";

/** Orange County service-area polygons. Outside this box the app has no water/sewer layer. */
export const ORANGE_UTILITY_BBOX = [-81.66, 28.34, -80.99, 28.79] as const;

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

export function describeFloodZone(input: {
  zone?: string | null;
  subtype?: string | null;
  sfhaFlag?: string | null;
  featuresFound: boolean;
  failed?: boolean;
}): FloodAtPoint {
  if (input.failed) {
    return {
      status: "unavailable",
      zone: null,
      subtype: null,
      sfha: null,
      floodway: false,
      summary: "FEMA’s flood service did not respond. Flood zone is unknown — that is not a finding of no hazard.",
      source: FEMA_SOURCE,
      sourceUrl: FEMA_SOURCE_URL,
    };
  }
  if (!input.featuresFound || !input.zone) {
    return {
      status: "unknown",
      zone: null,
      subtype: null,
      sfha: null,
      floodway: false,
      summary:
        "No NFHL flood-hazard polygon at this centroid. That can mean the digital map has no zone here. It is unknown, not Zone X.",
      source: FEMA_SOURCE,
      sourceUrl: FEMA_SOURCE_URL,
    };
  }
  const zone = input.zone.trim().toUpperCase();
  const subtype = input.subtype?.trim() || null;
  const floodway = Boolean(subtype && /floodway/i.test(subtype));
  const sfha = input.sfhaFlag?.toUpperCase() === "T" || SFHA_ZONES.has(zone);
  const sfhaLine = sfha ? "Special Flood Hazard Area (1% annual chance)." : "Not flagged as SFHA on this polygon.";
  const subtypeLine = subtype ? ` ${subtype}.` : "";
  return {
    status: "ok",
    zone,
    subtype,
    sfha,
    floodway,
    summary: `FEMA zone ${zone} at the parcel centroid.${subtypeLine} ${sfhaLine} This is not a survey or an insurance determination.`,
    source: FEMA_SOURCE,
    sourceUrl: FEMA_SOURCE_URL,
  };
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
        "No NWI wetland polygon at this centroid. Nearby wetlands can still exist — use the overlay. This is not a jurisdictional determination.",
      source: NWI_SOURCE,
      sourceUrl: NWI_SOURCE_URL,
    };
  }
  return {
    status: "ok",
    code,
    wetlandType,
    summary: `NWI ${[code, wetlandType].filter(Boolean).join(" · ")} at the centroid. National inventory, including Florida. Not a permit determination.`,
    source: NWI_SOURCE,
    sourceUrl: NWI_SOURCE_URL,
  };
}

export function describeUtility(input: {
  kind: UtilityKind;
  providers: string[];
  covered: boolean;
  failed?: boolean;
  extra?: string | null;
}): UtilityAtPoint {
  const source =
    input.kind === "power"
      ? { name: HIFLD_POWER_SOURCE, url: HIFLD_POWER_SOURCE_URL }
      : { name: ORANGE_UTILITY_SOURCE, url: ORANGE_UTILITY_SOURCE_URL };
  const label = input.kind === "power" ? "Electric retail territory" : input.kind === "water" ? "Water service area" : "Sewer service area";
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
          ? "No HIFLD electric retail territory contains this point. That is not a finding that power cannot be extended."
          : `This point is outside the published Orange County ${input.kind} service-area polygons. It is not a will-serve letter.`,
      source: source.name,
      sourceUrl: source.url,
    };
  }
  const caveat =
    input.kind === "power"
      ? "Retail territory only — not a connection, capacity check, or will-serve."
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
  ratingKind: "letter" | "improvement" | null;
  year: string | null;
  source: string | null;
  sourceUrl: string | null;
  reportCardUrl: string | null;
  lon: number;
  lat: number;
}): SchoolRating {
  return {
    ...input,
    distanceMiles: null,
    summary: describeSchoolRating(input),
  };
}

export function describeSchoolRating(input: {
  state: string | null;
  rating: string | null;
  ratingKind: "letter" | "improvement" | null;
  year: string | null;
  source: string | null;
}): string {
  if (input.rating && input.ratingKind === "letter") {
    return `Public rating ${input.rating}${input.year ? ` (${input.year})` : ""}. ${input.source ?? ""}`.trim();
  }
  if (input.rating && input.ratingKind === "improvement") {
    return `Improvement rating ${input.rating}${input.year ? ` (${input.year})` : ""}, not an A–F grade. ${input.source ?? ""}`.trim();
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
    "Water overlay is Orange County’s public service-area layer only. Every other county is unknown — the map does not invent a provider.",
  sewer:
    "Sewer overlay is Orange County’s public wastewater service-area layer only. Every other county is unknown.",
  power:
    "Electric overlay is the national HIFLD retail-territory layer. A territory is not a connection or a will-serve letter.",
  flood: "FEMA NFHL effective flood zones. The drawer reports the zone at the centroid when the service returns one.",
  wetlands:
    "National Wetlands Inventory, which covers Florida and the other states in this app. Polygons draw at closer zoom because the service scale limit is about 1:100,000.",
  schools:
    "Florida dots use 2025-26 DOE letter grades. North Carolina dots use 2024-25 school performance grades. Other states plot NCES locations and link the state report card — no invented grade.",
} as const;
