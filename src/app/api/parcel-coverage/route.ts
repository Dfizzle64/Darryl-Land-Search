import { NextResponse } from "next/server";
import { loadParcelCoverage } from "@/lib/data/parcelCoverageStore";

export async function GET() {
  const collection = await loadParcelCoverage();
  return NextResponse.json(collection);
}
