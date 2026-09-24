"use client";

import type { ReactNode } from "react";
import { MfPriorityFilter } from "./MfPriorityFilter";
import { SouthCarolinaStatusNote } from "./SouthCarolinaStatusNote";
import { ZoningKnowledgePanel } from "./ZoningKnowledgePanel";
import { southCarolinaOverlayMode } from "@/lib/markets";
import { screeningLayerNotes } from "@/lib/screeningLayerHelp";
import type { ScreeningToggles } from "@/lib/screening";
import { ACREAGE_SLIDER, DEFAULT_FILTERS, SHED_CAVEAT, type FilterState, type FluConfig, type LandUseFilter, type MfPriorityView, type OzFilter, type SearchMarketId, type ZoningConfig } from "@/lib/types";

type FilterSidebarProps = {
  filters: FilterState;
  onChange: (next: FilterState) => void;
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  matchedCount: number;
  totalCount: number;
  fluJoinedCount: number | null;
  showExcluded: boolean;
  onShowExcluded: (value: boolean) => void;
  showTraffic: boolean;
  onShowTraffic: (value: boolean) => void;
  showOz: boolean;
  onShowOz: (value: boolean) => void;
  showOz2: boolean;
  onShowOz2: (value: boolean) => void;
  screening: ScreeningToggles;
  onScreening: (key: keyof ScreeningToggles, value: boolean) => void;
  open: boolean;
  onClose: () => void;
  meta: Record<string, unknown>;
  orangePilot: boolean;
  orlandoParcels: boolean;
  parcelCoverageNote?: string | null;
  market: SearchMarketId;
  county: string | null;
  countyState: string | null;
  marketStates: string[];
  tractCount: number;
  ruralTractCount: number;
  urbanTractCount: number;
  parcelNote: string;
  statusHelp?: string | null;
  priorityView?: MfPriorityView;
  priorityCounts?: { all: number; priority: number; A: number; B: number };
  onPriorityView?: (view: MfPriorityView) => void;
};

function YesNo({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div>
      <p className="text-sm text-white">{label}</p>
      {hint ? <p className="mt-0.5 text-xs leading-relaxed text-ink-300">{hint}</p> : null}
      <div className="mt-2 grid grid-cols-2 gap-1 rounded-xl border border-white/15 bg-ink-950 p-1" role="group" aria-label={label}>
        {(
          [
            [true, "Yes"],
            [false, "No"],
          ] as const
        ).map(([next, text]) => {
          const selected = value === next;
          return (
            <button
              key={text}
              type="button"
              aria-pressed={selected}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                selected ? "bg-white text-ink-950" : "text-ink-200 hover:bg-white/10"
              }`}
              onClick={() => onChange(next)}
            >
              {text}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Note({ label, children }: { label: string; children: ReactNode }) {
  return (
    <details className="text-xs text-ink-400">
      <summary className="cursor-pointer text-ink-300">{label}</summary>
      <div className="mt-1 space-y-1 leading-relaxed text-ink-500">{children}</div>
    </details>
  );
}

function Toggle({
  label,
  checked,
  onChange,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  hint?: string;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-3">
      <span>
        <span className="block text-sm text-white">{label}</span>
        {hint ? <span className="mt-0.5 block text-xs text-ink-500">{hint}</span> : null}
      </span>
      <input
        type="checkbox"
        className="mt-1 h-4 w-4 accent-moss-400"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  );
}

const LAND_USE_OPTIONS: { value: LandUseFilter; label: string; hint: string }[] = [
  {
    value: "zoning",
    label: "Multifamily-capable",
    hint: "Current zoning is by-right multifamily in the knowledge base. PD and conditional are separate toggles.",
  },
  {
    value: "off",
    label: "All parcels",
    hint: "Ignore zoning and FLU; still apply acreage, income, traffic, and Opportunity Zone filters.",
  },
  {
    value: "non-mf",
    label: "Non-multifamily zoning",
    hint: "Currently NOT MF-capable. Use this as a zoning-only rezoning hunt — FLU is not required.",
  },
  {
    value: "rezoning",
    label: "Rezoning candidates",
    hint: "FLU supports multifamily / higher density, but current zoning is not MF-capable. Missing FLU is omitted, not guessed.",
  },
  {
    value: "flu",
    label: "FLU allows multifamily / higher density",
    hint: "Future Land Use supports MF even if current zoning does not. Orlando + unincorporated county are joined; other cities may be unknown.",
  },
  {
    value: "either",
    label: "Either zoning or FLU",
    hint: "Keep a parcel if current MF zoning or MF-supportive FLU matches.",
  },
  {
    value: "both",
    label: "Both zoning and FLU",
    hint: "Require current MF zoning and MF-supportive FLU.",
  },
];

const OZ_OPTIONS: { value: OzFilter; label: string; hint: string }[] = [
  { value: "either", label: "Either", hint: "Do not filter by designated Opportunity Zones or OZ 2.0 eligibility." },
  {
    value: "rural-eligible",
    label: "OZ 2.0 rural-eligible",
    hint: "Centroid is in a Rev. Proc. 2026-14 tract marked Rural. Eligible for nomination — not a designated 2027 QOZ.",
  },
  {
    value: "non-rural-eligible",
    label: "OZ 2.0 eligible, not rural",
    hint: "Centroid is in an eligible tract the revenue procedure marks Non-rural. Nomination only, not designated.",
  },
  {
    value: "in",
    label: "In designated Opportunity Zone",
    hint: "Centroid is inside a current HUD/Treasury QOZ (2018 designation, 2010 tracts).",
  },
  {
    value: "out",
    label: "Not in designated Opportunity Zone",
    hint: "Centroid is outside the county’s current designated QOZ tracts.",
  },
];

export function FilterSidebar({
  filters,
  onChange,
  zoningConfig,
  fluConfig,
  matchedCount,
  totalCount,
  fluJoinedCount,
  showExcluded,
  onShowExcluded,
  showTraffic,
  onShowTraffic,
  showOz,
  onShowOz,
  showOz2,
  onShowOz2,
  screening,
  onScreening,
  open,
  onClose,
  meta,
  orangePilot,
  orlandoParcels,
  parcelCoverageNote = null,
  market,
  county,
  countyState,
  marketStates,
  tractCount,
  ruralTractCount,
  urbanTractCount,
  parcelNote,
  statusHelp = null,
  priorityView,
  priorityCounts,
  onPriorityView,
}: FilterSidebarProps) {
  const generatedAt = typeof meta.generatedAt === "string" ? meta.generatedAt.slice(0, 10) : null;
  const layerNotes = screeningLayerNotes({ market, county, state: countyState, states: marketStates });
  const overlayMode = southCarolinaOverlayMode(market, countyState);
  const ozOptions = OZ_OPTIONS.map((option) => {
    if (overlayMode === "eligible") return option;
    if (option.value === "rural-eligible") {
      return {
        ...option,
        label: overlayMode === "nominated-only" ? "Nominated, rural" : option.label,
        hint:
          overlayMode === "nominated-only"
            ? "Centroid is in a South Carolina Governor-nominated tract marked Rural. Not a designated 2027 QOZ."
            : "In South Carolina, only Governor-nominated rural tracts match. Other states still use the Rev. Proc. 2026-14 rural-eligible list. Not a designated 2027 QOZ.",
      };
    }
    if (option.value === "non-rural-eligible") {
      return {
        ...option,
        label: overlayMode === "nominated-only" ? "Nominated, not rural" : option.label,
        hint:
          overlayMode === "nominated-only"
            ? "Centroid is in a South Carolina Governor-nominated tract marked Non-rural. Not a designated 2027 QOZ."
            : "In South Carolina, only Governor-nominated tracts match. Other states still use the Rev. Proc. 2026-14 non-rural eligible list. Not a designated 2027 QOZ.",
      };
    }
    return option;
  });
  const tractHeading = overlayMode === "nominated-only" ? "Nominated sheds" : overlayMode === "mixed" ? "Tract sheds" : "Eligible sheds";
  const tractCountLabel =
    overlayMode === "nominated-only" ? "nominated" : overlayMode === "mixed" ? "" : "eligible";
  const tractToggleLabel =
    overlayMode === "nominated-only" ? "Nominated tracts" : overlayMode === "mixed" ? "OZ tracts" : "Eligible tracts";

  return (
    <>
      {open ? <button type="button" className="fixed inset-0 z-20 bg-black/50 md:hidden" onClick={onClose} aria-label="Close filters" /> : null}
      <aside
        className={`sidebar-scroll fixed inset-y-0 left-0 z-30 w-[min(100%,22rem)] overflow-y-auto border-r border-white/10 bg-ink-900 px-4 py-4 transition-transform md:static md:z-0 md:block md:w-[22rem] md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="mb-4 flex items-center justify-between md:hidden">
          <h2 className="text-lg text-white">Filters</h2>
          <button type="button" className="text-sm text-ink-300" onClick={onClose}>
            Done
          </button>
        </div>

        <section className="rounded-2xl border border-white/10 bg-ink-800/70 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-ink-500">Results</p>
          <p className="mt-1 font-display text-3xl text-white">{matchedCount.toLocaleString()}</p>
          <p className="text-xs text-ink-500">
            matching {totalCount.toLocaleString()} {orlandoParcels ? "parcels in this view" : "sample parcels"}
          </p>
          <button
            type="button"
            className="mt-3 text-xs text-clay-400 underline-offset-2 hover:underline"
            onClick={() => onChange({ ...DEFAULT_FILTERS, landUseFilter: orlandoParcels ? "off" : DEFAULT_FILTERS.landUseFilter })}
          >
            Reset filters
          </button>
        </section>

        <section className="mt-5 space-y-2 rounded-2xl border border-white/10 bg-ink-800/70 p-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">{tractHeading}</h2>
          <p className="text-sm text-white">
            {market}: {tractCount.toLocaleString()} {`${tractCountLabel ? `${tractCountLabel} ` : ""}${tractCount === 1 ? "tract" : "tracts"}`}
          </p>
          <p className="text-xs text-ink-300">
            {ruralTractCount.toLocaleString()} rural · {urbanTractCount.toLocaleString()} urban
          </p>
          {statusHelp ? <SouthCarolinaStatusNote note={statusHelp} className="text-xs leading-relaxed text-ink-300" /> : null}
          {onPriorityView && priorityView && priorityCounts ? (
            <div className="border-t border-white/10 pt-2">
              <MfPriorityFilter compact value={priorityView} counts={priorityCounts} onChange={onPriorityView} />
            </div>
          ) : null}
          <Note label="Shed notes">
            <p>
              {overlayMode === "nominated-only"
                ? "South Carolina shows Governor-nominated tracts only. Rural and urban are attributes on that list. They are awaiting Treasury and are not a QOZ. Eligible tracts that were not nominated are not shown. No OZ 2.0 tax benefits apply today from this label."
                : overlayMode === "mixed"
                  ? "Rural eligible — not designated and urban eligible — not designated still describe tracts outside South Carolina. South Carolina tracts in this count are Governor-nominated only. Eligible tracts that were not nominated are not shown in South Carolina."
                  : "Rural eligible — not designated: Tract on Treasury OZ 2.0 eligible list, tagged entirely rural. Not yet a QOZ. No OZ 2.0 tax benefits apply today from this label. Urban eligible — not designated: Same eligible list, not tagged entirely rural. Also not yet a QOZ."}
            </p>
            <p>{SHED_CAVEAT}</p>
            <p>{parcelNote}</p>
            {parcelCoverageNote ? <p>{parcelCoverageNote}</p> : null}
            {orlandoParcels && !orangePilot ? (
              <p>Zoning and future land use are joined for Orange County. Missing zoning elsewhere is not guessed.</p>
            ) : null}
            {!orlandoParcels ? (
              <p>
                {parcelCoverageNote
                  ? overlayMode === "nominated-only"
                    ? "No parcel polygons were stored for this market. The map stays on nominated tracts."
                    : "No parcel polygons were stored for this market. The map stays on eligible tracts."
                  : "Parcel polygons for this market are not seeded yet."}
              </p>
            ) : null}
          </Note>
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Opportunity Zones</h2>
          <YesNo
            label="Opportunity Zone"
            value={filters.considerOpportunityZone}
            onChange={(considerOpportunityZone) => onChange({ ...filters, considerOpportunityZone })}
          />
          {filters.considerOpportunityZone ? (
            <fieldset className="space-y-2">
              <legend className="sr-only">Opportunity Zone filter</legend>
              {ozOptions.map((option) => (
                <label key={option.value} className="flex cursor-pointer items-start gap-2 rounded-xl border border-white/5 bg-ink-950/30 px-2 py-2">
                  <input
                    type="radio"
                    className="mt-1 accent-moss-400"
                    name="oz-filter"
                    checked={filters.ozFilter === option.value}
                    onChange={() => onChange({ ...filters, ozFilter: option.value })}
                  />
                  <span className="block text-sm text-white">{option.label}</span>
                </label>
              ))}
            </fieldset>
          ) : null}
          <Toggle label={tractToggleLabel} checked={showOz2} onChange={onShowOz2} />
          <Toggle label="Designated QOZ overlay" checked={showOz} onChange={onShowOz} />
          <Note label="What these mean">
            <p>
              {overlayMode === "nominated-only"
                ? "Parcel filter only. South Carolina tracts in this filter are the Governor-nominated list, not the broader federal eligible set, and not a designated 2027 QOZ."
                : overlayMode === "mixed"
                  ? "Parcel filter only. South Carolina matches are Governor-nominated tracts only. Other states use Rev. Proc. 2026-14 eligibility, not a designated 2027 QOZ."
                  : "Parcel filter only. Eligible tracts are Rev. Proc. 2026-14 nomination geography, not a designated 2027 QOZ."}
            </p>
            <p>{layerNotes.eligibleTracts}</p>
            <p>{layerNotes.designatedOz}</p>
          </Note>
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Map layers</h2>
          <Toggle label="Flood" checked={screening.flood} onChange={(value) => onScreening("flood", value)} />
          <Toggle label="Wetlands" checked={screening.wetlands} onChange={(value) => onScreening("wetlands", value)} />
          <Toggle label="Schools" checked={screening.schools} onChange={(value) => onScreening("schools", value)} />
          <Toggle label="Water" checked={screening.water} onChange={(value) => onScreening("water", value)} />
          <Toggle label="Sewer" checked={screening.sewer} onChange={(value) => onScreening("sewer", value)} />
          <Toggle label="Electric" checked={screening.power} onChange={(value) => onScreening("power", value)} />
          <Note label="Layer notes">
            <p>Off by default. These draw on the map and do not change which parcels match. No grade, BFE, or service connection is invented.</p>
            <p>{layerNotes.flood}</p>
            <p>{layerNotes.wetlands}</p>
            <p>{layerNotes.schools}</p>
            <p>{layerNotes.water}</p>
            <p>{layerNotes.sewer}</p>
            <p>{layerNotes.power}</p>
          </Note>
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Zoning</h2>
          <YesNo
            label="Zoning"
            value={filters.considerZoning}
            onChange={(considerZoning) => onChange({ ...filters, considerZoning })}
          />
          {filters.considerZoning ? (
            <>
              <fieldset className="space-y-2">
                <legend className="sr-only">Zoning and Future Land Use mode</legend>
                {LAND_USE_OPTIONS.map((option) => (
                  <label key={option.value} className="flex cursor-pointer items-start gap-2 rounded-xl border border-white/5 bg-ink-950/30 px-2 py-2">
                    <input
                      type="radio"
                      className="mt-1 accent-moss-400"
                      name="land-use-filter"
                      checked={filters.landUseFilter === option.value}
                      onChange={() => onChange({ ...filters, landUseFilter: option.value })}
                    />
                  <span className="block text-sm text-white">{option.label}</span>
                  </label>
                ))}
              </fieldset>
              <Toggle
                label="Include planned development"
                checked={filters.includePlannedDevelopment}
                onChange={(includePlannedDevelopment) => onChange({ ...filters, includePlannedDevelopment })}
              />
              <Toggle
                label="Include conditional zoning"
                checked={filters.includeConditionalZoning}
                onChange={(includeConditionalZoning) => onChange({ ...filters, includeConditionalZoning })}
              />
              <Note label="Zoning notes">
                {LAND_USE_OPTIONS.map((option) => (
                  <p key={option.value}>
                    {option.label}: {option.hint}
                  </p>
                ))}
                <p>Planned development is site-specific. Conditional zoning covers Live Local and similar overlays. Missing zoning is not guessed.</p>
              </Note>
            </>
          ) : null}
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Minimum acreage</h2>
          <label className="block text-sm">
            Parcel acreage
            <input
              type="range"
              min={ACREAGE_SLIDER.min}
              max={ACREAGE_SLIDER.max}
              step={ACREAGE_SLIDER.step}
              value={Math.min(filters.minAcreage, ACREAGE_SLIDER.max)}
              onChange={(event) => onChange({ ...filters, minAcreage: Number(event.target.value) })}
              className="mt-2 w-full accent-clay-400"
            />
            <span className="mt-1 block text-ink-300">
              {filters.minAcreage === 0
                ? "No minimum"
                : `${filters.minAcreage.toLocaleString("en-US", { maximumFractionDigits: 2 })} ac+`}
            </span>
          </label>
          <Note label="Acreage notes">
            <p>
              Slider runs 0–{ACREAGE_SLIDER.max} acres. Larger parcels still match any threshold at or below{" "}
              {ACREAGE_SLIDER.max} ac. Lake, Orange, Osceola, Polk, Seminole, and Sumter fixtures include every public parcel
              from 5.0 through 150.0 acres. Parcels under 5 or over 150 are excluded. Brevard, Marion, and Volusia are still
              smaller samples. Eligible tracts have no acreage attribute, so this slider does not hide tracts.
            </p>
          </Note>
          <Toggle
            label="Include unknown acreage"
            checked={filters.includeUnknownAcreage}
            onChange={(includeUnknownAcreage) => onChange({ ...filters, includeUnknownAcreage })}
          />
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Area income</h2>
          <label className="block text-sm">
            Census geography
            <select
              className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-2 text-sm"
              value={filters.incomeGeography}
              onChange={(event) =>
                onChange({ ...filters, incomeGeography: event.target.value as FilterState["incomeGeography"] })
              }
            >
              <option value="tract">Census tract</option>
              <option value="blockGroup">Block group</option>
            </select>
          </label>
          <label className="block text-sm">
            Minimum median household income
            <input
              type="range"
              min={0}
              max={200000}
              step={5000}
              value={filters.minIncome}
              onChange={(event) => {
                const minIncome = Number(event.target.value);
                const engaging = filters.minIncome <= 0 && minIncome > 0;
                const clearing = minIncome <= 0;
                onChange({
                  ...filters,
                  minIncome,
                  // Engaging the minimum excludes parcels with no joined median. Clearing it restores the idle default.
                  includeUnknownIncome: engaging ? false : clearing ? true : filters.includeUnknownIncome,
                });
              }}
              className="mt-2 w-full accent-clay-400"
            />
            <span className="mt-1 block text-ink-300">
              {filters.minIncome === 0 ? "No minimum" : `$${filters.minIncome.toLocaleString()}+`}
            </span>
          </label>
          <Toggle
            label="Include unknown income"
            checked={filters.includeUnknownIncome}
            onChange={(includeUnknownIncome) => onChange({ ...filters, includeUnknownIncome })}
          />
          <Note label="Income notes">
            <p>
              Census tract median household income is ACS 5-year 2020–2024 table B19013 (2024 dollars) for every live
              parcel market. A parcel with an 11-digit 2020 tract GEOID uses that id; otherwise the tract containing
              the centroid is used. Setting a minimum hides parcels below it and parcels with no joined median, unless
              Include unknown income is on. Block-group income is Orange County only. County, ZIP, and neighborhood
              substitutes are not the filter. Charlotte neighborhood income is not used. No income is invented.
            </p>
          </Note>
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Nearby traffic</h2>
          <label className="block text-sm">
            Minimum AADT on the nearest count segment
            <input
              type="range"
              min={0}
              max={100000}
              step={1000}
              value={filters.minAadt}
              onChange={(event) => onChange({ ...filters, minAadt: Number(event.target.value) })}
              className="mt-2 w-full accent-clay-400"
            />
            <span className="mt-1 block text-ink-300">
              {filters.minAadt === 0 ? "No minimum" : `${filters.minAadt.toLocaleString()}+ vehicles/day`}
            </span>
          </label>
          <Toggle
            label="Include unknown AADT"
            checked={filters.includeUnknownAadt}
            onChange={(includeUnknownAadt) => onChange({ ...filters, includeUnknownAadt })}
          />
          <Toggle label="Road counts" checked={showTraffic} onChange={onShowTraffic} />
          <Note label="Traffic notes">
            <p>
              Florida parcels use the nearest FDOT count within 15 km. Footprint counties in North Carolina, Georgia,
              South Carolina, Tennessee, Mississippi, Alabama, and Arkansas use that state’s published traffic counts,
              labeled Nearest AADT, where the state layer has a count. A county with no published segment stays unknown.
              The road overlay is still FDOT segments at 15,000 or more. Tracts have no AADT.
            </p>
          </Note>
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Map</h2>
          <Toggle label="Parcels that fail filters" checked={showExcluded} onChange={onShowExcluded} />
        </section>

        <Note label="Zoning reference">
          <ZoningKnowledgePanel
            zoningConfig={zoningConfig}
            fluConfig={fluConfig}
            fluJoinedCount={fluJoinedCount}
            parcelCount={totalCount}
          />
        </Note>
        <Note label="About this data">
          <p>
            Snapshot {generatedAt ?? "unknown"}. Public parcel rows only. Designated QOZ copper outlines are the current
            HUD layer, not a 2027 designation. Income and traffic joins stay unknown where the public source has no row.
          </p>
        </Note>
      </aside>
    </>
  );
}
