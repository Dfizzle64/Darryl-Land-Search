export default function Loading() {
  return (
    <div className="flex h-dvh items-center justify-center bg-ink-950 text-ink-100">
      <div className="rounded-2xl border border-white/10 bg-ink-900 px-6 py-5">
        <p className="font-display text-2xl text-white">Loading Orange County parcels</p>
        <p className="mt-2 text-sm text-ink-300">Reading the bundled Property Appraiser, ACS, FLU, Opportunity Zone, and FDOT fixtures…</p>
      </div>
    </div>
  );
}
