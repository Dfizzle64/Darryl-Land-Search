import { NextResponse } from "next/server";
import { parseBbox, schoolsInView } from "@/lib/screeningFetch";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const bbox = parseBbox(new URL(request.url).searchParams.get("bbox"));
  if (!bbox) return NextResponse.json({ error: "bbox=west,south,east,north is required." }, { status: 400 });
  return NextResponse.json(await schoolsInView(bbox));
}
