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
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col justify-center px-6 py-16">
        <div className="max-w-4xl">
          <div className="mb-6 inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-600 shadow-sm">
            Freight Back Office OS
          </div>

          <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
            Run freight operations, documents, and settlement workflows in one system.
          </h1>

          <p className="mt-5 text-lg leading-8 text-slate-600">
            Freight Back Office OS helps teams run post-booking operations after freight is booked externally: manual load intake, assignment, document collection, invoice readiness, and settlement follow-up.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href="/signup"
              className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-700"
            >
              Create Workspace
            </Link>

            <Link
              href="/login"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Staff Login
            </Link>

            <Link
              href="/driver-login"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Driver Login
            </Link>

            <Link
              href="/request-demo"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Request Demo
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
            <h2 className="text-lg font-semibold text-slate-900">Document ownership at scale</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Keep documents tied to loads with source channel, uploader metadata, and processing
              status so staff can continue operations regardless of intake channel.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-900">Role-aware workspaces</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Separate operator and driver entry flows while preserving organization-scoped controls
              for multi-tenant teams.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-900">Operational finance readiness</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Support billing, invoicing, broker/factoring handoffs, and audit-ready history as your
              back-office operation grows.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
