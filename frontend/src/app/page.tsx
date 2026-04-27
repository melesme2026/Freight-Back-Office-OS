"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearAuth, getAccessToken, getOrganizationId, getUserRole } from "@/lib/auth";
import { resolvePostLoginRoute } from "@/lib/rbac";

export default function HomePage() {
  const router = useRouter();
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    const accessToken = getAccessToken();
    const organizationId = getOrganizationId();
    const role = getUserRole();

    if (accessToken && organizationId) {
      router.replace(resolvePostLoginRoute(role));
      return;
    }

    if (accessToken && !organizationId) {
      clearAuth();
    }

    setIsCheckingSession(false);
  }, [router]);

  if (isCheckingSession) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-4 text-sm text-slate-600 shadow-soft">
          Checking session...
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="max-w-5xl">
          <div className="mb-6 inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-600 shadow-sm">
            Freight Back Office OS
          </div>

          <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
            Run your freight back office without spreadsheets, texts, or lost paperwork.
          </h1>

          <p className="mt-5 text-lg leading-8 text-slate-600">
            Freight Back Office OS helps owner-operators, dispatchers, and small fleets manage
            post-booking operations: loads, documents, invoices, packets, payments, and follow-ups.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href="/signup"
              className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-700"
            >
              Create Workspace
            </Link>
            <Link
              href="/request-demo"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Request Onboarding
            </Link>
            <Link
              href="/driver-login"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Driver Login
            </Link>
            <Link
              href="/login"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Staff Login
            </Link>
            <Link
              href="/pricing"
              className="rounded-xl border border-brand-300 bg-brand-50 px-5 py-3 text-sm font-semibold text-brand-700 transition hover:bg-brand-100"
            >
              View Pricing
            </Link>
          </div>
        </div>

        <div className="mt-14 grid gap-5 md:grid-cols-3">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-900">For owner-operators</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Replace paperwork and text chains with one place to capture load details, track docs,
              and move invoices forward.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-900">For dispatchers managing drivers</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Keep dispatch and document flow organized across multiple drivers without changing your
              broker relationships or load sourcing process.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-900">For billing and back-office teams</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Build invoice-ready packets, track payment follow-up, and keep status visible from
              booking handoff through settlement.
            </p>
          </section>
        </div>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-900">How it works</h2>
          <ol className="mt-3 grid gap-3 text-sm text-slate-600 md:grid-cols-5">
            <li>1. Add your next load</li>
            <li>2. Upload documents</li>
            <li>3. Generate invoice</li>
            <li>4. Send packet</li>
            <li>5. Track payment follow-up</li>
          </ol>
        </section>
      </div>
    </main>
  );
}
