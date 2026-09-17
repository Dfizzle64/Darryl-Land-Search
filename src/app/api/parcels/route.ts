import { NextResponse } from "next/server";
import { getParcelProvider } from "@/lib/data/adapters";
import { loadZoningConfig } from "@/lib/data/loadFixtures";
import { filterParcels } from "@/lib/filters";
import { DEFAULT_FILTERS, type FilterState, type IncomeGeography } from "@/lib/types";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const filters: FilterState = {
    ...DEFAULT_FILTERS,
    multifamilyZoningOnly: url.searchParams.get("mf") !== "0",
    includePlannedDevelopment: url.searchParams.get("pd") !== "0",
    minIncome: Number(url.searchParams.get("minIncome") ?? DEFAULT_FILTERS.minIncome),
    incomeGeography: (url.searchParams.get("geo") as IncomeGeography) || DEFAULT_FILTERS.incomeGeography,
    includeUnknownIncome: url.searchParams.get("unkIncome") !== "0",
    minAadt: Number(url.searchParams.get("minAadt") ?? DEFAULT_FILTERS.minAadt),
    includeUnknownAadt: url.searchParams.get("unkAadt") !== "0",
  };

  try {
    const [collection, zoningConfig] = await Promise.all([getParcelProvider().listParcels(), loadZoningConfig()]);
    const features = filterParcels(collection.features, filters, zoningConfig);
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
