import { describe, expect, it } from "vitest";
import { MAP_SCALE } from "../lib/mapScale";

describe("map scale", () => {
  it("uses an imperial scale in the bottom-right corner", () => {
    expect(MAP_SCALE.unit).toBe("imperial");
    expect(MAP_SCALE.position).toBe("bottom-right");
    expect(MAP_SCALE.maxWidth).toBeGreaterThan(40);
    expect(MAP_SCALE.maxWidth).toBeLessThan(160);
  });
});
