import { NextResponse } from "next/server";
import { parseBbox, utilityPolygons } from "@/lib/screeningFetch";
import type { UtilityKind } from "@/lib/screening";

export const dynamic = "force-dynamic";

const KINDS = new Set<UtilityKind>(["water", "sewer", "power"]);

export async function GET(request: Request) {
  const url = new URL(request.url);
  const layer = url.searchParams.get("layer");
  const bbox = parseBbox(url.searchParams.get("bbox"));
  if (!layer || !KINDS.has(layer as UtilityKind)) {
    return NextResponse.json({ error: "layer must be water, sewer, or power." }, { status: 400 });
  }
  if (!bbox) return NextResponse.json({ error: "bbox=west,south,east,north is required." }, { status: 400 });
  return NextResponse.json(await utilityPolygons(layer as UtilityKind, bbox));
}
