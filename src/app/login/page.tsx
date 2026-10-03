import type { Metadata } from "next";
import { Suspense } from "react";
import Image from "next/image";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = {
  title: "Sign in · Southeast rural OZ 2.0 land search",
};

export default function LoginPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-ink-950 px-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))] pt-[max(2.5rem,env(safe-area-inset-top))] pb-[max(2.5rem,env(safe-area-inset-bottom))] text-ink-100">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="overflow-hidden rounded-lg bg-white ring-1 ring-white/40">
            <Image
              src="/catalyst-logo.webp"
              alt="Catalyst Development Partners"
              width={110}
              height={112}
              priority
              className="block h-16 w-auto"
              style={{ width: "auto" }}
            />
          </div>
          <p className="mt-5 text-[11px] uppercase tracking-[0.22em] text-clay-400">Catalyst Development Partners</p>
          <h1 className="mt-1 font-display text-2xl tracking-tight text-white">Land search</h1>
        </div>
        <div className="rounded-2xl border border-white/10 bg-ink-900 px-5 py-6 shadow-2xl sm:px-6">
          <Suspense fallback={<div className="h-28" />}>
            <LoginForm />
          </Suspense>
        </div>
      </div>
    </main>
  );
}
