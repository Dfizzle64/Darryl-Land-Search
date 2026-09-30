import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    // Parcel-tile scans already take tens of seconds. GitHub-hosted runners
    // hit the 5s default on heartlandParcels while other files were in flight.
    testTimeout: 60_000,
    hookTimeout: 60_000,
  },
});
