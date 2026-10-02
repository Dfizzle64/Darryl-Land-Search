/** Finger travel that counts as a drag instead of a tap, in CSS pixels. */
export const SHEET_DRAG_THRESHOLD_PX = 24;

/**
 * A bottom sheet starts at a peek. Dragging up expands it, dragging down
 * collapses it, and a tap toggles. `deltaY` is start Y minus end Y, so a
 * positive value means the finger moved up.
 */
export function sheetExpandedAfterGesture(expanded: boolean, deltaY: number): boolean {
  if (deltaY > SHEET_DRAG_THRESHOLD_PX) return true;
  if (deltaY < -SHEET_DRAG_THRESHOLD_PX) return false;
  return !expanded;
}
