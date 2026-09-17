export type IncomeGeography = "tract" | "blockGroup";

export type LandUseFilter = "off" | "zoning" | "flu" | "either" | "both";

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
  minAcreage: 0,
  includeUnknownAcreage: true,
  minIncome: 0,
  incomeGeography: "tract",
  includeUnknownIncome: true,
  minAadt: 0,
  includeUnknownAadt: true,
};

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
