"use client";

import { FormEvent, useState } from "react";
import { useSearchParams } from "next/navigation";
import { safeNextPath } from "@/lib/siteGate";

export function LoginForm() {
  const searchParams = useSearchParams();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ password }),
      });
      if (response.status === 401) {
        setError("Incorrect password");
        setPending(false);
        return;
      }
      if (!response.ok) {
        setError("Could not sign in. Try again.");
        setPending(false);
        return;
      }
      // Full navigation so the new cookie is on the next document request.
      window.location.assign(safeNextPath(searchParams.get("next")));
    } catch {
      setError("Could not sign in. Try again.");
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <label className="flex flex-col gap-2 text-sm text-ink-300" htmlFor="password">
        Password
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          required
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
            if (error) setError(null);
          }}
          className="w-full rounded-full border border-white/15 bg-ink-800 px-4 py-3 text-base text-white outline-none focus:border-clay-400/70 focus:ring-2 focus:ring-clay-400/40"
        />
      </label>
      {error ? (
        <p role="alert" className="text-sm text-clay-400">
          {error}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={pending}
        className="min-h-11 rounded-full bg-clay-500 px-5 py-2.5 text-sm font-semibold text-ink-950 disabled:opacity-60"
      >
        {pending ? "Checking…" : "Enter"}
      </button>
    </form>
  );
}
