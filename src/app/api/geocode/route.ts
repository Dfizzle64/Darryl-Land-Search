import { NextResponse } from "next/server";
import { geocodeAddress } from "@/lib/geocode";
import { coordinateError, parseLatLng } from "@/lib/jumpTo";

export const dynamic = "force-dynamic";

/** Headroom for one Census retry plus Esri and Nominatim. Each provider has its own timeout. */
export const maxDuration = 20;

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.get("q")?.trim() ?? "";
  const invalid = coordinateError(query);
  if (invalid) return NextResponse.json({ error: invalid }, { status: 400 });
  const local = parseLatLng(query);
  if (local) return NextResponse.json({ ...local, kind: "coordinates" });
  if (query.length < 5) {
    return NextResponse.json({ error: "Enter a street address or lat, long." }, { status: 400 });
  }
  const result = await geocodeAddress(query);
  const headers = { "Cache-Control": "no-store" };
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status, headers });
  return NextResponse.json(
    { lng: result.lng, lat: result.lat, kind: "address", provider: result.provider },
    { headers },
  );
}
