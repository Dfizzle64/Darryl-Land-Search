/**
 * Parcel outlines turn on at zoom 10. From there the map draws every 5–150 acre
 * parcel in view with its real boundary. Tiles already loaded stay cached.
 * Hide parcels sticks until the user turns them back on.
 */

/** Zoom where parcel polygons may draw. */
export const PARCEL_MIN_ZOOM = 10;

/**
 * Same 0.25° grid as the parcel extracts (origin -83, 27). One cell is one
 * cached chunk. The key does not include zoom.
 */
export const PARCEL_TILE_DEGREES = 0.25;
export const PARCEL_TILE_ORIGIN_LON = -83;
export const PARCEL_TILE_ORIGIN_LAT = 27;

/** @deprecated Use PARCEL_MIN_ZOOM. Kept so existing imports keep compiling. */
export const PARCEL_AUTO_ZOOM = PARCEL_MIN_ZOOM;

export const PARCEL_VISIBILITY_STORAGE_KEY = "dls.parcelVisibility";

export const PARCEL_ZOOM_HINT = "Zoom in to see parcels. Outlines start at zoom 10.";

export type ParcelTileCache<T> = {
  signature: string;
  tiles: Map<string, T>;
};

export function createParcelTileCache<T>(): ParcelTileCache<T> {
  return { signature: "", tiles: new Map() };
}

/** Drop cached tiles when the market or county changes. The same signature keeps them. */
export function syncParcelTileCache<T>(cache: ParcelTileCache<T>, signature: string): void {
  if (cache.signature === signature) return;
  cache.signature = signature;
  cache.tiles.clear();
}

export function parcelTileKey(ix: number, iy: number): string {
  return `${ix}:${iy}`;
}

export function parcelTileKeysForBbox(bbox: [number, number, number, number]): string[] {
  const [west, south, east, north] = bbox;
  const ix0 = Math.floor((west - PARCEL_TILE_ORIGIN_LON) / PARCEL_TILE_DEGREES);
  const ix1 = Math.floor((Math.max(west, east - 1e-9) - PARCEL_TILE_ORIGIN_LON) / PARCEL_TILE_DEGREES);
  const iy0 = Math.floor((south - PARCEL_TILE_ORIGIN_LAT) / PARCEL_TILE_DEGREES);
  const iy1 = Math.floor((Math.max(south, north - 1e-9) - PARCEL_TILE_ORIGIN_LAT) / PARCEL_TILE_DEGREES);
  const keys: string[] = [];
  for (let ix = ix0; ix <= ix1; ix += 1) {
    for (let iy = iy0; iy <= iy1; iy += 1) {
      keys.push(parcelTileKey(ix, iy));
    }
  }
  return keys;
}

export function parcelTileBbox(key: string): [number, number, number, number] {
  const [ix, iy] = key.split(":").map((part) => Number(part));
  const west = PARCEL_TILE_ORIGIN_LON + ix * PARCEL_TILE_DEGREES;
  const south = PARCEL_TILE_ORIGIN_LAT + iy * PARCEL_TILE_DEGREES;
  return [west, south, west + PARCEL_TILE_DEGREES, south + PARCEL_TILE_DEGREES];
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
      : "Zoom in to see parcels. Outlines start at zoom 10. Show parcels stays on once you get there.";
  }
  if (!parcelsVisible) return PARCEL_ZOOM_HINT;
  return "On from zoom 10. Zoom out past zoom 10 and the outlines hide, unless you turn Show parcels on.";
}
