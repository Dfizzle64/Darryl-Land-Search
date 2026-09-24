import { NextResponse } from "next/server";
import { fetchCensusTractTile } from "@/lib/censusTiger";
import { tractsVisibleAtZoom, TRACT_TILE_DEGREES, type TractBbox } from "@/lib/censusTracts";
import { loadOrangeTractIncomeMap } from "@/lib/data/loadFixtures";
import { parseBbox } from "@/lib/screeningFetch";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const bbox = parseBbox(url.searchParams.get("bbox"));
  const zoom = Number(url.searchParams.get("zoom"));
  if (!bbox) return NextResponse.json({ error: "bbox=west,south,east,north is required." }, { status: 400 });
  if (!tractsVisibleAtZoom(zoom)) {
    return NextResponse.json({ type: "FeatureCollection", features: [] });
  }
  const [west, south, east, north] = bbox;
  if (east - west > TRACT_TILE_DEGREES + 0.05 || north - south > TRACT_TILE_DEGREES + 0.05) {
    return NextResponse.json({ error: "bbox is larger than one tract tile." }, { status: 400 });
  }
  try {
    const income = await loadOrangeTractIncomeMap();
    const features = await fetchCensusTractTile(bbox as TractBbox, zoom, income);
    return NextResponse.json({ type: "FeatureCollection", features });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Census tract request failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
