"use client";

import { ScreeningDetails } from "./ScreeningDetails";
import { SouthCarolinaStatusNote } from "./SouthCarolinaStatusNote";
import type { ScreeningPoint } from "@/lib/screening";
import { displayStatusChip, formatCountyLabel, showsGovernorFiledSoftCopy } from "@/lib/markets";
import { formatTractCounty } from "@/lib/tractCounty";
import { isFull5AcCounty, ORLANDO_FIPS_BY_NAME } from "@/lib/orlandoParcels";
import { MF_PRIORITY_DISCLAIMER, NOM_WATCH_CAVEAT, tractPlaceLabel } from "@/lib/scMfPriority";
import { SC_GOVERNOR_FILED_STATUS, SHED_CAVEAT, type EligibleTractRow } from "@/lib/types";

type TractDrawerProps = {
  tract: EligibleTractRow | null;
  statusHelp?: string | null;
  screeningPoint?: ScreeningPoint | null;
  screeningStatus?: "idle" | "loading" | "error";
  onClose: () => void;
  /** `pane` fills the desktop details rail. `page` is the standalone column / mobile sheet. */
  layout?: "page" | "pane";
};

export function TractDrawer({
  tract,
  statusHelp = null,
  screeningPoint = null,
  screeningStatus = "idle",
  onClose,
  layout = "page",
}: TractDrawerProps) {
  const pane = layout === "pane";
  if (!tract) {
    return (
      <aside className={pane ? "h-full overflow-y-auto bg-ink-900/80 p-5" : "hidden"}>
        <p className="font-display text-2xl text-white">Tract details</p>
        <p className="mt-2 text-sm leading-relaxed text-ink-300">
          Select an eligible tract to see its county, state, GEOID, rural flag, status, and place or corridor notes.
          These tracts are eligible for nomination. They are not certified 2027 Qualified Opportunity Zones.
        </p>
        {statusHelp ? (
          <SouthCarolinaStatusNote note={statusHelp} className="mt-3 text-xs leading-relaxed text-ink-300" />
        ) : null}
      </aside>
    );
  }

  const southCarolina = showsGovernorFiledSoftCopy(tract);
  const priority = tract.mfPriority ?? null;
  const place = tractPlaceLabel(tract);
  const rural = tract.rural === "Y";
  const statusChip = displayStatusChip(tract);

  return (
    <aside className={pane ? "drawer-scroll h-full overflow-y-auto bg-ink-900 p-5" : "drawer-scroll absolute inset-x-0 bottom-0 z-20 max-h-[70vh] overflow-y-auto rounded-t-3xl border border-white/10 bg-ink-900 p-5 shadow-2xl"}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-clay-400">{tract.geoid}</p>
          <h2 className="mt-1 font-display text-2xl leading-tight text-white">{place}</h2>
          <p className="text-sm text-ink-300">
            {formatCountyLabel(tract.county, tract.state)} · {tract.market}
          </p>
          {priority && priority.place !== tract.placeOrCorridor ? (
            <p className="mt-1 text-xs text-ink-500">Pack label: {tract.placeOrCorridor}</p>
          ) : null}
        </div>
        <button type="button" onClick={onClose} className="rounded-full border border-white/15 px-3 py-1 text-sm">
          Close
        </button>
      </div>

      <p
        className={`mt-4 inline-block rounded-full border px-2 py-1 text-xs ${
          rural
            ? "border-[#8b5a2b]/70 bg-[#8b5a2b]/15 text-[#f6e6d4]"
            : "border-[#3d7dff]/70 bg-[#3d7dff]/15 text-[#d6e4ff]"
        }`}
      >
        {statusChip}
      </p>
      {southCarolina ? <p className="mt-2 text-xs leading-relaxed text-ink-100">{SC_GOVERNOR_FILED_STATUS}</p> : null}
      {priority ? (
        <p
          className={`mt-2 inline-block rounded-full border px-2 py-1 text-xs ${
            priority.tier === "A"
              ? "border-[#ffe08a]/80 bg-[#ffe08a]/15 text-[#ffe08a]"
              : "border-[#7ec8ff]/80 bg-[#7ec8ff]/15 text-[#d7eeff]"
          }`}
        >
          Tier {priority.tier} · SC MF priority
        </p>
      ) : null}

      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">County</dt>
          <dd className="mt-1 text-ink-100">{formatTractCounty(tract.county, tract.state)}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">State</dt>
          <dd className="mt-1 text-ink-100">{tract.state || "Unavailable"}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">GEOID</dt>
          <dd className="mt-1 text-ink-100">{tract.geoid}</dd>
        </div>
        {priority ? (
          <>
            <div>
              <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Multifamily priority</dt>
              <dd className="mt-1 text-ink-100">
                {MF_PRIORITY_DISCLAIMER} {NOM_WATCH_CAVEAT}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Why it is on the shortlist</dt>
              <dd className="mt-1 text-ink-100">{priority.mfRationale}</dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Acreage realism</dt>
              <dd className="mt-1 text-ink-100">
                {priority.acreageRealism}. This is tract-wide Census land area, not a 5–40 acre pad.
              </dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">MF notes</dt>
              <dd className="mt-1 text-ink-100">{priority.notes}</dd>
            </div>
          </>
        ) : null}
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">What this means</dt>
          <dd className="mt-1 text-ink-100">
            {rural
              ? "Rev. Proc. 2026-14 lists this 2020 census tract as a low-income community comprised entirely of a rural area."
              : "Rev. Proc. 2026-14 lists this 2020 census tract as a low-income community that is eligible and not entirely rural."}{" "}
            It is eligible for nomination.{" "}
            {southCarolina
              ? "South Carolina’s governor filed OZ 2.0 nominations on Sep 10, 2026, but the tract list is not public. This GEOID is not marked nominated or designated."
              : "It has not been nominated or certified as a 2027 QOZ."}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Rural</dt>
          <dd className="mt-1 text-ink-100">{rural ? "Y — entirely rural" : "N — urban / not entirely rural"}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Status</dt>
          <dd className="mt-1 text-ink-100">{statusChip}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Place / corridor</dt>
          <dd className="mt-1 text-ink-100">{tract.placeOrCorridor}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">
            {priority ? "Rural-pack notes" : "Notes"}
          </dt>
          <dd className="mt-1 text-ink-100">{tract.notes}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Internal point</dt>
          <dd className="mt-1 text-ink-100">
            {tract.lat.toFixed(5)}, {tract.lon.toFixed(5)} (Census Gazetteer)
          </dd>
        </div>
      </dl>

      {tract.outerEdge ? (
        <p className="mt-4 rounded-2xl border border-clay-400/40 bg-clay-500/10 p-3 text-sm text-ink-100">
          This county sits on the outer edge of the approximate 90-minute shed. Peak drive time can run longer than 90
          minutes.
        </p>
      ) : null}
      {tract.specialUse ? (
        <p className="mt-3 rounded-2xl border border-clay-400/40 bg-clay-500/10 p-3 text-sm text-ink-100">
          The GEOID uses a 98xx tract pattern that often marks airports or other special land use. Confirm the ground
          before treating it as a development tract.
        </p>
      ) : null}

      <ScreeningDetails point={screeningPoint} status={screeningStatus} />
      <p className="mt-4 text-xs leading-relaxed text-ink-500">
        {SHED_CAVEAT} An eligible GEOID is not a pad site. Sewer, zoning, wetlands, title, and assembly still control.
        {tract.state === "Florida" && isFull5AcCounty(tract.county)
          ? ` ${tract.county} County includes public parcels from 5.0 through 150.0 acres. Parcels under 5 or over 150 are excluded. Zoom in if the view says it is showing a spread of a larger set.`
          : tract.state === "Florida" && ORLANDO_FIPS_BY_NAME[tract.county]
            ? ` ${tract.county} County still uses a thinner public-GIS sample in this build, not every parcel of 5 acres and up.`
            : " This county has no parcel extract in the app — the map shows the tract polygon."}
      </p>
    </aside>
  );
}
