import { NextResponse } from "next/server";
import { loadFixtureMeta, loadZoningConfig } from "@/lib/data/loadFixtures";

export async function GET() {
  const [zoningConfig, meta] = await Promise.all([loadZoningConfig(), loadFixtureMeta()]);
  return NextResponse.json({ zoningConfig, meta, dataSource: process.env.DATA_SOURCE ?? "fixture" });
}
