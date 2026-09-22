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
};

export type OpportunityZoneProperties = {
  id: string;
  tractGeoid: string;
  tract: string | null;
  name: string | null;
  rural: boolean | null;
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

/** Status chip for the seven-market rural pack. Never a certified 2027 QOZ. */
export const RURAL_ELIGIBLE_STATUS_CHIP = "Eligible (rural) — not designated";

export const SHED_CAVEAT =
  "90-minute sheds are approximate county rings, not drive-time isochrones. Outer-edge counties are flagged in tract notes.";

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
};

export type MarketCountySummary = {
  county: string;
  state: string;
  count: number;
  outerEdge: boolean;
};

export type MarketSummary = {
  market: MarketId;
  rowCount: number;
  bounds: [[number, number], [number, number]];
  center: [number, number];
  counties: MarketCountySummary[];
};

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
  source: string;
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
