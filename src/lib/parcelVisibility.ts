/**
 * Parcel outlines turn on at zoom 8, the same zoom as detailed tract boundaries.
 * A zoom-8 screen can cover several counties, so that band draws a capped,
 * simplified sample. Full boundaries start at the detail zoom. Hide parcels
 * sticks until the user turns them back on.
 */

/** Zoom where parcel polygons may draw. */
export const PARCEL_MIN_ZOOM = 8;

/** Full parcel boundaries. Zooms 8–12 use simplified rings. */
export const PARCEL_DETAIL_ZOOM = 13;

/**
 * A zoom-8 view of one market can hold tens of thousands of 5–150 acre parcels.
 * The map draws at most this many in that view, spread across it.
 */
export const PARCEL_LOW_ZOOM_LIMIT = 1600;

/** Quantize a low-zoom view to this grid so a small pan reuses the cached sample. */
export const PARCEL_RANGE_DEGREES = 1;

/** @deprecated Use PARCEL_MIN_ZOOM. Kept so existing imports keep compiling. */
export const PARCEL_AUTO_ZOOM = PARCEL_MIN_ZOOM;

export const PARCEL_VISIBILITY_STORAGE_KEY = "dls.parcelVisibility";

export const PARCEL_ZOOM_HINT = "Zoom in to see parcels. Outlines start at zoom 8.";

export type ParcelGeometryBand = "low" | "detail";

export function parcelGeometryBand(zoom: number): ParcelGeometryBand {
  return zoom >= PARCEL_DETAIL_ZOOM ? "detail" : "low";
}

export type ParcelRangeCache<T> = {
  signature: string;
  ranges: Map<string, T>;
};

export function createParcelRangeCache<T>(): ParcelRangeCache<T> {
  return { signature: "", ranges: new Map() };
}

/** Drop cached views when the market or filters change. The same signature keeps them. */
export function syncParcelRangeCache<T>(cache: ParcelRangeCache<T>, signature: string): void {
  if (cache.signature === signature) return;
  cache.signature = signature;
  cache.ranges.clear();
}

/**
 * Stable cache key for a view. Low zoom snaps to 1°; detail snaps to 0.25°.
 * The key does not include the exact zoom, so zooming within a band does not refetch.
 */
export function parcelRangeKey(bbox: [number, number, number, number], zoom: number): string {
  const tile = parcelGeometryBand(zoom) === "low" ? PARCEL_RANGE_DEGREES : 0.25;
  const [west, south, east, north] = bbox;
  const snapDown = (value: number) => Math.floor(value / tile) * tile;
  const snapUp = (value: number) => Math.ceil(value / tile) * tile;
  const quant = [snapDown(west), snapDown(south), snapUp(east), snapUp(north)];
  return `${parcelGeometryBand(zoom)}|${quant.map((value) => value.toFixed(2)).join(",")}`;
}

export type ParcelVisibilityPreference = "auto" | "manual-on" | "manual-off";

export function isParcelVisibilityPreference(value: string | null): value is ParcelVisibilityPreference {
  return value === "auto" || value === "manual-on" || value === "manual-off";
}

export function parcelsAreVisible(
  preference: ParcelVisibilityPreference,
  zoom: number,
  aoiLocked: boolean,
): boolean {
  // A locked area still feeds the ranked list, but polygons wait for parcel zoom.
  void aoiLocked;
  if (zoom < PARCEL_MIN_ZOOM) return false;
  if (preference === "manual-off") return false;
  return true;
}

/**
 * The ranked list follows the same zoom gate as the polygons. Hide parcels
 * still queries once the camera is close enough. An area lock is loaded on
 * its own path and does not pull the whole shed at tract zoom.
 */
export function shouldQueryParcelsForZoom(preference: ParcelVisibilityPreference, zoom: number): boolean {
  void preference;
  return zoom >= PARCEL_MIN_ZOOM;
}

/**
 * The toggle is on/off from the user's point of view.
 * Turning parcels off sticks (manual-off) through zoom and AOI changes.
 * Turning them back on resumes auto when the camera is already at parcel zoom,
 * and remembers Show parcels when the user is still zoomed out.
 */
export function toggleParcelVisibility(
  preference: ParcelVisibilityPreference,
  zoom: number,
  aoiLocked: boolean,
): ParcelVisibilityPreference {
  if (parcelsAreVisible(preference, zoom, aoiLocked)) return "manual-off";
  if (zoom >= PARCEL_MIN_ZOOM || aoiLocked) return "auto";
  return "manual-on";
}

export function parcelVisibilityHint(preference: ParcelVisibilityPreference, parcelsVisible = false): string {
  if (preference === "manual-off") {
    return "Off until you turn Show parcels back on. Zooming in or locking an area will not show them.";
  }
  if (preference === "manual-on") {
    return parcelsVisible
      ? "On at this zoom. Turn Show parcels off to hide the outlines."
      : "Zoom in to see parcels. Outlines start at zoom 8. Show parcels stays on once you get there.";
  }
  if (!parcelsVisible) return PARCEL_ZOOM_HINT;
  return "On from zoom 8. Zoom out past zoom 8 and the outlines hide, unless you turn Show parcels on.";
}
