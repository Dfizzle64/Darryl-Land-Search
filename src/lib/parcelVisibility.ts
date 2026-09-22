/**
 * Parcel outlines at shed scale hide the tract overlays. The layer stays off
 * until the user is close enough to read parcels, or until an area is locked.
 * A manual off wins over both until the user turns parcels back on.
 */

/** Zoom where auto mode starts drawing parcels. Between the shed fit (~11) and a block view. */
export const PARCEL_AUTO_ZOOM = 11.5;

export const PARCEL_VISIBILITY_STORAGE_KEY = "dls.parcelVisibility";

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

export function parcelVisibilityHint(preference: ParcelVisibilityPreference): string {
  if (preference === "manual-off") {
    return "Off until you turn parcels back on. Zooming in or locking an area will not show them.";
  }
  if (preference === "manual-on") {
    return "On at every zoom, including the full shed. Turn them off to hide the outlines.";
  }
  return "Hidden below zoom 11.5. Turns on when you zoom in or lock an area. Off stays off until you turn parcels back on.";
}
