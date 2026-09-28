"use client";

import { useState, type FormEvent } from "react";
import { safeNextPath } from "@/lib/siteGate";

export function LoginForm() {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const password = String(new FormData(event.currentTarget).get("password") ?? "");
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
        credentials: "same-origin",
      });
      if (!response.ok) {
        setError("Incorrect password");
        setPending(false);
        return;
      }
      const next = safeNextPath(new URLSearchParams(window.location.search).get("next"));
      window.location.assign(next);
    } catch {
      setError("Incorrect password");
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-6">
      <label htmlFor="site-password" className="text-[11px] uppercase tracking-[0.18em] text-ink-500">
        Password
      </label>
      <input
        id="site-password"
        name="password"
        type="password"
        autoComplete="current-password"
        autoFocus
        required
        spellCheck={false}
        className="mt-2 w-full rounded-full border border-white/15 bg-ink-800 px-4 py-2.5 text-base text-white outline-none focus:ring-2 focus:ring-clay-400"
      />
      <button
        type="submit"
        disabled={pending}
        className="mt-4 w-full rounded-full bg-clay-500 px-4 py-2.5 text-sm font-semibold text-ink-950 disabled:opacity-50"
      >
        Enter
      </button>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-red-300">
          {error}
        </p>
      ) : null}
    </form>
  );
}
