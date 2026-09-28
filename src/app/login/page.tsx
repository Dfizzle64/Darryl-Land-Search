import type { Metadata } from "next";
import { CompanyLogo } from "@/components/CompanyLogo";
import { LoginForm } from "@/components/LoginForm";

export const metadata: Metadata = {
  title: "Sign in",
};

export default function LoginPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-ink-950 px-4 py-10">
      <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-ink-900 px-5 py-8 shadow-2xl sm:px-6">
        <div className="flex items-center gap-3">
          <CompanyLogo />
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-[0.22em] text-clay-400">Catalyst</p>
            <h1 className="font-display text-2xl tracking-tight text-white">Sign in</h1>
          </div>
        </div>
        <p className="mt-4 text-sm text-ink-300">Southeast rural OZ 2.0 land search</p>
        <LoginForm />
      </div>
    </main>
  );
}
