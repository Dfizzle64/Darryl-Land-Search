/** Imperial scale bar. Feet under a mile, miles after that. Bottom-right of the map. */
export const MAP_SCALE = {
  unit: "imperial" as const,
  position: "bottom-right" as const,
  maxWidth: 100,
};

/** Live zoom readout. One decimal, updated on the map element, not through React state. */
export function formatMapZoom(zoom: number): string {
  if (!Number.isFinite(zoom)) return "Zoom";
  return `Zoom ${zoom.toFixed(1)}`;
}
