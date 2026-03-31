import Link from "next/link";
import type { Route } from "next";

type OnboardingStep = {
  id: string;
  title: string;
  description: string;
  href: string;
  ctaLabel: string;
};

const onboardingSteps: OnboardingStep[] = [
  {
    id: "customer-profile",
    title: "Customer profile",
    description: "Create and verify the customer account before onboarding work begins.",
    href: "/dashboard/customers",
    ctaLabel: "Open Customers",
  },
  {
    id: "driver-setup",
    title: "Driver setup",
    description: "Add drivers and validate their records before dispatch operations begin.",
    href: "/dashboard/drivers",
    ctaLabel: "Open Drivers",
  },
  {
    id: "billing-setup",
    title: "Billing setup",
    description: "Confirm pricing, invoices, subscriptions, and payment readiness.",
    href: "/dashboard/billing",
    ctaLabel: "Open Billing",
  },
  {
    id: "document-readiness",
    title: "Document readiness",
    description: "Review required documents and resolve missing or invalid items before go-live.",
    href: "/dashboard/documents",
    ctaLabel: "Open Documents",
  },
  {
    id: "load-readiness",
    title: "Operational readiness",
    description: "Validate load workflows and downstream processing before the account goes live.",
    href: "/dashboard/loads",
    ctaLabel: "Open Loads",
  },
  {
    id: "review-queue",
    title: "Review queue",
    description: "Resolve extracted field issues and manual review items that can block activation.",
    href: "/dashboard/review-queue",
    ctaLabel: "Open Review Queue",
  },
];

const readinessChecks: readonly string[] = [
  "Customer account created and verified",
  "Required onboarding documents received",
  "Pricing confirmed",
  "Payment method or billing workflow configured",
  "Drivers created and validated",
  "Channel and notification path configured",
  "Open review items resolved",
  "Initial operational workflow validated",
];

function toRoute(href: string): Route {
  return href as Route;
}

export default function OnboardingPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Onboarding</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Onboarding</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Manage customer onboarding through the live operational modules. This page provides a
              production-safe entry point for onboarding tasks without exposing placeholder metrics
              or demo-only account data in release paths.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href={toRoute("/dashboard/customers")}
              className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              Open Customers
            </Link>
            <Link
              href={toRoute("/dashboard/review-queue")}
              className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Open Review Queue
            </Link>
          </div>
        </div>

        <section className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">Onboarding workspace</h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  Use the linked modules below to complete onboarding work with real system data.
                  This avoids stale dashboard snapshots and keeps staff in the authoritative
                  workflows.
                </p>
              </div>
              <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                Release-safe
              </span>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {onboardingSteps.map((step) => (
                <article
                  key={step.id}
                  className="flex h-full flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5"
                >
                  <h3 className="text-base font-semibold text-slate-950">{step.title}</h3>
                  <p className="mt-2 flex-1 text-sm leading-6 text-slate-600">
                    {step.description}
                  </p>
                  <div className="mt-4">
                    <Link
                      href={toRoute(step.href)}
                      className="inline-flex items-center text-sm font-semibold text-brand-700 transition hover:text-brand-800"
                    >
                      {step.ctaLabel} →
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <aside className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-950">Go-live checklist</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Use this checklist as the operational standard before marking an account ready.
            </p>

            <ul className="mt-5 space-y-3">
              {readinessChecks.map((item) => (
                <li key={item} className="flex items-start gap-3 rounded-xl bg-slate-50 px-4 py-3">
                  <span
                    aria-hidden="true"
                    className="mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700"
                  >
                    ✓
                  </span>
                  <span className="text-sm text-slate-700">{item}</span>
                </li>
              ))}
            </ul>
          </aside>
        </section>

        <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">Implementation note</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            This route intentionally avoids hardcoded counts and sample customer records. Until a
            dedicated onboarding API exists, onboarding status should be managed through the live
            customer, billing, document, driver, load, and review queue modules.
          </p>

          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href={toRoute("/dashboard/customers")}
              className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Customer accounts
            </Link>
            <Link
              href={toRoute("/dashboard/documents")}
              className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Document review
            </Link>
            <Link
              href={toRoute("/dashboard/billing")}
              className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Billing readiness
            </Link>
            <Link
              href={toRoute("/dashboard/drivers")}
              className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Driver readiness
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}