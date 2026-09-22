"use client";

import { SouthCarolinaStatusNote } from "./SouthCarolinaStatusNote";
import { formatCountyLabel, isSouthCarolinaState } from "@/lib/markets";
import { RURAL_ELIGIBLE_STATUS_CHIP, SC_GOVERNOR_FILED_STATUS, SHED_CAVEAT, type RuralMarketTractRow } from "@/lib/types";

type TractDrawerProps = {
  tract: RuralMarketTractRow | null;
  statusHelp?: string | null;
  onClose: () => void;
};

export function TractDrawer({ tract, statusHelp = null, onClose }: TractDrawerProps) {
  if (!tract) {
    return (
      <aside className="hidden w-[24rem] shrink-0 border-l border-white/10 bg-ink-900/80 p-5 lg:block">
        <p className="font-display text-2xl text-white">Tract details</p>
        <p className="mt-2 text-sm leading-relaxed text-ink-300">
          Select a rural-eligible tract to see its GEOID, county, and notes. These tracts are eligible for nomination.
          They are not certified 2027 Qualified Opportunity Zones. A tract is not a shovel-ready site.
        </p>
        {statusHelp ? (
          <SouthCarolinaStatusNote note={statusHelp} className="mt-3 text-xs leading-relaxed text-ink-300" />
        ) : null}
      </aside>
    );
  }

  const orangePilotTract = tract.state === "Florida" && tract.county === "Orange";
  const southCarolina = isSouthCarolinaState(tract.state);

  return (
    <aside className="drawer-scroll absolute inset-x-0 bottom-0 z-20 max-h-[70vh] overflow-y-auto rounded-t-3xl border border-white/10 bg-ink-900 p-5 shadow-2xl lg:static lg:z-0 lg:max-h-none lg:w-[24rem] lg:shrink-0 lg:rounded-none lg:border-l lg:border-t-0 lg:shadow-none">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-clay-400">{tract.geoid}</p>
          <h2 className="mt-1 font-display text-2xl leading-tight text-white">{tract.placeOrCorridor}</h2>
          <p className="text-sm text-ink-300">
            {formatCountyLabel(tract.county, tract.state)} · {tract.market}
          </p>
        </div>
        <button type="button" onClick={onClose} className="rounded-full border border-white/15 px-3 py-1 text-sm">
          Close
        </button>
      </div>

      <p className="mt-4 inline-block rounded-full border border-[#f15a08]/70 bg-[#f15a08]/15 px-2 py-1 text-xs text-[#ffc7a3]">
        {RURAL_ELIGIBLE_STATUS_CHIP}
      </p>
      {southCarolina ? <p className="mt-2 text-xs leading-relaxed text-ink-100">{SC_GOVERNOR_FILED_STATUS}</p> : null}

      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">What this means</dt>
          <dd className="mt-1 text-ink-100">
            Rev. Proc. 2026-14 lists this 2020 census tract as a low-income community comprised entirely of a rural
            area. It is eligible for nomination.{" "}
            {southCarolina
              ? "South Carolina’s governor filed OZ 2.0 nominations on Sep 10, 2026, but the tract list is not public. This GEOID is not marked nominated or designated."
              : "It has not been nominated or certified as a 2027 QOZ."}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Notes</dt>
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

      <p className="mt-4 text-xs leading-relaxed text-ink-500">
        {SHED_CAVEAT} A rural-eligible GEOID is not a pad site. Sewer, zoning, wetlands, title, and assembly still
        control.
        {orangePilotTract
          ? " Orange County, Florida still has the parcel sample on the map when this county is selected."
          : " This county has no parcel extract in the app — the map shows the tract polygon and a pin."}
      </p>
    </aside>
  );
}
