import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  IDLE_JUMP_PIN,
  JUMP_PIN_COLOR,
  JUMP_PIN_FADE_MS,
  JUMP_PIN_HIT,
  JUMP_PIN_TTL_MS,
  formatJumpPinLabel,
  jumpPinFromQuery,
  reduceJumpPin,
  type JumpPin,
  type JumpPinState,
} from "../lib/jumpPin";

const address = jumpPinFromQuery("  123 Main St,   Miami, FL  ", { lng: -80.1918, lat: 25.7617 }, 1);
const coordinates = jumpPinFromQuery("26.1224, -80.1373", { lng: -80.1373, lat: 26.1224 }, 2);

function visible(pin: JumpPin, shownAt = 0): JumpPinState {
  return reduceJumpPin(reduceJumpPin(IDLE_JUMP_PIN, { type: "search", pin }), { type: "fly-end", now: shownAt });
}

describe("jump-to pin lifecycle", () => {
  it("keeps the pin pending until the fly-to ends, then shows the searched text", () => {
    expect(formatJumpPinLabel("  123 Main St,   Miami, FL  ")).toBe("123 Main St, Miami, FL");
    const pending = reduceJumpPin(IDLE_JUMP_PIN, { type: "search", pin: address });
    expect(pending).toEqual({ status: "pending", pin: address });
    expect(address.label).toBe("123 Main St, Miami, FL");
    expect(reduceJumpPin(pending, { type: "fly-end", now: 1_000 })).toEqual({
      status: "visible",
      pin: address,
      shownAt: 1_000,
    });
    expect(coordinates.label).toBe("26.1224, -80.1373");
  });

  it("replaces the current pin when a new search starts", () => {
    const showing = visible(address, 500);
    const replaced = reduceJumpPin(showing, { type: "search", pin: coordinates });
    expect(replaced).toEqual({ status: "pending", pin: coordinates });
    expect(replaced.status === "pending" && replaced.pin.key).toBe(2);
    const shown = reduceJumpPin(replaced, { type: "fly-end", now: 900 });
    expect(shown).toMatchObject({ status: "visible", pin: coordinates });
  });

  it("clears on dismiss and ignores a late fly-end", () => {
    const pending = reduceJumpPin(IDLE_JUMP_PIN, { type: "search", pin: address });
    expect(reduceJumpPin(pending, { type: "dismiss" })).toEqual(IDLE_JUMP_PIN);
    expect(reduceJumpPin(reduceJumpPin(pending, { type: "dismiss" }), { type: "fly-end", now: 50 })).toEqual(IDLE_JUMP_PIN);

    const showing = visible(address, 10);
    expect(reduceJumpPin(showing, { type: "dismiss" })).toEqual(IDLE_JUMP_PIN);
  });

  it("stays up for about 60 seconds, then fades out", () => {
    const shownAt = 5_000;
    const showing = visible(address, shownAt);
    expect(reduceJumpPin(showing, { type: "tick", now: shownAt + JUMP_PIN_TTL_MS - 1 })).toEqual(showing);

    const fading = reduceJumpPin(showing, { type: "tick", now: shownAt + JUMP_PIN_TTL_MS });
    expect(fading).toEqual({ status: "fading", pin: address, shownAt });

    const stillFading = reduceJumpPin(fading, { type: "tick", now: shownAt + JUMP_PIN_TTL_MS + JUMP_PIN_FADE_MS - 1 });
    expect(stillFading.status).toBe("fading");

    expect(reduceJumpPin(fading, { type: "tick", now: shownAt + JUMP_PIN_TTL_MS + JUMP_PIN_FADE_MS })).toEqual(
      IDLE_JUMP_PIN,
    );
    expect(JUMP_PIN_TTL_MS).toBe(60_000);
  });

  it("lets clicks pass through the label and keeps them on the pin and the x", () => {
    expect(JUMP_PIN_HIT.label).toBe("none");
    expect(JUMP_PIN_HIT.root).toBe("none");
    expect(JUMP_PIN_HIT.body).toBe("none");
    expect(JUMP_PIN_HIT.pin).toBe("auto");
    expect(JUMP_PIN_HIT.close).toBe("auto");
    expect(JUMP_PIN_COLOR).toBe("#0a5694");

    const lib = readFileSync(new URL("../lib/jumpPin.ts", import.meta.url), "utf8");
    expect(lib).toContain("JUMP_PIN_HIT.pin");
    expect(lib).toContain("JUMP_PIN_HIT.label");
    expect(lib).toContain("JUMP_PIN_HIT.close");
    expect(lib).toContain('aria-label", "Dismiss searched location"');

    const map = readFileSync(new URL("../components/SiteMap.tsx", import.meta.url), "utf8");
    expect(map).toContain("new maplibregl.Marker");
    expect(map).toContain('anchor: "bottom"');
    expect(map).toContain("paintJumpPinElement");
    expect(map).toContain("reduceJumpPin");
    expect(map).toContain('event.key !== "Escape"');
    expect(map).toContain("JUMP_PIN_TTL_MS");
    expect(map).toContain("JUMP_PIN_FADE_MS");
  });
});
