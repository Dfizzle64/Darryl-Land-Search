import { NextResponse } from "next/server";
import { getParcelProvider } from "@/lib/data/adapters";
import { loadFluConfig, loadZoningConfig } from "@/lib/data/loadFixtures";
import { filterParcels } from "@/lib/filters";
import { isMarketId } from "@/lib/markets";
import {
  DEFAULT_FILTERS,
  LAND_USE_FILTERS,
  OZ_FILTERS,
  type BBox,
  type FilterState,
  type IncomeGeography,
  type LandUseFilter,
  type OzFilter,
} from "@/lib/types";

function landUseParam(value: string | null): LandUseFilter {
  if (value && (LAND_USE_FILTERS as string[]).includes(value)) {
    return value as LandUseFilter;
  }
  if (value === "0" || value === "all") return "off";
  if (value === "mf") return "zoning";
  return DEFAULT_FILTERS.landUseFilter;
}

function ozParam(value: string | null): OzFilter {
  if (value && (OZ_FILTERS as string[]).includes(value)) {
    return value as OzFilter;
  }
  return DEFAULT_FILTERS.ozFilter;
}

function parseBbox(value: string | null): BBox | null {
  if (!value) return null;
  const parts = value.split(",").map((part) => Number(part.trim()));
  if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) return null;
  const [west, south, east, north] = parts;
  if (west >= east || south >= north) return null;
  return [west, south, east, north];
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const marketParam = url.searchParams.get("market");
  const market = marketParam && isMarketId(marketParam) ? marketParam : null;
  const county = url.searchParams.get("county");
  const state = url.searchParams.get("state") ?? (county ? "Florida" : null);
  const bbox = parseBbox(url.searchParams.get("bbox"));
  const source = url.searchParams.get("source") === "live" ? "live" : "fixture";
  const limit = Number(url.searchParams.get("limit") ?? (source === "live" ? 800 : 4000));
  const applyFilters = url.searchParams.get("filter") === "1";

  const filters: FilterState = {
    ...DEFAULT_FILTERS,
    landUseFilter: landUseParam(url.searchParams.get("landUse") ?? url.searchParams.get("mf")),
    includePlannedDevelopment: url.searchParams.get("pd") !== "0",
    includeConditionalZoning: url.searchParams.get("cond") === "1",
    ozFilter: ozParam(url.searchParams.get("oz")),
    minAcreage: Number(url.searchParams.get("minAcres") ?? DEFAULT_FILTERS.minAcreage),
    includeUnknownAcreage: url.searchParams.get("unkAcres") !== "0",
    minIncome: Number(url.searchParams.get("minIncome") ?? DEFAULT_FILTERS.minIncome),
    incomeGeography: (url.searchParams.get("geo") as IncomeGeography) || DEFAULT_FILTERS.incomeGeography,
    includeUnknownIncome: url.searchParams.get("unkIncome") !== "0",
    minAadt: Number(url.searchParams.get("minAadt") ?? DEFAULT_FILTERS.minAadt),
    includeUnknownAadt: url.searchParams.get("unkAadt") !== "0",
  };

  try {
    const provider = getParcelProvider();
    let page =
      market === "Orlando" && provider.queryOrlandoParcels
        ? await provider.queryOrlandoParcels({
            bbox,
            county,
            state,
            limit: Number.isFinite(limit) ? Math.min(limit, 8000) : 4000,
            source,
          })
        : {
            collection: await provider.listParcels(),
            totalInBbox: 0,
            truncated: false,
          };
    let collection = page.collection;
    if (market !== "Orlando") {
      page = { collection, totalInBbox: collection.features.length, truncated: false };
    }

    if (applyFilters) {
      const [zoningConfig, fluConfig] = await Promise.all([loadZoningConfig(), loadFluConfig()]);
      collection = {
        type: "FeatureCollection",
        features: filterParcels(collection.features, filters, zoningConfig, fluConfig),
      };
    }

    return NextResponse.json({
      type: "FeatureCollection",
      features: collection.features,
      meta: {
        market,
        county,
        state,
        bbox,
        source,
        total: collection.features.length,
        totalInBbox: applyFilters ? collection.features.length : page.totalInBbox,
        truncated: applyFilters ? false : page.truncated,
        filters: applyFilters ? filters : undefined,
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to load parcels" },
      { status: 500 },
    );
  }
}
