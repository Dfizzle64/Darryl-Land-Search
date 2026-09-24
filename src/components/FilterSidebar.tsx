"use client";

import { MfPriorityFilter } from "./MfPriorityFilter";
import { SouthCarolinaStatusNote } from "./SouthCarolinaStatusNote";
import { ZoningKnowledgePanel } from "./ZoningKnowledgePanel";
import { UTILITY_LAYER_NOTE, type ScreeningToggles } from "@/lib/screening";
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
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Eligible sheds</h2>
          <p className="text-sm text-white">
            {market}: {tractCount.toLocaleString()} eligible {tractCount === 1 ? "tract" : "tracts"}
          </p>
          <p className="text-xs text-ink-300">
            {ruralTractCount.toLocaleString()} rural · {urbanTractCount.toLocaleString()} urban. Violet is rural. Blue
            is urban, including Orlando. Status is eligible — not designated.
          </p>
          <p className="text-xs leading-relaxed text-ink-500">{SHED_CAVEAT}</p>
          {statusHelp ? (
            <SouthCarolinaStatusNote note={statusHelp} className="text-xs leading-relaxed text-ink-300" />
          ) : null}
          <p className="text-xs leading-relaxed text-ink-500">{parcelNote}</p>
          {orlandoParcels && !orangePilot ? (
            <p className="text-xs leading-relaxed text-ink-300">
              Zoning and FLU knowledge is Orange County–first. Outside Orange, prefer All parcels — missing zoning is
              treated honestly, not guessed.
            </p>
          ) : null}
          {parcelCoverageNote ? (
            <p className="text-xs leading-relaxed text-ink-300">{parcelCoverageNote}</p>
          ) : null}
          {orlandoParcels && !orangePilot ? (
            <p className="text-xs leading-relaxed text-ink-300">
              Parcel outlines stay off until neighborhood zoom, an area is locked, or Show parcels is on. Only this
              market&apos;s tiles load.
            </p>
          ) : null}
          {!orlandoParcels ? (
            <p className="text-xs leading-relaxed text-ink-300">
              {parcelCoverageNote
                ? "No parcel polygons were stored for this market. The map stays on eligible tracts."
                : "Parcel polygons for this market are not seeded yet. Switch to Orlando to browse the nine-county shed extract."}
            </p>
          ) : null}
          {onPriorityView && priorityView && priorityCounts ? (
            <div className="border-t border-white/10 pt-2">
              <MfPriorityFilter value={priorityView} counts={priorityCounts} onChange={onPriorityView} />
            </div>
          ) : null}
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Opportunity Zones</h2>
          <YesNo
            label="Consider opportunity zone in parcels"
            hint="No leaves parcel results unfiltered by Opportunity Zone. Yes shows the parcel OZ choices below."
            value={filters.considerOpportunityZone}
            onChange={(considerOpportunityZone) => onChange({ ...filters, considerOpportunityZone })}
          />
          {filters.considerOpportunityZone ? (
            <fieldset className="space-y-2">
              <legend className="sr-only">Opportunity Zone filter</legend>
              {OZ_OPTIONS.map((option) => (
                <label key={option.value} className="flex cursor-pointer items-start gap-2 rounded-xl border border-white/5 bg-ink-950/30 px-2 py-2">
                  <input
                    type="radio"
                    className="mt-1 accent-moss-400"
                    name="oz-filter"
                    checked={filters.ozFilter === option.value}
                    onChange={() => onChange({ ...filters, ozFilter: option.value })}
                  />
                  <span>
                    <span className="block text-sm text-white">{option.label}</span>
                    <span className="mt-0.5 block text-xs text-ink-500">{option.hint}</span>
                  </span>
                </label>
              ))}
            </fieldset>
          ) : null}
          <Toggle
            label="Show OZ 2.0 eligible tracts"
            checked={showOz2}
            onChange={onShowOz2}
            hint="Violet tracts are rural-eligible. Blue tracts are urban eligible in every market, including Orlando. None of these are designated."
          />
          <Toggle
            label="Show designated Opportunity Zone overlay"
            checked={showOz}
            onChange={onShowOz}
            hint="Orange County pilot only. Current HUD/Treasury QOZ tracts (2010 geography), copper fill with a dashed outline. Eligible is not designated."
          />
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Site screening</h2>
          <p className="text-xs text-ink-500">
            Off by default. These are public map layers, not parcel filters, and they do not change which sites match.
          </p>
          <Toggle label="Flood zones" checked={screening.flood} onChange={(value) => onScreening("flood", value)} hint={UTILITY_LAYER_NOTE.flood} />
          <Toggle label="Wetlands" checked={screening.wetlands} onChange={(value) => onScreening("wetlands", value)} hint={UTILITY_LAYER_NOTE.wetlands} />
          <Toggle label="School ratings" checked={screening.schools} onChange={(value) => onScreening("schools", value)} hint={UTILITY_LAYER_NOTE.schools} />
          <Toggle label="Water service areas" checked={screening.water} onChange={(value) => onScreening("water", value)} hint={UTILITY_LAYER_NOTE.water} />
          <Toggle label="Sewer service areas" checked={screening.sewer} onChange={(value) => onScreening("sewer", value)} hint={UTILITY_LAYER_NOTE.sewer} />
          <Toggle label="Electric retail territories" checked={screening.power} onChange={(value) => onScreening("power", value)} hint={UTILITY_LAYER_NOTE.power} />
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Zoning</h2>
          <YesNo
            label="Consider zoning in parcels"
            hint="No ignores zoning, future land use, and rezoning rules. Yes shows those parcel choices below."
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
                    <span>
                      <span className="block text-sm text-white">{option.label}</span>
                      <span className="mt-0.5 block text-xs text-ink-500">{option.hint}</span>
                    </span>
                  </label>
                ))}
              </fieldset>
              <Toggle
                label="Include planned development"
                checked={filters.includePlannedDevelopment}
                onChange={(includePlannedDevelopment) => onChange({ ...filters, includePlannedDevelopment })}
                hint="PD / PUD / PURD is maybe — entitlements are site-specific"
              />
              <Toggle
                label="Include conditional zoning"
                checked={filters.includeConditionalZoning}
                onChange={(includeConditionalZoning) => onChange({ ...filters, includeConditionalZoning })}
                hint="Live Local commercial/industrial, limited multiplex, some mixed-use overlays"
              />
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
          <p className="text-xs text-ink-500">
            Slider runs 0–{ACREAGE_SLIDER.max} acres. Larger parcels still match any threshold at or below{" "}
            {ACREAGE_SLIDER.max} ac. Lake, Orange, Osceola, Polk, and Seminole fixtures include every public parcel from
            5.0 through 150.0 acres. Parcels under 5 or over 150 are excluded. Brevard, Marion, Sumter, and Volusia are
            still smaller samples. Eligible tracts have no acreage attribute, so this slider does not hide tracts.
          </p>
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
              onChange={(event) => onChange({ ...filters, minIncome: Number(event.target.value) })}
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
          <p className="text-xs text-ink-500">
            Florida parcels in the current view pick up ACS tract median income (B19013) where that county has a parcel
            extract. The minimum hides parcels whose known income is below it. While Include unknown income is checked,
            parcels and tracts with no joined median stay on the map — uncheck it to hide them. Block group income is
            joined for Orange County parcels only. Tract geography uses the same minimum on eligible-tract overlays.
          </p>
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Nearby traffic</h2>
          <label className="block text-sm">
            Minimum AADT on nearest FDOT segment
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
          <p className="text-xs text-ink-500">
            Florida parcels pick up the nearest FDOT count segment within 15 km, including counts under 15,000. A parcel
            farther away, or outside Florida, stays unknown. While Include unknown AADT is checked, those parcels stay
            visible — uncheck it to hide them. Eligible tracts have no AADT, so this slider does not hide tracts.
          </p>
          <Toggle
            label="Show major-road AADT overlay"
            checked={showTraffic}
            onChange={onShowTraffic}
            hint="FDOT segments with 15,000+ AADT"
          />
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Map</h2>
          <Toggle
            label="Show parcels that fail filters"
            checked={showExcluded}
            onChange={onShowExcluded}
            hint="Failed parcels render as faded outlines"
          />
        </section>

        <ZoningKnowledgePanel
          zoningConfig={zoningConfig}
          fluConfig={fluConfig}
          fluJoinedCount={fluJoinedCount}
          parcelCount={totalCount}
        />

        <p className="mt-6 text-[11px] leading-relaxed text-ink-500">
          Fixture snapshot {generatedAt ?? "unknown"}. Orlando shed parcels are partitioned public GIS extracts (DOH
          EHWATER / Orange County Property Appraiser). Zoning and FLU joins are richest for Orange County; other counties
          degrade when a field is missing. Opportunity Zones shown in copper with a dashed outline are current designated
          QOZs in the Orange pilot. Rural tracts are violet and urban eligible tracts are blue in every market,
          including Orlando. Both are Rev. Proc. 2026-14 nomination eligibility — Eligible — not designated. The
          seven-market rural chip still reads Eligible (rural) — not designated. {SHED_CAVEAT} Income
          and AADT joins are Orange-pilot first.
        </p>
      </aside>
    </>
  );
}
