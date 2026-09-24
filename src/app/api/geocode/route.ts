import { NextResponse } from "next/server";
import { censusMatchPoint, parseLatLng } from "@/lib/jumpTo";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.get("q")?.trim() ?? "";
  const local = parseLatLng(query);
  if (local) return NextResponse.json({ ...local, kind: "coordinates" });
  if (query.length < 5) {
    return NextResponse.json({ error: "Enter a street address or lat, long." }, { status: 400 });
  }
  const url = new URL("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress");
  url.searchParams.set("address", query);
  url.searchParams.set("benchmark", "Public_AR_Current");
  url.searchParams.set("format", "json");
  try {
    const response = await fetch(url.toString(), { headers: { Accept: "application/json" } });
    if (!response.ok) {
      return NextResponse.json({ error: "Address lookup failed." }, { status: 502 });
    }
    const point = censusMatchPoint(await response.json());
    if (!point) return NextResponse.json({ error: "No match for that address." }, { status: 404 });
    return NextResponse.json({ ...point, kind: "address" });
  } catch {
    return NextResponse.json({ error: "Address lookup failed." }, { status: 502 });
  }
}
