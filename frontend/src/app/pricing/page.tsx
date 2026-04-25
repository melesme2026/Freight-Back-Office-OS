"use client";

import Link from "next/link";

import { appConfig } from "@/lib/config";

type Plan = {
  name: string;
  price: string;
  summary: string;
  href: string;
  cta: string;
  external?: boolean;
  unavailableNote?: string;
};

function resolvePlanLink(link: string): { href: string; configured: boolean } {
  const trimmed = link.trim();
  if (!trimmed) {
    return { href: "/dashboard/billing", configured: false };
  }
  return { href: trimmed, configured: true };
}

export default function PricingPage() {
  const starter = resolvePlanLink(appConfig.pricing.starterLink);
  const growth = resolvePlanLink(appConfig.pricing.growthLink);

  const plans: Plan[] = [
    {
      name: "Starter",
      price: "$49/mo",
      summary:
        "For owner-led and small teams handling post-booking load intake, document collection, packet readiness, invoice preparation, and basic follow-up.",
      href: starter.href,
      cta: starter.configured ? "Start Starter" : "Setup required",
      external: starter.configured,
      unavailableNote: starter.configured ? undefined : "Starter checkout link is not configured. Contact support to activate billing.",
    },
    {
      name: "Growth",
      price: "$99/mo",
      summary:
        "For active dispatch and billing teams that need faster document throughput, stronger follow-up execution, and higher workflow capacity.",
      href: growth.href,
      cta: growth.configured ? "Start Growth" : "Setup required",
      external: growth.configured,
      unavailableNote: growth.configured ? undefined : "Growth checkout link is not configured. Contact support to activate billing.",
    },
    {
      name: "Enterprise",
      price: "Contact us",
      summary: "Custom workflow design, onboarding support, and request-based integrations or factoring/back-office coordination.",
      href: `${appConfig.pricing.enterpriseContact}?intent=contact-sales`,
      cta: "Contact Sales",
      external: false,
    },
  ];

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-4 flex justify-center">
            <Link
              href="/"
              className="inline-flex rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              ← Back to landing
            </Link>
          </div>
          <p className="text-sm font-medium text-brand-700">Pricing</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-950">Back-office plans built for freight teams</h1>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Plans are designed for post-booking operations: document workflows, invoice readiness, settlement follow-up, and coordinated team/driver execution.
          </p>
        </div>

        <section className="mt-10 grid gap-5 md:grid-cols-3">
          {plans.map((plan) => (
            <article key={plan.name} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-xl font-semibold text-slate-950">{plan.name}</h2>
              <p className="mt-2 text-3xl font-bold text-slate-900">{plan.price}</p>
              <p className="mt-3 text-sm leading-6 text-slate-600">{plan.summary}</p>

              <a
                href={plan.href}
                target={plan.external ? "_blank" : undefined}
                rel={plan.external ? "noopener noreferrer" : undefined}
                className={`mt-6 inline-flex rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  plan.external
                    ? "bg-brand-600 text-white hover:bg-brand-700"
                    : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                }`}
              >
                {plan.cta}
              </a>

              {plan.unavailableNote ? (
                <p className="mt-3 text-xs text-amber-700">{plan.unavailableNote}</p>
              ) : null}
              {plan.external ? (
                <p className="mt-3 text-xs text-slate-500">
                  Opens Stripe checkout in a new tab so you can keep this page open.
                </p>
              ) : null}
            </article>
          ))}
        </section>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-soft">
          <h2 className="text-lg font-semibold text-slate-900">Need a guided setup call?</h2>
          <p className="mt-2 text-sm text-slate-600">
            Use Request Demo for onboarding support or Contact Sales for enterprise rollout planning.
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            <Link href="/request-demo" className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Request Demo
            </Link>
            <a
              href={`${appConfig.pricing.enterpriseContact}?intent=contact-sales`}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Contact Sales
            </a>
          </div>
        </section>
      </div>
    </main>
  );
}
