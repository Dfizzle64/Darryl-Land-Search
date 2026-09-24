import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    config.module.rules.push({
      test: /\.csv$/,
      resourceQuery: /raw/,
      type: "asset/source",
    });
    return config;
  },
  // Tile paths are chosen from meta.json at runtime, so the file tracer cannot
  // see them. Keep the Orlando parcel fixtures inside the parcel API functions.
  outputFileTracingIncludes: {
    "/": ["./data/fixtures/orlando-parcels/meta.json"],
    "/api/parcels": [
      "./data/fixtures/orlando-parcels/**/*",
      "./data/fixtures/screening/cobb-batch40.json",
      "./data/fixtures/screening/dekalb-batch40.json",
    ],
    "/api/parcels/[id]": [
      "./data/fixtures/orlando-parcels/**/*",
      "./data/fixtures/screening/cobb-batch40.json",
      "./data/fixtures/screening/dekalb-batch40.json",
    ],
    "/api/screening/point": [
      "./data/fixtures/screening/school-ratings.json",
      "./data/fixtures/screening/cms-spg-2025-26.json",
      "./data/fixtures/screening/cobb-batch40.json",
      "./data/fixtures/screening/dekalb-batch40.json",
    ],
    "/api/screening/schools": ["./data/fixtures/screening/school-ratings.json", "./data/fixtures/screening/cms-spg-2025-26.json"],
  },
};

export default nextConfig;
