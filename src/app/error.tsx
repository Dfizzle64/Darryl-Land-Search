"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex h-dvh items-center justify-center bg-ink-950 px-4 text-ink-100">
      <div className="max-w-md rounded-2xl border border-red-500/30 bg-ink-900 px-6 py-5">
        <p className="font-display text-2xl text-white">Unable to load the site search</p>
        <p className="mt-2 text-sm text-ink-300">{error.message || "An unexpected error occurred."}</p>
        <button
          type="button"
          onClick={reset}
          className="mt-4 rounded-full bg-clay-500 px-4 py-2 text-sm text-ink-950"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
