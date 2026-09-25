import { describe, expect, it } from "vitest";
import { formatMapZoom, MAP_SCALE } from "../lib/mapScale";

describe("map scale", () => {
  it("uses an imperial scale in the bottom-right corner", () => {
    expect(MAP_SCALE.unit).toBe("imperial");
    expect(MAP_SCALE.position).toBe("bottom-right");
    expect(MAP_SCALE.maxWidth).toBeGreaterThan(40);
    expect(MAP_SCALE.maxWidth).toBeLessThan(160);
  });

  it("formats the live zoom readout to one decimal", () => {
    expect(formatMapZoom(10.44)).toBe("Zoom 10.4");
    expect(formatMapZoom(10)).toBe("Zoom 10.0");
    expect(formatMapZoom(Number.NaN)).toBe("Zoom");
  });
});
