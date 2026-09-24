"use client";

import type { SchoolRating, ScreeningPoint } from "@/lib/screening";

type ScreeningDetailsProps = {
  point: ScreeningPoint | null;
  status: "idle" | "loading" | "error";
};

function Block({ title, summary, source, sourceUrl }: { title: string; summary: string; source: string; sourceUrl: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-ink-800/80 p-3 text-sm">
      <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">{title}</p>
      <p className="mt-1 text-ink-100">{summary}</p>
      <a className="mt-1 block text-xs text-moss-400 underline-offset-2 hover:underline" href={sourceUrl} target="_blank" rel="noreferrer">
        {source}
      </a>
    </div>
  );
}

function SchoolRow({ school }: { school: SchoolRating }) {
  return (
    <li className="border-t border-white/10 pt-2 first:border-t-0 first:pt-0">
      <p className="text-white">
        {school.zoned ? <span className="mr-2 text-clay-400">Zoned</span> : null}
        {school.rating ? <span className="mr-2 font-semibold">{school.rating}</span> : <span className="mr-2 text-ink-500">No grade</span>}
        {school.name}
      </p>
      <p className="text-xs text-ink-300">
        {[school.level, school.city, school.state, school.distanceMiles != null ? `${school.distanceMiles.toFixed(1)} mi` : null]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <p className="text-xs text-ink-300">{school.summary}</p>
      {school.reportCardUrl ? (
        <a className="text-xs text-moss-400 underline-offset-2 hover:underline" href={school.reportCardUrl} target="_blank" rel="noreferrer">
          Official report card
        </a>
      ) : null}
    </li>
  );
}

export function ScreeningDetails({ point, status }: ScreeningDetailsProps) {
  return (
    <section className="mt-5 space-y-3">
      <h3 className="text-[11px] uppercase tracking-[0.16em] text-ink-500">Site screening</h3>
      {status === "loading" && !point ? (
        <p className="text-sm text-ink-300">Looking up flood, wetlands, utilities, and nearby public school ratings…</p>
      ) : null}
      {status === "error" && !point ? (
        <p className="text-sm text-ink-300">Screening services did not respond. That is unknown, not a clear site.</p>
      ) : null}
      {point ? (
        <>
          <Block title="Flood zone" summary={point.flood.summary} source={point.flood.source} sourceUrl={point.flood.sourceUrl} />
          {point.tract ? (
            <Block title="Census tract" summary={point.tract.summary} source={point.tract.source} sourceUrl={point.tract.sourceUrl} />
          ) : null}
          <Block title="Wetlands" summary={point.wetland.summary} source={point.wetland.source} sourceUrl={point.wetland.sourceUrl} />
          {point.utilities.map((utility) => (
            <Block
              key={utility.kind}
              title={
                utility.kind === "power" ? "Electric" : utility.kind === "gas" ? "Gas" : utility.kind === "water" ? "Water" : "Sewer"
              }
              summary={utility.summary}
              source={utility.source}
              sourceUrl={utility.sourceUrl}
            />
          ))}
          <div className="rounded-2xl border border-white/10 bg-ink-800/80 p-3 text-sm">
            <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Schools</p>
            {point.schools.length ? (
              <ul className="mt-2 space-y-2">
                {point.schools.map((school) => (
                  <SchoolRow key={school.id} school={school} />
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-ink-100">No public school in this extract within 3 miles.</p>
            )}
            <p className="mt-2 text-xs text-ink-500">{point.schoolsNote}</p>
          </div>
        </>
      ) : null}
    </section>
  );
}
