import { describe, expect, it } from "vitest";
import { marketsCoveringBbox, queryParcelsInView } from "../lib/data/parcelViewQuery";

describe("parcels follow the view", () => {
  it("covers Nashville and Orlando from the extracts, and not a county with no pull", async () => {
    const nashville = await marketsCoveringBbox([-86.9, 36.1, -86.7, 36.2]);
    const orlando = await marketsCoveringBbox([-81.5, 28.4, -81.25, 28.65]);
    const kentucky = await marketsCoveringBbox([-84.5, 38.0, -84.25, 38.25]);
    expect(nashville).toContain("Nashville");
    expect(orlando).toContain("Orlando");
    expect(kentucky).toEqual([]);
  }, 60_000);

  it("returns Davidson parcels for a Nashville view without asking for the Orlando market", async () => {
    const page = await queryParcelsInView([-86.82, 36.14, -86.74, 36.2]);
    expect(page.covered).toBe(true);
    expect(page.markets).toContain("Nashville");
    expect(page.collection.features.length).toBeGreaterThan(0);
    expect(page.truncated).toBe(false);
    for (const feature of page.collection.features) {
      const acres = feature.properties.acreage ?? 0;
      expect(acres).toBeGreaterThanOrEqual(5);
      expect(acres).toBeLessThanOrEqual(150);
    }
  }, 60_000);
});