export type IncomeGeography = "tract" | "blockGroup";

/** Zoning / FLU search modes. `zoning` is the historical MF-capable default. */
export type LandUseFilter = "off" | "zoning" | "non-mf" | "flu" | "rezoning" | "either" | "both";

export type OzFilter = "either" | "in" | "out" | "rural-eligible" | "non-rural-eligible";

export type DistrictStatus = "permitted" | "conditional" | "maybe" | "not-mf";

export type CoverageLevel = "verified" | "partial" | "unverified";

export type MailingAddress = {
  line1: string | null;
  line2: string | null;
  city: string | null;
  state: string | null;
  zip: string | null;
};

export type LastSale = {
  date: string | null;
  price: number | null;
  qualified: string | null;
};

export type TaxInfo = {
  marketValue: number | null;
  assessedValue: number | null;
  taxableValue: number | null;
  taxes: number | null;
};

export type IncomeInfo = {
  geoid: string | null;
  name: string | null;
  medianHouseholdIncome: number | null;
  medianHouseholdIncomeMoe: number | null;
};

export type NearestRoad = {
  aadt: number | null;
  year: number | null;
  roadwayId: string | null;
  from: string | null;
  to: string | null;
  distanceMeters: number | null;
};

export type FluInfo = {
  code: string | null;
  label: string | null;
  jurisdiction: string | null;
  source: string | null;
};

export type OpportunityZoneInfo = {
  inOpportunityZone: boolean;
  tractGeoid: string | null;
  tractName: string | null;
  source: string | null;
  /** Notice 2025-50 rural flag for a current designated QOZ. Null when the parcel is not in one. */
  designatedRural?: boolean | null;
};

/**
 * Rev. Proc. 2026-14 nomination eligibility. This is not a 2027 designation.
 * `rural` is the appendix Rural Status column, and is null when the tract is not eligible.
 */
export type Oz2EligibilityInfo = {
  eligible: boolean;
  rural: boolean | null;
  tractGeoid: string | null;
  tractName: string | null;
  designation: "eligible-for-nomination" | "not-eligible";
  source: string | null;
};

export type Oz2TractProperties = {
  id: string;
  tractGeoid: string;
  tract: string | null;
  name: string | null;
  rural: boolean;
  designation: "eligible-for-nomination";
  source: string | null;
  /** Short county name, without a "County" suffix (for example "Orange"). */
  county?: string | null;
  state?: string | null;
  /** Orange County ACS median household income when the GEOID is in that fixture. */
  medianHouseholdIncome?: number;
};

export type OpportunityZoneProperties = {
  id: string;
  tractGeoid: string;
  tract: string | null;
  name: string | null;
  rural: boolean | null;
  /** Short county name, without a "County" suffix. */
  county?: string | null;
  state?: string | null;
};

export type OpportunityZoneFeature = GeoJSON.Feature<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  OpportunityZoneProperties
>;

export const MARKETS = [
  "Atlanta",
  "Tampa",
  "Orlando",
  "Charleston",
  "Nashville",
  "Charlotte",
  "Raleigh-Durham",
] as const;

export type MarketId = (typeof MARKETS)[number];

/**
 * Smaller MSAs, visually secondary to the seven primary markets.
 * Florida markets stay together: SWFL and the Heartland shelf, east coast south to north,
 * then North-Central Florida, Big Bend, and the panhandle. Jackson is Jackson, Tennessee.
 * Heartland is a parcel shelf with no eligible-tract rows.
 */
export const OTHER_MARKETS = [
  "SWFL",
  "Heartland",
  "Vero Beach",
  "Melbourne",
  "Jacksonville",
  "North-Central Florida",
  "Big Bend",
  "Pensacola",
  "Birmingham",
  "Mobile",
  "Huntsville",
  "Savannah",
  "Columbia",
  "Greenville",
  "Chattanooga",
  "Knoxville",
  "Memphis",
  "Jackson",
  "Winston-Salem",
  "Wilmington",
] as const;

export type OtherMarketId = (typeof OTHER_MARKETS)[number];

export type SearchMarketId = MarketId | OtherMarketId;

/** Rural, urban (non-rural eligible), or both. */
export type TractClassView = "both" | "rural" | "urban";

/** Status chip for the seven-market rural pack. Never a certified 2027 QOZ. */
export const RURAL_ELIGIBLE_STATUS_CHIP = "Eligible (rural) — not designated";

/**
 * Status chip for the urban pack and the other-MSA pack.
 * Rural vs urban is a separate flag. This chip is never a designation.
 */
export const ELIGIBLE_NOT_DESIGNATED_STATUS = "Eligible — not designated";

/**
 * Secondary status for South Carolina tracts after the Sep 10, 2026 governor filing.
 * The nominated GEOID list is not public, so this is not a designation.
 */
export const SC_GOVERNOR_FILED_STATUS = "Governor-filed — list not public yet / not designated";

export const SC_COMMERCE_OZ_URL = "https://www.sccommerce.com/opportunity-zone";

export const SHED_CAVEAT =
  "90-minute sheds are approximate county rings, not drive-time isochrones. Outer-edge counties are flagged in tract notes.";

/** Underwriting priority among rural-eligible tracts. Not a nomination. */
export type MfPriorityTier = "A" | "B";

/** `all` keeps every rural tract and still highlights the shortlist. */
export type MfPriorityView = "all" | "priority" | "A" | "B";

export type MfPriorityInfo = {
  tier: MfPriorityTier;
  rank: number;
  place: string;
  mfRationale: string;
  acreageRealism: string;
  notes: string;
};

export type ScMfPriorityTract = {
  market: MarketId;
  state: "South Carolina";
  county: string;
  geoid: string;
  place: string;
  rural: "Y";
  status: string;
  tier: MfPriorityTier;
  rank: number;
  mfRationale: string;
  acreageRealism: string;
  lat: number;
  lon: number;
  notes: string;
  sourceStatus: string;
};

export type ScMfPriorityCatalog = {
  generatedAt: string;
  sourceCsv: string;
  statusChip: string;
  governorFiledStatus: string;
  disclaimer: string;
  rowCount: number;
  tierACount: number;
  tierBCount: number;
  rows: ScMfPriorityTract[];
};

export type RuralMarketTractRow = {
  market: MarketId;
  state: string;
  county: string;
  geoid: string;
  placeOrCorridor: string;
  rural: "Y";
  status: string;
  lat: number;
  lon: number;
  notes: string;
  outerEdge: boolean;
  specialUse: boolean;
  /** Joined from the SC multifamily shortlist. Absent on the seven-market fixture. */
  mfPriority?: MfPriorityInfo | null;
};

export type MarketCountySummary = {
  county: string;
  state: string;
  count: number;
  outerEdge: boolean;
};

export type MarketSummary = {
  market: SearchMarketId;
  rowCount: number;
  ruralCount?: number;
  urbanCount?: number;
  bounds: [[number, number], [number, number]];
  center: [number, number];
  counties: MarketCountySummary[];
};

/** Urban 7-market pack, or the smaller MSAs (rural and urban together). */
export type EligibleTractRow = {
  market: SearchMarketId;
  state: string;
  county: string;
  geoid: string;
  placeOrCorridor: string;
  rural: "Y" | "N";
  status: string;
  lat: number;
  lon: number;
  notes: string;
  outerEdge: boolean;
  specialUse: boolean;
  mfPriority?: MfPriorityInfo | null;
};

export type EligibleMarketsCatalog = {
  generatedAt: string;
  sourceCsv: string;
  geometrySource: string;
  shedCaveat: string;
  statusChip: string;
  pack: "urban-7" | "other-msas";
  rowCount: number;
  uniqueGeoidCount: number;
  ruralRowCount: number;
  urbanRowCount: number;
  markets: MarketSummary[];
  rows: EligibleTractRow[];
};

export type EligiblePackTractProperties = {
  id: string;
  tractGeoid: string;
  tract: string | null;
  name: string | null;
  county: string;
  state: string;
  rural: boolean;
  designation: "eligible-for-nomination";
  statusChip: string;
  markets: SearchMarketId[];
  packs: Array<"urban-7" | "other-msas">;
  placeOrCorridor: string;
  notes: string;
  outerEdge: boolean;
  specialUse: boolean;
  lat: number;
  lon: number;
  source: string;
  /**
   * ACS tract median household income when this GEOID is in the Orange County
   * income fixture. Absent for every other tract — do not treat absence as zero.
   */
  medianHouseholdIncome?: number;
};

export type EligiblePackTractFeature = GeoJSON.Feature<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  EligiblePackTractProperties
>;

export type EligiblePackTractCollection = GeoJSON.FeatureCollection<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  EligiblePackTractProperties
>;

export type RuralMarketsCatalog = {
  generatedAt: string;
  sourceCsv: string;
  geometrySource: string;
  shedCaveat: string;
  statusChip: string;
  rowCount: number;
  uniqueGeoidCount: number;
  parcelNote: string;
  markets: MarketSummary[];
  rows: RuralMarketTractRow[];
};

export type RuralMarketTractProperties = {
  id: string;
  tractGeoid: string;
  tract: string | null;
  name: string | null;
  county: string;
  state: string;
  rural: true;
  designation: "eligible-for-nomination";
  statusChip: string;
  markets: MarketId[];
  placeOrCorridor: string;
  notes: string;
  outerEdge: boolean;
  specialUse: boolean;
  lat: number;
  lon: number;
  source: string;
  /** Orange County ACS median household income when the GEOID is in that fixture. */
  medianHouseholdIncome?: number;
};

export type RuralMarketTractFeature = GeoJSON.Feature<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  RuralMarketTractProperties
>;

export type RuralMarketTractCollection = GeoJSON.FeatureCollection<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  RuralMarketTractProperties
>;

export type Oz2TractFeature = GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon, Oz2TractProperties>;

export type Oz2TractCollection = GeoJSON.FeatureCollection<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  Oz2TractProperties
>;

export type OpportunityZoneCollection = GeoJSON.FeatureCollection<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  OpportunityZoneProperties
>;

export type ParcelProperties = {
  id: string;
  parcelId: string;
  /** Five-digit county FIPS when known (Orlando shed partitions). */
  countyFips?: string | null;
  countyName?: string | null;
  state?: string | null;
  marketIds?: SearchMarketId[];
  situsAddress: string | null;
  situsCity: string | null;
  situsZip: string | null;
  jurisdictionCode: string | null;
  ownerName: string | null;
  ownerName2: string | null;
  propertyName: string | null;
  zoningCode: string | null;
  zoningDistrict: string | null;
  jurisdictionPrefix: string | null;
  dorCode: string | null;
  acreage: number | null;
  centroid: [number, number];
  lastSale: LastSale;
  tax: TaxInfo;
  mailingAddress: MailingAddress;
  incomeTract: IncomeInfo | null;
  incomeBlockGroup: IncomeInfo | null;
  nearestRoad: NearestRoad | null;
  flu: FluInfo | null;
  opportunityZone: OpportunityZoneInfo | null;
  oz2Eligibility: Oz2EligibilityInfo | null;
  /**
   * 1 when the parcel passes the active filters. The map uses this instead of
   * an id list, which stops matching once a dense viewport is loaded.
   */
  filterMatch?: 0 | 1;
  /** County property appraiser / parcel search landing page when known. */
  appraiserUrl?: string | null;
  /** Honest per-county gaps (no zoning, etc.). */
  dataGaps?: string[];
  source: string;
};

export type BBox = [west: number, south: number, east: number, north: number];

export type OrlandoParcelCoverage = "complete-gte-5ac" | "sample";

export type OrlandoParcelCountyMeta = {
  name: string;
  fips: string;
  featureCount: number;
  ruralEligibleParcelCount: number;
  oz2EligibleParcelCount?: number;
  zoningJoinedCount?: number;
  fluJoinedCount?: number;
  ocpaMatchedCount?: number;
  sourceCount?: number;
  droppedNoGeometry?: number;
  tileCount?: number;
  coverage: OrlandoParcelCoverage;
  partition: "tiles" | "file";
  minAcres: number;
  /** Inclusive upper bound for complete counties (150). Sample counties omit this. */
  maxAcres?: number;
  /** Parcels removed because stored acreage was above maxAcres. */
  excludedOverMaxAcres?: number;
  source: string;
  queryUrl: string;
  gaps: string[];
  path: string;
};

export type OrlandoParcelsMeta = {
  generatedAt: string;
  market: "Orlando";
  parcelCount: number;
  perCountyCap: number | null;
  minAcres: number | null;
  coreMinAcres: number;
  coreMaxAcres: number;
  tile: { originLon: number; originLat: number; tileDeg: number };
  sourcesDoc: string;
  notes: string[];
  counties: OrlandoParcelCountyMeta[];
};

export type ParcelFeature = GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon, ParcelProperties>;

export type ParcelCollection = GeoJSON.FeatureCollection<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  ParcelProperties
>;

export type TrafficFeature = GeoJSON.Feature<
  GeoJSON.LineString,
  {
    aadt: number | null;
    year: number | null;
    roadwayId: string | null;
    from: string | null;
    to: string | null;
  }
>;

export type FilterState = {
  /**
   * When false, parcel OZ radios are hidden and `ozFilter` is not applied.
   * Map overlays for eligible tracts stay independent of this switch.
   */
  considerOpportunityZone: boolean;
  /**
   * When false, zoning / FLU / rezoning radios are hidden and land use is not applied.
   */
  considerZoning: boolean;
  landUseFilter: LandUseFilter;
  includePlannedDevelopment: boolean;
  includeConditionalZoning: boolean;
  ozFilter: OzFilter;
  minAcreage: number;
  includeUnknownAcreage: boolean;
  minIncome: number;
  incomeGeography: IncomeGeography;
  includeUnknownIncome: boolean;
  minAadt: number;
  includeUnknownAadt: boolean;
};

export type ZoningToken = {
  token: string;
  label: string;
  jurisdictions?: string[];
  status?: DistrictStatus;
  why: string;
  sourceUrl?: string;
  aliases?: string[];
};

export type CodeSource = {
  label: string;
  url: string;
};

export type ZoningJurisdiction = {
  code: string;
  name: string;
  coverage: CoverageLevel;
  coverageNote?: string;
  codeSource?: CodeSource;
  districts: ZoningToken[];
};

export type ZoningConfig = {
  version: number;
  county: string;
  updatedAt: string;
  notes: string;
  sources?: CodeSource[];
  jurisdictions: ZoningJurisdiction[];
  multifamilyTokens: ZoningToken[];
  plannedDevelopmentTokens: ZoningToken[];
  notAllowedExamples: string[];
};

export type FluCategory = {
  code: string;
  jurisdiction: string;
  label: string;
  allowsMultifamily: boolean;
  status: "yes" | "maybe" | "no";
  maxDensityDuAc?: number | null;
  why: string;
  sourceUrl?: string;
};

export type FluConfig = {
  version: number;
  updatedAt: string;
  notes: string;
  sources: CodeSource[];
  categories: FluCategory[];
};

export const DEFAULT_FILTERS: FilterState = {
  considerOpportunityZone: false,
  considerZoning: false,
  landUseFilter: "zoning",
  includePlannedDevelopment: true,
  includeConditionalZoning: false,
  ozFilter: "either",
  minAcreage: 0,
  includeUnknownAcreage: true,
  minIncome: 0,
  incomeGeography: "tract",
  includeUnknownIncome: true,
  minAadt: 0,
  includeUnknownAadt: true,
};

export const LAND_USE_FILTERS: LandUseFilter[] = [
  "zoning",
  "off",
  "non-mf",
  "rezoning",
  "flu",
  "either",
  "both",
];

export const OZ_FILTERS: OzFilter[] = ["either", "rural-eligible", "non-rural-eligible", "in", "out"];

export const ACREAGE_SLIDER = {
  min: 0,
  max: 25,
  step: 0.25,
} as const;

export const ORANGE_COUNTY_BOUNDS: [[number, number], [number, number]] = [
  [-81.66, 28.34],
  [-80.99, 28.79],
];

export const ORANGE_COUNTY_CENTER: [number, number] = [-81.379, 28.538];
