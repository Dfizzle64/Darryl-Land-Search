/**
 * Map navigation stays on for scroll, pinch, double-click, keyboard, and +/-.
 * Drawing an area only suspends drag-pan and shift-drag box zoom so the
 * rectangle gesture does not pan the map. Those come back when drawing ends.
 */

/** Mouse-wheel zoom rate. Default MapLibre is 1/450, which feels stuck on a notch. */
export const MAP_WHEEL_ZOOM_RATE = 1 / 200;

/** Trackpad and pinch-zoom rate. Default MapLibre is 1/100. */
export const MAP_TRACKPAD_ZOOM_RATE = 1 / 60;

type GestureHandler = {
  enable(): void;
  disable(): void;
};

type ScrollZoomHandler = GestureHandler & {
  setWheelZoomRate?(rate: number): void;
  setZoomRate?(rate: number): void;
};

export type MapGestureTarget = {
  dragPan: GestureHandler;
  scrollZoom: ScrollZoomHandler;
  boxZoom: GestureHandler;
  doubleClickZoom: GestureHandler;
  touchZoomRotate: GestureHandler;
  keyboard: GestureHandler;
};

export function applyMapGestures(map: MapGestureTarget, drawing: boolean, measuring = false) {
  map.scrollZoom.enable();
  map.scrollZoom.setWheelZoomRate?.(MAP_WHEEL_ZOOM_RATE);
  map.scrollZoom.setZoomRate?.(MAP_TRACKPAD_ZOOM_RATE);
  map.touchZoomRotate.enable();
  map.keyboard.enable();
  // Measure uses double-click as a map click, so that zoom stays off until the tool closes.
  if (measuring) map.doubleClickZoom.disable();
  else map.doubleClickZoom.enable();
  if (drawing) {
    map.dragPan.disable();
    map.boxZoom.disable();
    return;
  }
  map.dragPan.enable();
  map.boxZoom.enable();
}
