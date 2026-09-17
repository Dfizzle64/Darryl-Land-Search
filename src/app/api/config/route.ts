import { NextResponse } from "next/server";
import { loadFixtureMeta, loadFluConfig, loadZoningConfig } from "@/lib/data/loadFixtures";

export async function GET() {
  const [zoningConfig, fluConfig, meta] = await Promise.all([
    loadZoningConfig(),
    loadFluConfig(),
    loadFixtureMeta(),
  ]);
  return NextResponse.json({
    zoningConfig,
    fluConfig,
    meta,
    dataSource: process.env.DATA_SOURCE ?? "fixture",
  });
}
