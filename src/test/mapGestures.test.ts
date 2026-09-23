import { describe, expect, it } from "vitest";
import { applyMapGestures, MAP_TRACKPAD_ZOOM_RATE, MAP_WHEEL_ZOOM_RATE, type MapGestureTarget } from "../lib/mapGestures";

function handler() {
  let enabled = true;
  return {
    enable() {
      enabled = true;
    },
    disable() {
      enabled = false;
    },
    isEnabled() {
      return enabled;
    },
  };
}

function fakeMap() {
  const scroll = handler();
  let wheelRate: number | null = null;
  let trackpadRate: number | null = null;
  const map: MapGestureTarget = {
    dragPan: handler(),
    boxZoom: handler(),
    doubleClickZoom: handler(),
    touchZoomRotate: handler(),
    keyboard: handler(),
    scrollZoom: {
      ...scroll,
      enable: scroll.enable,
      disable: scroll.disable,
      setWheelZoomRate(rate: number) {
        wheelRate = rate;
      },
      setZoomRate(rate: number) {
        trackpadRate = rate;
      },
    },
  };
  return {
    map,
    enabled: (key: keyof MapGestureTarget) =>
      "isEnabled" in map[key] ? (map[key] as ReturnType<typeof handler>).isEnabled() : scroll.isEnabled(),
    scrollEnabled: () => scroll.isEnabled(),
    wheelRate: () => wheelRate,
    trackpadRate: () => trackpadRate,
  };
}

describe("map gestures", () => {
  it("keeps scroll, pinch, and double-click zoom on while drawing an area", () => {
    const fake = fakeMap();
    applyMapGestures(fake.map, true);
    expect(fake.scrollEnabled()).toBe(true);
    expect(fake.enabled("touchZoomRotate")).toBe(true);
    expect(fake.enabled("doubleClickZoom")).toBe(true);
    expect(fake.enabled("keyboard")).toBe(true);
    expect(fake.enabled("dragPan")).toBe(false);
    expect(fake.enabled("boxZoom")).toBe(false);
    expect(fake.wheelRate()).toBe(MAP_WHEEL_ZOOM_RATE);
    expect(fake.trackpadRate()).toBe(MAP_TRACKPAD_ZOOM_RATE);
  });

  it("keeps scroll zoom on while measuring and turns double-click zoom back on after", () => {
    const fake = fakeMap();
    applyMapGestures(fake.map, false, true);
    expect(fake.scrollEnabled()).toBe(true);
    expect(fake.enabled("dragPan")).toBe(true);
    expect(fake.enabled("touchZoomRotate")).toBe(true);
    expect(fake.enabled("doubleClickZoom")).toBe(false);
    applyMapGestures(fake.map, false, false);
    expect(fake.enabled("doubleClickZoom")).toBe(true);
    expect(fake.enabled("dragPan")).toBe(true);
  });

  it("restores pan after the draw tool closes", () => {
    const fake = fakeMap();
    applyMapGestures(fake.map, true);
    applyMapGestures(fake.map, false);
    expect(fake.enabled("dragPan")).toBe(true);
    expect(fake.enabled("boxZoom")).toBe(true);
    expect(fake.scrollEnabled()).toBe(true);
    expect(fake.enabled("touchZoomRotate")).toBe(true);
  });
});
