import { NextResponse } from "next/server";
import { getParcelProvider } from "@/lib/data/adapters";
import { loadFluConfig, loadZoningConfig } from "@/lib/data/loadFixtures";
import { filterParcels, parcelFiltersFromSearchParams } from "@/lib/filters";
import { isSearchMarketId } from "@/lib/markets";
import type { BBox, ParcelFeature } from "@/lib/types";

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
  const market = marketParam && isSearchMarketId(marketParam) ? marketParam : null;
  const county = url.searchParams.get("county");
  const state = url.searchParams.get("state") ?? (county && market === "Orlando" ? "Florida" : null);
  const bbox = parseBbox(url.searchParams.get("bbox"));
  const source = url.searchParams.get("source") === "live" ? "live" : "fixture";
  const limit = Number(url.searchParams.get("limit") ?? (source === "live" ? 800 : 4000));
  const applyFilters = url.searchParams.get("filter") === "1";
  const includeExcluded = url.searchParams.get("includeExcluded") === "1";
  const filters = parcelFiltersFromSearchParams(url.searchParams);

  try {
    const provider = getParcelProvider();
    const [zoningConfig, fluConfig] = applyFilters
      ? await Promise.all([loadZoningConfig(), loadFluConfig()])
      : [null, null];

    if (market === "Orlando" && provider.queryOrlandoParcels) {
      const page = await provider.queryOrlandoParcels({
        bbox,
        county,
        state,
        limit: Number.isFinite(limit) ? Math.min(limit, 8000) : 4000,
        source,
        filters: applyFilters ? filters : null,
        zoningConfig,
        fluConfig,
        includeExcluded: applyFilters && includeExcluded,
      });
      return NextResponse.json({
        type: "FeatureCollection",
        features: page.collection.features,
        excluded: page.excluded,
        meta: {
          market,
          county,
          state,
          bbox,
          source,
          total: page.collection.features.length,
          totalInBbox: page.totalInBbox,
          totalMatching: page.totalMatching,
          truncated: page.truncated,
          filters: applyFilters ? filters : undefined,
        },
      });
    }

    if (market && market !== "Orlando" && provider.queryMarketParcels) {
      const page = await provider.queryMarketParcels(market, {
        bbox,
        county,
        state,
        limit: Number.isFinite(limit) ? Math.min(limit, 8000) : 4000,
        filters: applyFilters ? filters : null,
        zoningConfig,
        fluConfig,
        includeExcluded: applyFilters && includeExcluded,
      });
      return NextResponse.json({
        type: "FeatureCollection",
        features: page.collection.features,
        excluded: page.excluded,
        meta: {
          market,
          county,
          state,
          bbox,
          source: "fixture",
          total: page.collection.features.length,
          totalInBbox: page.totalInBbox,
          totalMatching: page.totalMatching,
          truncated: page.truncated,
          filters: applyFilters ? filters : undefined,
        },
      });
    }

    const collection = await provider.listParcels();
    let features: ParcelFeature[] = collection.features;
    if (applyFilters && zoningConfig && fluConfig) {
      features = filterParcels(features, filters, zoningConfig, fluConfig);
    }
    return NextResponse.json({
      type: "FeatureCollection",
      features,
      excluded: [],
      meta: {
        market,
        county,
        state,
        bbox,
        source,
        total: features.length,
        totalInBbox: collection.features.length,
        totalMatching: features.length,
        truncated: false,
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
