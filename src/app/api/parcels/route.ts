import { NextResponse } from "next/server";
import { getParcelProvider } from "@/lib/data/adapters";
import { loadFluConfig, loadZoningConfig } from "@/lib/data/loadFixtures";
import { filterParcels } from "@/lib/filters";
import { DEFAULT_FILTERS, type FilterState, type IncomeGeography, type LandUseFilter } from "@/lib/types";

function landUseParam(value: string | null): LandUseFilter {
  if (value === "off" || value === "zoning" || value === "flu" || value === "either" || value === "both") {
    return value;
  }
  if (value === "0") return "off";
  return DEFAULT_FILTERS.landUseFilter;
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const filters: FilterState = {
    ...DEFAULT_FILTERS,
    landUseFilter: landUseParam(url.searchParams.get("landUse") ?? url.searchParams.get("mf")),
    includePlannedDevelopment: url.searchParams.get("pd") !== "0",
    includeConditionalZoning: url.searchParams.get("cond") === "1",
    minAcreage: Number(url.searchParams.get("minAcres") ?? DEFAULT_FILTERS.minAcreage),
    includeUnknownAcreage: url.searchParams.get("unkAcres") !== "0",
    minIncome: Number(url.searchParams.get("minIncome") ?? DEFAULT_FILTERS.minIncome),
    incomeGeography: (url.searchParams.get("geo") as IncomeGeography) || DEFAULT_FILTERS.incomeGeography,
    includeUnknownIncome: url.searchParams.get("unkIncome") !== "0",
    minAadt: Number(url.searchParams.get("minAadt") ?? DEFAULT_FILTERS.minAadt),
    includeUnknownAadt: url.searchParams.get("unkAadt") !== "0",
  };

  try {
    const [collection, zoningConfig, fluConfig] = await Promise.all([
      getParcelProvider().listParcels(),
      loadZoningConfig(),
      loadFluConfig(),
    ]);
    const features = filterParcels(collection.features, filters, zoningConfig, fluConfig);
    return NextResponse.json({
      type: "FeatureCollection",
      features,
      meta: { total: collection.features.length, matched: features.length, filters },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to load parcels" },
      { status: 500 },
    );
  }
}
