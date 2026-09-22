import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Tile paths are chosen from meta.json at runtime, so the file tracer cannot
  // see them. Keep the Orlando parcel fixtures inside the parcel API functions.
  outputFileTracingIncludes: {
    "/": ["./data/fixtures/orlando-parcels/meta.json"],
    "/api/parcels": ["./data/fixtures/orlando-parcels/**/*"],
    "/api/parcels/[id]": ["./data/fixtures/orlando-parcels/**/*"],
  },
};

export default nextConfig;
