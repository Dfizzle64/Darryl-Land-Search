import { describe, expect, it } from "vitest";
import { loadOpportunityZones, loadOz2Tracts, loadRuralMarketTracts } from "../lib/data/loadFixtures";
import { formatTractCounty, tractClickFromFeature } from "../lib/tractCounty";
import { RURAL_ELIGIBLE_STATUS_CHIP } from "../lib/types";

describe("tract county on click", () => {
  it("labels county and state without doubling the word County", () => {
    expect(formatTractCounty("Orange", "Florida")).toBe("Orange County, Florida");
    expect(formatTractCounty("Orange County", "Florida")).toBe("Orange County, Florida");
    expect(formatTractCounty(null, null)).toBe("County unavailable");
  });

  it("describes an eligible non-rural tract without calling it designated", () => {
    const details = tractClickFromFeature({
      layerId: "oz2-fill",
      properties: {
        tractGeoid: "12095010400",
        county: "Orange",
        state: "Florida",
        rural: false,
      },
    });
    expect(details?.placeLabel).toBe("Orange County, Florida");
    expect(details?.geoid).toBe("12095010400");
    expect(details?.status).toBe("Eligible for nomination, not rural — not designated");
    expect(details?.ruralLabel).toBe("Rural: no");
    expect(details?.opensRuralDrawer).toBe(false);
    expect(details?.status.toLowerCase()).not.toContain("designated qoz");
  });

  it("opens the rural drawer for rural-eligible tracts and keeps the status chip", () => {
    const details = tractClickFromFeature({
      layerId: "rural-fill",
      properties: { tractGeoid: "12095016605", county: "Orange", state: "Florida", rural: true },
    });
    expect(details?.opensRuralDrawer).toBe(true);
    expect(details?.status).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(details?.ruralLabel).toBe("Rural: yes");
  });

  it("keeps designated tracts on the Notice 2025-50 rural flag", () => {
    const details = tractClickFromFeature({
      layerId: "oz-fill",
      properties: { tractGeoid: "12095017600", county: "Orange", state: "Florida", rural: false },
    });
    expect(details?.kind).toBe("designated");
    expect(details?.opensRuralDrawer).toBe(false);
    expect(details?.status).toMatch(/current designated QOZ/i);
    expect(details?.status).toMatch(/not a 2027 designation/i);
    expect(details?.ruralLabel).toBe("Notice 2025-50 rural: no");
  });

  it("stamps county and state onto Orange eligible, designated, and rural tract features", async () => {
    const [oz2, designated, rural] = await Promise.all([
      loadOz2Tracts(),
      loadOpportunityZones(),
      loadRuralMarketTracts(),
    ]);
    expect(oz2.features.length).toBeGreaterThan(80);
    expect(oz2.features.every((feature) => feature.properties.county === "Orange" && feature.properties.state === "Florida")).toBe(
      true,
    );
    const urban = oz2.features.find((feature) => feature.properties.tractGeoid === "12095010400");
    expect(urban?.properties.rural).toBe(false);
    expect(urban?.properties.county).toBe("Orange");
    expect(designated.features.every((feature) => feature.properties.county === "Orange" && feature.properties.state === "Florida")).toBe(
      true,
    );
    expect(rural.features.every((feature) => feature.properties.county && feature.properties.state)).toBe(true);
    const brevard = rural.features.find((feature) => feature.properties.tractGeoid === "12009060104");
    expect(brevard?.properties.county).toBe("Brevard");
    expect(brevard?.properties.state).toBe("Florida");
  });
});