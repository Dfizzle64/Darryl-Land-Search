/**
 * Parcel outlines at shed scale hide the tract overlays. Auto mode stays off
 * until the camera reaches neighborhood zoom, or until an area is locked.
 * Show parcels forces outlines on at any zoom. Hide parcels sticks until the
 * user turns them back on.
 */

/** Zoom where auto mode starts drawing parcels. Neighborhood scale, under the old 11.5 gate. */
export const PARCEL_AUTO_ZOOM = 10.5;

export const PARCEL_VISIBILITY_STORAGE_KEY = "dls.parcelVisibility";

export const PARCEL_ZOOM_HINT =
  "Zoom in to neighborhood level, lock an area, or turn Show parcels on.";

export type ParcelVisibilityPreference = "auto" | "manual-on" | "manual-off";

export function isParcelVisibilityPreference(value: string | null): value is ParcelVisibilityPreference {
  return value === "auto" || value === "manual-on" || value === "manual-off";
}

export function parcelsAreVisible(
  preference: ParcelVisibilityPreference,
  zoom: number,
  aoiLocked: boolean,
): boolean {
  if (preference === "manual-off") return false;
  if (preference === "manual-on") return true;
  return zoom >= PARCEL_AUTO_ZOOM || aoiLocked;
}

/**
 * Keep the viewport query once the camera is at the auto gate (Hide parcels
 * still feeds the ranked list) or whenever outlines are forced on, including
 * the full shed.
 */
export function shouldQueryParcelsForZoom(preference: ParcelVisibilityPreference, zoom: number): boolean {
  return parcelsAreVisible(preference, zoom, false) || zoom >= PARCEL_AUTO_ZOOM;
}

/**
 * The toggle is on/off from the user's point of view.
 * Turning parcels off sticks (manual-off) through zoom and AOI changes.
 * Turning them back on resumes auto when zoom or an AOI would already show them,
 * and forces them on when the user asks to see the shed.
 */
export function toggleParcelVisibility(
  preference: ParcelVisibilityPreference,
  zoom: number,
  aoiLocked: boolean,
): ParcelVisibilityPreference {
  if (parcelsAreVisible(preference, zoom, aoiLocked)) return "manual-off";
  if (zoom >= PARCEL_AUTO_ZOOM || aoiLocked) return "auto";
  return "manual-on";
}

export function parcelVisibilityHint(preference: ParcelVisibilityPreference, parcelsVisible = false): string {
  if (preference === "manual-off") {
    return "Off until you turn Show parcels back on. Zooming in or locking an area will not show them.";
  }
  if (preference === "manual-on") {
    return "On at every zoom, including the full shed. Turn Show parcels off to hide the outlines.";
  }
  if (!parcelsVisible) return PARCEL_ZOOM_HINT;
  return "On around neighborhood zoom. Zoom out and they hide again, unless you turn Show parcels on.";
}
