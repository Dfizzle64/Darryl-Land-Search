/**
 * Parcel outlines cover the tract boundaries until the camera is close enough
 * to read individual parcels. Auto mode stays off until that zoom. Show parcels
 * still waits for the same zoom so a county view does not fill with polygons.
 * Hide parcels sticks until the user turns them back on.
 */

/** Zoom where parcel polygons may draw. Closer than the tract outline gate. */
export const PARCEL_MIN_ZOOM = 13;

/** @deprecated Use PARCEL_MIN_ZOOM. Kept so existing imports keep compiling. */
export const PARCEL_AUTO_ZOOM = PARCEL_MIN_ZOOM;

export const PARCEL_VISIBILITY_STORAGE_KEY = "dls.parcelVisibility";

export const PARCEL_ZOOM_HINT = "Zoom in to see parcels.";

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
      : "Zoom in to see parcels. Show parcels stays on once you get there.";
  }
  if (!parcelsVisible) return PARCEL_ZOOM_HINT;
  return "On at closer zoom. Zoom out and tract outlines take over, unless you turn Show parcels on.";
}
