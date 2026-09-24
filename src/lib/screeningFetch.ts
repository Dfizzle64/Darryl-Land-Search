import fs from "node:fs";
import path from "node:path";
import {
  bboxSpan,
  bboxesIntersect,
  CMS_ELEM_ZONES,
  CMS_GRADES_SOURCE,
  CMS_GRADES_URL,
  CMS_HIGH_ZONES,
  CMS_MIDDLE_ZONES,
  DCSD_ELEM_ZONES,
  DCSD_HIGH_ZONES,
  DCSD_MIDDLE_ZONES,
  DEKALB_BBOX,
  CMS_SCHOOL_POINTS,
  CMS_ZONES_SOURCE,
  CMS_ZONES_URL,
  cmsAgencyCode,
  describeFloodZone,
  describeMeckTract,
  describeUtility,
  describeWetland,
  haversineMiles,
  FEMA_FLOOD_LAYER,
  FEMA_NFHL_SERVICE,
  FEMA_POLITICAL_LAYER,
  FL_GRADES_SOURCE,
  FL_GRADES_URL,
  HIFLD_POWER_SERVICE,
  MECK_BBOX,
  MECK_JURISDICTIONS,
  MECK_TRACTS,
  ORANGE_ELEM_ZONES,
  ORANGE_HIGH_ZONES,
  ORANGE_MIDDLE_ZONES,
  ORANGE_POWER_SERVICE,
  ORANGE_SCHOOL_POINTS,
  NCES_SCHOOLS_SERVICE,
  NCES_SOURCE,
  NCES_SOURCE_URL,
  nearestSchools,
  NWI_SERVICE,
  ORANGE_SEWER_SERVICE,
  ORANGE_UTILITY_BBOX,
  ORANGE_WATER_SERVICE,
  pointInBbox,
  STATE_REPORT_CARDS,
  toSchoolRating,
  UTILITY_LAYER_NOTE,
  type SchoolRating,
  type ScreeningPoint,
  type TractAtPoint,
  type UtilityKind,
} from "./screening";
import { cobbBatchParcel, cobbScreeningOverlay } from "./cobbBatch40";
import { dekalbBatchParcel, dekalbScreeningOverlay } from "./dekalbBatch40";

const FIXTURE_PATH = path.join(process.cwd(), "data/fixtures/screening/school-ratings.json");
const CMS_FIXTURE_PATH = path.join(process.cwd(), "data/fixtures/screening/cms-spg-2025-26.json");
const QUERY_MS = 12000;
const MAX_VECTOR_SPAN = 1.2;
const SCHOOL_CAP = 400;

type FloridaSchool = {
  id: string;
  name: string;
  grade: string | null;
  improvement: string | null;
  city: string | null;
  level: string | null;
  district?: string;
  school?: string;
  lat: number;
  lon: number;
  reportCardUrl: string | null;
};

type RatingsFixture = {
  florida: { year: string; source: string; sourceUrl: string; schools: FloridaSchool[] };
  northCarolina: { year: string; source: string; sourceUrl: string; byNces: Record<string, string> };
};

type CmsGradeFile = {
  year: string;
  source: string;
  sourceUrl: string;
  reportCardUrl: string;
  byCode: Record<string, { grade: string; name: string }>;
  byNces: Record<string, string>;
  alternativeModel: { code: string; name: string }[];
};

let ratingsCache: RatingsFixture | null = null;
let cmsGradesCache: CmsGradeFile | null | undefined;

export function loadCmsGrades(): CmsGradeFile | null {
  if (cmsGradesCache !== undefined) return cmsGradesCache;
  try {
    cmsGradesCache = JSON.parse(fs.readFileSync(CMS_FIXTURE_PATH, "utf8")) as CmsGradeFile;
  } catch {
    cmsGradesCache = null;
  }
  return cmsGradesCache;
}

export function loadSchoolRatings(): RatingsFixture | null {
  if (ratingsCache) return ratingsCache;
  try {
    ratingsCache = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8")) as RatingsFixture;
  } catch {
    ratingsCache = null;
  }
  return ratingsCache;
}

export type BBox = readonly [number, number, number, number];

export function parseBbox(value: string | null): BBox | null {
  if (!value) return null;
  const parts = value.split(",").map((part) => Number(part.trim()));
  if (parts.length !== 4 || parts.some((part) => !Number.isFinite(part))) return null;
  const [west, south, east, north] = parts;
  if (west >= east || south >= north) return null;
  if (west < -180 || east > 180 || south < -90 || north > 90) return null;
  return [west, south, east, north];
}

async function getJson(url: string): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), QUERY_MS);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload: unknown = await response.json();
    if (payload && typeof payload === "object" && (payload as { error?: unknown }).error) {
      throw new Error("ArcGIS error");
    }
    return payload;
  } finally {
    clearTimeout(timer);
  }
}

function attrsOf(feature: unknown): Record<string, unknown> {
  if (!feature || typeof feature !== "object") return {};
  const record = feature as { attributes?: Record<string, unknown>; properties?: Record<string, unknown> };
  return record.attributes ?? record.properties ?? {};
}

function featuresOf(payload: unknown): unknown[] {
  if (!payload || typeof payload !== "object") return [];
  const record = payload as { features?: unknown[]; results?: unknown[] };
  return record.features ?? record.results ?? [];
}

function textAttr(attrs: Record<string, unknown>, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = attrs[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
  }
  return null;
}

function pointQuery(service: string, lon: number, lat: number, outFields: string): string {
  const params = new URLSearchParams({
    geometry: `${lon},${lat}`,
    geometryType: "esriGeometryPoint",
    inSR: "4326",
    spatialRel: "esriSpatialRelIntersects",
    outFields,
    returnGeometry: "false",
    f: "json",
  });
  return `${service.replace(/\/$/, "")}/query?${params}`;
}

async function floodCommunity(lon: number, lat: number): Promise<{ community: string | null; cid: string | null }> {
  try {
    const payload = await getJson(
      pointQuery(`${FEMA_NFHL_SERVICE}/${FEMA_POLITICAL_LAYER}`, lon, lat, "POL_NAME1,CID"),
    );
    const attrs = attrsOf(featuresOf(payload)[0]);
    return { community: textAttr(attrs, "POL_NAME1"), cid: textAttr(attrs, "CID") };
  } catch {
    return { community: null, cid: null };
  }
}

export async function floodAtPoint(lon: number, lat: number) {
  const [zoneResult, community] = await Promise.all([
    getJson(
      pointQuery(`${FEMA_NFHL_SERVICE}/${FEMA_FLOOD_LAYER}`, lon, lat, "FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE,V_DATUM,DEPTH"),
    ).then(
      (payload) => ({ payload, failed: false as const }),
      () => ({ payload: null, failed: true as const }),
    ),
    floodCommunity(lon, lat),
  ]);
  if (zoneResult.failed || !zoneResult.payload) {
    return describeFloodZone({ featuresFound: false, failed: true, ...community });
  }
  const features = featuresOf(zoneResult.payload);
  const attrs = attrsOf(features[0]);
  return describeFloodZone({
    zone: textAttr(attrs, "FLD_ZONE"),
    subtype: textAttr(attrs, "ZONE_SUBTY"),
    sfhaFlag: textAttr(attrs, "SFHA_TF"),
    staticBfe: textAttr(attrs, "STATIC_BFE"),
    depth: textAttr(attrs, "DEPTH"),
    datum: textAttr(attrs, "V_DATUM"),
    featuresFound: features.length > 0,
    ...community,
  });
}

export async function wetlandAtPoint(lon: number, lat: number) {
  // The NWI query ignores a bare point. A ~70-foot envelope is the public lookup that still means "here."
  const pad = 0.0002;
  const params = new URLSearchParams({
    geometry: `${lon - pad},${lat - pad},${lon + pad},${lat + pad}`,
    geometryType: "esriGeometryEnvelope",
    inSR: "4326",
    spatialRel: "esriSpatialRelIntersects",
    outFields: "Wetlands.ATTRIBUTE,Wetlands.WETLAND_TYPE",
    returnGeometry: "false",
    resultRecordCount: "1",
    f: "json",
  });
  try {
    const payload = await getJson(`${NWI_SERVICE.replace(/\/$/, "")}/0/query?${params}`);
    const features = featuresOf(payload);
    const attrs = attrsOf(features[0]);
    return describeWetland({
      code: textAttr(attrs, "ATTRIBUTE", "Wetlands.ATTRIBUTE"),
      wetlandType: textAttr(attrs, "WETLAND_TYPE", "Wetlands.WETLAND_TYPE"),
    });
  } catch {
    return describeWetland({ failed: true });
  }
}

async function utilityProviders(service: string, lon: number, lat: number, field: string): Promise<string[]> {
  const payload = await getJson(pointQuery(service, lon, lat, field));
  const names = featuresOf(payload)
    .map((feature) => textAttr(attrsOf(feature), field, "NAME", "SERVEDBY", "COMPANY"))
    .filter((name): name is string => Boolean(name));
  return [...new Set(names)];
}

async function meckJurisdictionName(lon: number, lat: number): Promise<string | null> {
  if (!pointInBbox(lon, lat, MECK_BBOX)) return null;
  try {
    const payload = await getJson(pointQuery(MECK_JURISDICTIONS, lon, lat, "name"));
    return textAttr(attrsOf(featuresOf(payload)[0]), "name");
  } catch {
    return null;
  }
}

export async function utilityAtPoint(kind: UtilityKind, lon: number, lat: number) {
  if (kind === "gas") {
    const jurisdictionName = await meckJurisdictionName(lon, lat);
    return describeUtility({ kind: "gas", providers: [], covered: false, jurisdictionName });
  }
  const inOrange = pointInBbox(lon, lat, ORANGE_UTILITY_BBOX);
  if (!inOrange && kind !== "power") {
    const jurisdictionName = await meckJurisdictionName(lon, lat);
    return describeUtility({ kind, providers: [], covered: false, jurisdictionName });
  }
  const ocflPower = kind === "power" && inOrange;
  const service = kind === "water" ? ORANGE_WATER_SERVICE : kind === "sewer" ? ORANGE_SEWER_SERVICE : ocflPower ? ORANGE_POWER_SERVICE : HIFLD_POWER_SERVICE;
  const field = kind === "water" || kind === "sewer" ? "SERVEDBY" : ocflPower ? "COMPANY" : "NAME";
  try {
    const providers = await utilityProviders(service, lon, lat, field);
    return describeUtility({
      kind,
      providers,
      covered: true,
      powerLayer: kind === "power" ? (ocflPower ? "ocfl" : "hifld") : undefined,
    });
  } catch {
    return describeUtility({
      kind,
      providers: [],
      covered: true,
      failed: true,
      powerLayer: kind === "power" ? (ocflPower ? "ocfl" : "hifld") : undefined,
    });
  }
}

function floridaSchoolsInBbox(bbox: BBox): SchoolRating[] {
  const fixture = loadSchoolRatings();
  if (!fixture) return [];
  return fixture.florida.schools
    .filter((school) => pointInBbox(school.lon, school.lat, bbox))
    .map((school) =>
      toSchoolRating({
        id: school.id,
        name: school.name,
        city: school.city,
        state: "FL",
        level: school.level,
        rating: school.grade ?? school.improvement,
        ratingKind: school.grade ? "letter" : school.improvement ? "improvement" : null,
        year: fixture.florida.year,
        source: fixture.florida.source,
        sourceUrl: fixture.florida.sourceUrl,
        reportCardUrl: school.reportCardUrl,
        lon: school.lon,
        lat: school.lat,
      }),
    );
}

let ocpsIndex: Map<number, FloridaSchool> | null = null;

function ocpsByNumber(): Map<number, FloridaSchool> {
  const fixture = loadSchoolRatings();
  if (!fixture) return new Map();
  if (ocpsIndex) return ocpsIndex;
  const index = new Map<number, FloridaSchool>();
  for (const school of fixture.florida.schools) {
    if (school.district !== "48" || !school.school) continue;
    const number = Number(school.school);
    if (Number.isFinite(number)) index.set(number, school);
  }
  ocpsIndex = index;
  return index;
}

function pointLonLat(feature: unknown): { lon: number; lat: number } | null {
  if (!feature || typeof feature !== "object") return null;
  const geometry = (feature as { geometry?: { x?: number; y?: number } }).geometry;
  const x = geometry?.x;
  const y = geometry?.y;
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return { lon: x as number, lat: y as number };
}

async function orangeZonedSchools(lon: number, lat: number): Promise<SchoolRating[]> {
  if (!pointInBbox(lon, lat, ORANGE_UTILITY_BBOX)) return [];
  const zones = [
    { service: ORANGE_ELEM_ZONES, level: "Elementary" },
    { service: ORANGE_MIDDLE_ZONES, level: "Middle" },
    { service: ORANGE_HIGH_ZONES, level: "High" },
  ];
  const hits = (
    await Promise.all(
      zones.map(async (zone) => {
        try {
          const payload = await getJson(pointQuery(zone.service, lon, lat, "SCHL_NUM,SCHOOL,TYPE"));
          const attrs = attrsOf(featuresOf(payload)[0]);
          const number = Number(textAttr(attrs, "SCHL_NUM"));
          const name = textAttr(attrs, "SCHOOL");
          if (!name || !Number.isFinite(number)) return null;
          return { number, name, level: zone.level };
        } catch {
          return null;
        }
      }),
    )
  ).filter((hit): hit is { number: number; name: string; level: string } => Boolean(hit));
  if (!hits.length) return [];

  const where = hits.map((hit) => `SCHL_NUM=${hit.number}`).join(" OR ");
  const campuses = new Map<number, { lon: number; lat: number }>();
  try {
    const payload = await getJson(
      `${ORANGE_SCHOOL_POINTS}/query?where=${encodeURIComponent(where)}&outFields=SCHL_NUM&returnGeometry=true&outSR=4326&f=json`,
    );
    for (const feature of featuresOf(payload)) {
      const number = Number(textAttr(attrsOf(feature), "SCHL_NUM"));
      const point = pointLonLat(feature);
      if (Number.isFinite(number) && point) campuses.set(number, point);
    }
  } catch {
    // Zone names still stand. Campus distance stays unpublished.
  }

  const grades = ocpsByNumber();
  const fixture = loadSchoolRatings();
  return hits.map((hit) => {
    const campus = campuses.get(hit.number);
    const graded = grades.get(hit.number);
    const rating = graded?.grade ?? graded?.improvement ?? null;
    return toSchoolRating({
      id: `ocps-${hit.number}`,
      name: graded?.name || hit.name,
      city: graded?.city ?? null,
      state: "FL",
      level: `${hit.level} attendance zone`,
      rating,
      ratingKind: graded?.grade ? "letter" : graded?.improvement ? "improvement" : null,
      year: rating ? fixture?.florida.year ?? "2025-26" : null,
      source: rating ? FL_GRADES_SOURCE : "Orange County Public Schools attendance zones",
      sourceUrl: rating ? FL_GRADES_URL : "https://www.orangecountyfl.net/PlanningDevelopment/InteractiveMapping.aspx",
      reportCardUrl: graded?.reportCardUrl ?? null,
      lon: campus?.lon ?? lon,
      lat: campus?.lat ?? lat,
      zoned: true,
    });
  }).map((school, index) => {
    const campus = campuses.get(hits[index].number);
    return {
      ...school,
      distanceMiles: campus ? Math.round(haversineMiles(lon, lat, campus.lon, campus.lat) * 10) / 10 : null,
    };
  });
}

function sameZonedSchool(zoned: SchoolRating, nearby: SchoolRating): boolean {
  const zone = zoned.name.toUpperCase().replace(/[^A-Z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  const other = nearby.name.toUpperCase().replace(/[^A-Z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  if (!zone || !other) return false;
  if (other !== zone && !other.startsWith(`${zone} `) && !zone.startsWith(`${other} `)) return false;
  const level = zoned.level?.toUpperCase() ?? "";
  if (level.includes("ELEMENTARY") && /MIDDLE|HIGH/.test(other) && !/ELEMENTARY/.test(other)) return false;
  if (level.includes("MIDDLE") && /ELEMENTARY|HIGH/.test(other) && !/MIDDLE/.test(other)) return false;
  if (level.includes("HIGH") && /ELEMENTARY|MIDDLE/.test(other) && !/HIGH/.test(other)) return false;
  return true;
}

async function cmsZonedSchools(lon: number, lat: number): Promise<SchoolRating[]> {
  if (!pointInBbox(lon, lat, MECK_BBOX)) return [];
  const zones = [
    { service: CMS_ELEM_ZONES, num: "elem_num", name: "elem_name", level: "Elementary" },
    { service: CMS_MIDDLE_ZONES, num: "midd_num", name: "midd_name", level: "Middle" },
    { service: CMS_HIGH_ZONES, num: "high_num", name: "high_name", level: "High" },
  ];
  const hits = (
    await Promise.all(
      zones.map(async (zone) => {
        try {
          const payload = await getJson(pointQuery(zone.service, lon, lat, `${zone.num},${zone.name}`));
          const attrs = attrsOf(featuresOf(payload)[0]);
          const number = Number(textAttr(attrs, zone.num));
          const name = textAttr(attrs, zone.name);
          if (!name || !Number.isFinite(number)) return null;
          return { number, name, level: zone.level };
        } catch {
          return null;
        }
      }),
    )
  ).filter((hit): hit is { number: number; name: string; level: string } => Boolean(hit));
  if (!hits.length) return [];

  const campuses = new Map<number, { lon: number; lat: number }>();
  try {
    const where = hits.map((hit) => `school_num=${Math.round(hit.number)}`).join(" OR ");
    const payload = await getJson(
      `${CMS_SCHOOL_POINTS}/query?where=${encodeURIComponent(where)}&outFields=school_num,school_typ&returnGeometry=true&outSR=4326&f=json`,
    );
    const wanted = new Map(hits.map((hit) => [Math.round(hit.number), hit.level.toUpperCase()]));
    for (const feature of featuresOf(payload)) {
      const number = Math.round(Number(textAttr(attrsOf(feature), "school_num")));
      const point = pointLonLat(feature);
      const level = wanted.get(number);
      const type = textAttr(attrsOf(feature), "school_typ")?.toUpperCase() ?? "";
      if (!point || !level) continue;
      if (type && type !== level && campuses.has(number)) continue;
      if (!campuses.has(number) || type === level) campuses.set(number, point);
    }
  } catch {
    // Zone names still stand. Campus distance stays unpublished.
  }

  const grades = loadCmsGrades();
  const alt = new Set((grades?.alternativeModel ?? []).map((school) => school.code));
  return hits.map((hit) => {
    const code = cmsAgencyCode(hit.number);
    const graded = code ? grades?.byCode[code] : undefined;
    const campus = campuses.get(Math.round(hit.number));
    const letter = graded?.grade ?? null;
    const onAltModel = Boolean(code && alt.has(code));
    const rating = letter && !onAltModel ? letter : null;
    const school = toSchoolRating({
      id: `cms-${code ?? Math.round(hit.number)}`,
      name: graded?.name || hit.name,
      city: null,
      state: "NC",
      level: `${hit.level} attendance zone`,
      rating,
      ratingKind: rating ? "letter" : null,
      year: rating || onAltModel ? grades?.year ?? "2025-26" : null,
      source: rating || onAltModel ? grades?.source ?? CMS_GRADES_SOURCE : CMS_ZONES_SOURCE,
      sourceUrl: rating || onAltModel ? grades?.sourceUrl ?? CMS_GRADES_URL : CMS_ZONES_URL,
      reportCardUrl: code && grades?.reportCardUrl ? grades.reportCardUrl.replace("{code}", code) : null,
      lon: campus?.lon ?? lon,
      lat: campus?.lat ?? lat,
      zoned: true,
    });
    if (onAltModel) {
      school.summary =
        "NCDPI 2025-26 lists this school on the alternative accountability model, not an A–F school performance grade.";
    }
    return {
      ...school,
      distanceMiles: campus ? Math.round(haversineMiles(lon, lat, campus.lon, campus.lat) * 10) / 10 : null,
    };
  });
}

export async function meckTractAtPoint(lon: number, lat: number): Promise<TractAtPoint | null> {
  if (!pointInBbox(lon, lat, MECK_BBOX)) return null;
  try {
    const payload = await getJson(pointQuery(MECK_TRACTS, lon, lat, "geoid20,name20"));
    const attrs = attrsOf(featuresOf(payload)[0]);
    return describeMeckTract({ geoid: textAttr(attrs, "geoid20"), name: textAttr(attrs, "name20") });
  } catch {
    return describeMeckTract({ failed: true });
  }
}

function ncesSchool(attrs: Record<string, unknown>): SchoolRating | null {
  const lon = Number(textAttr(attrs, "LON"));
  const lat = Number(textAttr(attrs, "LAT"));
  const name = textAttr(attrs, "NAME");
  if (!name || !Number.isFinite(lon) || !Number.isFinite(lat)) return null;
  const state = textAttr(attrs, "STATE");
  const nces = textAttr(attrs, "NCESSCH");
  const fixture = loadSchoolRatings();
  const cms = loadCmsGrades();
  const cmsGrade = state === "NC" && nces ? cms?.byNces[nces] ?? null : null;
  const ncGrade = cmsGrade ?? (state === "NC" && nces ? fixture?.northCarolina.byNces[nces] ?? null : null);
  const portal = state ? STATE_REPORT_CARDS[state] : null;
  const graded = Boolean(ncGrade);
  return toSchoolRating({
    id: nces ?? `${state ?? "school"}-${lon}-${lat}`,
    name,
    city: textAttr(attrs, "CITY"),
    state,
    level: null,
    rating: ncGrade,
    ratingKind: ncGrade ? "letter" : null,
    year: cmsGrade ? cms?.year ?? "2025-26" : graded ? fixture?.northCarolina.year ?? null : null,
    source: cmsGrade ? cms?.source ?? CMS_GRADES_SOURCE : graded ? fixture?.northCarolina.source ?? null : NCES_SOURCE,
    sourceUrl: cmsGrade ? cms?.sourceUrl ?? CMS_GRADES_URL : graded ? fixture?.northCarolina.sourceUrl ?? null : NCES_SOURCE_URL,
    reportCardUrl: portal?.url ?? null,
    lon,
    lat,
  });
}

export async function schoolsNear(lon: number, lat: number): Promise<{ schools: SchoolRating[]; note: string }> {
  const pad = 0.06;
  const bbox: BBox = [lon - pad, lat - pad, lon + pad, lat + pad];
  const zoned = (
    await Promise.all([
      orangeZonedSchools(lon, lat).catch(() => [] as SchoolRating[]),
      cmsZonedSchools(lon, lat).catch(() => [] as SchoolRating[]),
    ])
  ).flat();
  try {
    const local = floridaSchoolsInBbox(bbox);
    const params = new URLSearchParams({
      geometry: `${bbox[0]},${bbox[1]},${bbox[2]},${bbox[3]}`,
      geometryType: "esriGeometryEnvelope",
      inSR: "4326",
      spatialRel: "esriSpatialRelIntersects",
      where: loadSchoolRatings() ? "STATE <> 'FL'" : "1=1",
      outFields: "NCESSCH,NAME,CITY,STATE,LAT,LON",
      returnGeometry: "false",
      resultRecordCount: "200",
      f: "json",
    });
    const payload = await getJson(`${NCES_SCHOOLS_SERVICE}/query?${params}`);
    const remote = featuresOf(payload)
      .map((feature) => ncesSchool(attrsOf(feature)))
      .filter((school): school is SchoolRating => Boolean(school));
    const schools = [
      ...zoned,
      ...nearestSchools([...local, ...remote], lon, lat).filter(
        (school) => !zoned.some((zone) => sameZonedSchool(zone, school)),
      ),
    ].slice(0, 8);
    const fixture = loadSchoolRatings();
    const orangeNote = zoned.some((school) => school.id.startsWith("ocps-"))
      ? " Zoned elementary, middle, and high schools are OCPS attendance zones, not the nearest campus. "
      : zoned.some((school) => school.id.startsWith("cms-"))
        ? " Zoned elementary, middle, and high schools are CMS attendance zones, not the nearest campus. Charlotte-Mecklenburg letters are the 2025-26 NCDPI file for LEA 600. "
        : " ";
    const note = fixture
      ? `${UTILITY_LAYER_NOTE.schools}${orangeNote}`
      : `Florida letter grades are not loaded in this build. Dots still use NCES locations and state report-card links. No grade is invented.${orangeNote}`;
    return { schools, note };
  } catch {
    const schools = [...zoned, ...nearestSchools(floridaSchoolsInBbox(bbox), lon, lat)].slice(0, 8);
    return {
      schools,
      note: schools.length
        ? "Nearby states’ school locations did not load. Florida grades in this extract are still listed."
        : "School locations did not load. Ratings are unknown, not low.",
    };
  }
}

export async function screeningAtPoint(lon: number, lat: number, parcelId?: string | null): Promise<ScreeningPoint> {
  const cobb = cobbBatchParcel(parcelId);
  const dekalb = cobb ? null : dekalbBatchParcel(parcelId);
  const batchOverlay = cobb ? cobbScreeningOverlay(cobb, lon, lat) : dekalb ? dekalbScreeningOverlay(dekalb, lon, lat) : null;
  const [flood, wetland, water, sewer, power, gas, schools, tract] = await Promise.allSettled([
    batchOverlay ? Promise.resolve(batchOverlay.flood) : floodAtPoint(lon, lat),
    wetlandAtPoint(lon, lat),
    batchOverlay ? Promise.resolve(batchOverlay.utilities[0]) : utilityAtPoint("water", lon, lat),
    batchOverlay ? Promise.resolve(batchOverlay.utilities[1]) : utilityAtPoint("sewer", lon, lat),
    batchOverlay ? Promise.resolve(batchOverlay.utilities[2]) : utilityAtPoint("power", lon, lat),
    batchOverlay ? Promise.resolve(batchOverlay.utilities[3]) : utilityAtPoint("gas", lon, lat),
    batchOverlay ? Promise.resolve({ schools: batchOverlay.schools, note: batchOverlay.schoolsNote }) : schoolsNear(lon, lat),
    batchOverlay ? Promise.resolve(null) : meckTractAtPoint(lon, lat),
  ]);
  const schoolResult =
    schools.status === "fulfilled"
      ? schools.value
      : { schools: [], note: "School locations did not load. Ratings are unknown, not low." };
  return {
    flood: flood.status === "fulfilled" ? flood.value : describeFloodZone({ featuresFound: false, failed: true }),
    wetland: wetland.status === "fulfilled" ? wetland.value : describeWetland({ failed: true }),
    utilities: [
      water.status === "fulfilled" ? water.value : describeUtility({ kind: "water", providers: [], covered: true, failed: true }),
      sewer.status === "fulfilled" ? sewer.value : describeUtility({ kind: "sewer", providers: [], covered: true, failed: true }),
      power.status === "fulfilled" ? power.value : describeUtility({ kind: "power", providers: [], covered: true, failed: true, powerLayer: "hifld" }),
      gas.status === "fulfilled" ? gas.value : describeUtility({ kind: "gas", providers: [], covered: false }),
    ],
    schools: schoolResult.schools,
    schoolsNote: schoolResult.note,
    tract: tract.status === "fulfilled" ? tract.value : null,
  };
}

export type ScreeningCollection = {
  type: "FeatureCollection";
  features: GeoJSON.Feature[];
  meta: { status: "ok" | "zoom" | "unknown" | "unavailable"; summary: string };
};

const EMPTY_COLLECTION = (status: ScreeningCollection["meta"]["status"], summary: string): ScreeningCollection => ({
  type: "FeatureCollection",
  features: [],
  meta: { status, summary },
});

function slimGeometry(payload: unknown, nameField: string): GeoJSON.Feature[] {
  return featuresOf(payload).slice(0, 80).flatMap((feature) => {
    if (!feature || typeof feature !== "object") return [];
    const record = feature as { geometry?: GeoJSON.Geometry | null; attributes?: Record<string, unknown>; properties?: Record<string, unknown> };
    if (!record.geometry) return [];
    const attrs = record.attributes ?? record.properties ?? {};
    const name = textAttr(attrs, nameField, "NAME", "SERVEDBY", "COMPANY") ?? "Unnamed provider";
    return [{ type: "Feature" as const, geometry: record.geometry, properties: { name } }];
  });
}

const DCSD_ZONE_LAYERS = [
  { service: DCSD_ELEM_ZONES, fields: "DDP_ES_Nam,ES_Name", level: "Elementary" },
  { service: DCSD_MIDDLE_ZONES, fields: "DDP_MS_Name,MS_Name", level: "Middle" },
  { service: DCSD_HIGH_ZONES, fields: "DDP_HS_Nam,HS_Name", level: "High" },
] as const;

function dcsdZoneFeatures(payload: unknown, fields: string, level: string): GeoJSON.Feature[] {
  const [fullName, shortName] = fields.split(",");
  return featuresOf(payload).slice(0, 200).flatMap((feature) => {
    if (!feature || typeof feature !== "object") return [];
    const record = feature as { geometry?: GeoJSON.Geometry | null; properties?: Record<string, unknown>; attributes?: Record<string, unknown> };
    if (!record.geometry) return [];
    const attrs = record.properties ?? record.attributes ?? {};
    const name = textAttr(attrs, fullName, shortName) ?? "Unnamed school";
    return [{ type: "Feature" as const, geometry: record.geometry, properties: { name, level } }];
  });
}

/** DCSD attendance polygons. Empty outside DeKalb and when the view is larger than a county. */
export async function dcsdZonePolygons(bbox: BBox): Promise<ScreeningCollection> {
  if (bboxSpan(bbox) > MAX_VECTOR_SPAN) {
    return EMPTY_COLLECTION("zoom", "Zoom in to about a county before DeKalb school zones load.");
  }
  if (!bboxesIntersect(bbox, DEKALB_BBOX)) {
    return EMPTY_COLLECTION("unknown", "DeKalb County School District zones draw only inside DeKalb County.");
  }
  try {
    const groups = await Promise.all(
      DCSD_ZONE_LAYERS.map(async (layer) => {
        const params = new URLSearchParams({
          geometry: bbox.join(","),
          geometryType: "esriGeometryEnvelope",
          inSR: "4326",
          spatialRel: "esriSpatialRelIntersects",
          outFields: layer.fields,
          returnGeometry: "true",
          outSR: "4326",
          maxAllowableOffset: "0.002",
          geometryPrecision: "4",
          f: "geojson",
        });
        const payload = await getJson(`${layer.service.replace(/\/$/, "")}/query?${params}`);
        return dcsdZoneFeatures(payload, layer.fields, layer.level);
      }),
    );
    return {
      type: "FeatureCollection",
      features: groups.flat(),
      meta: { status: "ok", summary: "DeKalb County School District attendance zones." },
    };
  } catch {
    return EMPTY_COLLECTION("unavailable", "DeKalb school zones did not load.");
  }
}

export async function utilityPolygons(kind: UtilityKind, bbox: BBox): Promise<ScreeningCollection> {
  if (bboxSpan(bbox) > MAX_VECTOR_SPAN) {
    return EMPTY_COLLECTION("zoom", "Zoom in to about a county before this utility layer loads.");
  }
  const orangeView = bboxesIntersect(bbox, ORANGE_UTILITY_BBOX);
  if (!orangeView && kind !== "power") {
    return EMPTY_COLLECTION(
      "unknown",
      kind === "water" ? UTILITY_LAYER_NOTE.water : UTILITY_LAYER_NOTE.sewer,
    );
  }
  const ocflPower = kind === "power" && orangeView;
  const service = kind === "water" ? ORANGE_WATER_SERVICE : kind === "sewer" ? ORANGE_SEWER_SERVICE : ocflPower ? ORANGE_POWER_SERVICE : HIFLD_POWER_SERVICE;
  const field = kind === "water" || kind === "sewer" ? "SERVEDBY" : ocflPower ? "COMPANY" : "NAME";
  const params = new URLSearchParams({
    geometry: bbox.join(","),
    geometryType: "esriGeometryEnvelope",
    inSR: "4326",
    spatialRel: "esriSpatialRelIntersects",
    outFields: field,
    returnGeometry: "true",
    outSR: "4326",
    maxAllowableOffset: kind === "power" && !ocflPower ? "0.02" : "0.002",
    geometryPrecision: kind === "power" && !ocflPower ? "3" : "4",
    f: "geojson",
  });
  try {
    const payload = await getJson(`${service.replace(/\/$/, "")}/query?${params}`);
    const features = slimGeometry(payload, field);
    return {
      type: "FeatureCollection",
      features,
      meta: {
        status: "ok",
        summary: kind === "power" ? UTILITY_LAYER_NOTE.power : kind === "water" ? UTILITY_LAYER_NOTE.water : UTILITY_LAYER_NOTE.sewer,
      },
    };
  } catch {
    return EMPTY_COLLECTION("unavailable", "This utility service did not respond. Availability is unknown.");
  }
}

export async function schoolsInView(bbox: BBox): Promise<ScreeningCollection> {
  if (bboxSpan(bbox) > MAX_VECTOR_SPAN) {
    return EMPTY_COLLECTION("zoom", "Zoom in to about a county before school dots load.");
  }
  const florida = floridaSchoolsInBbox(bbox).map(schoolFeature);
  const states = loadSchoolRatings() ? "GA,NC,SC,TN,AL" : "FL,GA,NC,SC,TN,AL";
  const params = new URLSearchParams({
    geometry: bbox.join(","),
    geometryType: "esriGeometryEnvelope",
    inSR: "4326",
    spatialRel: "esriSpatialRelIntersects",
    where: `STATE IN ('${states.split(",").join("','")}')`,
    outFields: "NCESSCH,NAME,CITY,STATE,LAT,LON",
    returnGeometry: "false",
    resultRecordCount: String(SCHOOL_CAP),
    f: "json",
  });
  try {
    const payload = await getJson(`${NCES_SCHOOLS_SERVICE}/query?${params}`);
    const remote = featuresOf(payload)
      .map((feature) => ncesSchool(attrsOf(feature)))
      .filter((school): school is SchoolRating => Boolean(school))
      .filter((school) => pointInBbox(school.lon, school.lat, bbox))
      .map(schoolFeature);
    const gradedFlorida = Boolean(loadSchoolRatings());
    return {
      type: "FeatureCollection",
      features: [...florida, ...remote].slice(0, SCHOOL_CAP),
      meta: {
        status: "ok",
        summary: gradedFlorida
          ? UTILITY_LAYER_NOTE.schools
          : "Florida letter grades are not in this build. Dots are NCES locations with a link to the state report card. No grade is invented.",
      },
    };
  } catch {
    if (florida.length) {
      return {
        type: "FeatureCollection",
        features: florida.slice(0, SCHOOL_CAP),
        meta: { status: "ok", summary: "NCES locations did not load. Florida grades in this extract are still shown." },
      };
    }
    return EMPTY_COLLECTION("unavailable", "School locations did not load.");
  }
}

function schoolFeature(school: SchoolRating): GeoJSON.Feature {
  return {
    type: "Feature",
    geometry: { type: "Point", coordinates: [school.lon, school.lat] },
    properties: {
      name: school.name,
      rating: school.rating ?? "",
      summary: school.summary,
      reportCardUrl: school.reportCardUrl ?? "",
      source: school.source ?? "",
    },
  };
}
