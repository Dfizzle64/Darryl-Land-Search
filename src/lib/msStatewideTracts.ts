import type { EligiblePackTractCollection, EligibleTractRow } from "./types";

/** Statewide appendix tracts are not a 90-minute market. */
export const MS_STATEWIDE_MARKET = "Mississippi" as const;

export type MsStatewideTractRow = Omit<EligibleTractRow, "market"> & {
  market: typeof MS_STATEWIDE_MARKET;
};

export type TractInfoRow = EligibleTractRow | MsStatewideTractRow;

type GeoidFeature = { properties: { tractGeoid?: string } };

/**
 * Append Mississippi statewide tracts that are not already in a market pack.
 * Existing pack geometry wins, so other states and the tracts already drawn
 * near Memphis stay as they are.
 */
export function mergeMsStatewideTracts(
  eligible: EligiblePackTractCollection,
  rural: { features: GeoidFeature[] },
  oz2: { features: GeoidFeature[] },
  statewide: EligiblePackTractCollection,
): EligiblePackTractCollection {
  const seen = new Set<string>();
  for (const feature of [...rural.features, ...eligible.features, ...oz2.features]) {
    const geoid = feature.properties.tractGeoid;
    if (geoid) seen.add(geoid);
  }
  const extra = statewide.features.filter((feature) => {
    const geoid = feature.properties.tractGeoid;
    return Boolean(geoid) && !seen.has(geoid);
  });
  if (extra.length === 0) return eligible;
  return { ...eligible, features: [...eligible.features, ...extra] };
}

/** One drawer row per statewide feature. Eligibility still comes from the fixture, not from here. */
export function msStatewideTractRows(collection: EligiblePackTractCollection): MsStatewideTractRow[] {
  const rows: MsStatewideTractRow[] = [];
  for (const feature of collection.features) {
    const props = feature.properties;
    if (!props.tractGeoid || (props.rural !== true && props.rural !== false)) continue;
    if (!props.county || !props.state || !Number.isFinite(props.lat) || !Number.isFinite(props.lon)) continue;
    rows.push({
      market: MS_STATEWIDE_MARKET,
      state: props.state,
      county: props.county,
      geoid: props.tractGeoid,
      placeOrCorridor: props.placeOrCorridor || props.name || props.tractGeoid,
      rural: props.rural ? "Y" : "N",
      status: props.statusChip,
      lat: props.lat,
      lon: props.lon,
      notes: props.notes,
      outerEdge: props.outerEdge === true,
      specialUse: props.specialUse === true,
    });
  }
  return rows;
}
