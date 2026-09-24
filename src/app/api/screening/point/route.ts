import { NextResponse } from "next/server";
import { screeningAtPoint } from "@/lib/screeningFetch";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const lng = Number(url.searchParams.get("lng"));
  const lat = Number(url.searchParams.get("lat"));
  if (!Number.isFinite(lng) || !Number.isFinite(lat) || lng < -180 || lng > 180 || lat < -90 || lat > 90) {
    return NextResponse.json({ error: "lng and lat are required." }, { status: 400 });
  }
  const point = await screeningAtPoint(lng, lat);
  return NextResponse.json(point);
}
