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
  subtitle: string;
  features: string[];
  highlighted?: boolean;
};

function resolvePlanLink(link: string): { href: string; configured: boolean } {
  const trimmed = link.trim();
  if (!trimmed) {
    return { href: "", configured: false };
  }
  return { href: trimmed, configured: true };
}

export default function PricingPage() {
  const starter = resolvePlanLink(appConfig.pricing.starterLink);
  const growth = resolvePlanLink(appConfig.pricing.growthLink);
  const isPilotMode = appConfig.billing.mode === "pilot";

  const plans: Plan[] = [
    {
      name: "Starter",
      subtitle: "Owner-operators and lean dispatch desks",
      price: "$49/mo",
      summary:
        "Start replacing manual paperwork, text chains, and spreadsheet billing trackers with one freight back-office workspace.",
      href: isPilotMode ? "/request-demo?plan=starter" : starter.href,
      cta: isPilotMode ? "Request Starter demo" : starter.configured ? "Start Starter" : "Contact support",
      external: !isPilotMode && starter.configured,
      features: [
        "Load and document workspace",
        "Billing packet readiness tracking",
        "Invoice workflow foundation",
        "Driver paperwork handoff",
      ],
    },
    {
      name: "Growth",
      subtitle: "Dispatch teams managing multiple drivers",
      price: "$99/mo",
      summary:
        "Coordinate documents, packet intelligence, factoring status, collections follow-up, and operational reporting across a growing team.",
      href: isPilotMode ? "/request-demo?plan=growth" : growth.href,
      cta: isPilotMode ? "Request Growth demo" : growth.configured ? "Start Growth" : "Contact support",
      external: !isPilotMode && growth.configured,
      highlighted: true,
      features: [
        "Multi-driver operational views",
        "Factoring workflow tracking",
        "Collections and follow-up visibility",
        "Analytics and accounting export support",
      ],
    },
    {
      name: "Fleet / Enterprise",
      subtitle: "Fleets that need rollout planning",
      price: "Contact sales",
      summary:
        "For freight operations that need workflow mapping, onboarding support, reporting alignment, and integration planning.",
      href: `${appConfig.pricing.enterpriseContact}?intent=contact-sales&plan=fleet`,
      cta: "Contact sales",
      external: false,
      features: [
        "Custom onboarding plan",
        "Team and workflow design",
        "Operational reporting alignment",
        "Future integration planning",
      ],
    },
  ];

  return (
    <main className="safe-page min-h-screen bg-slate-50 text-slate-900">
      <section className="bg-slate-950 px-4 py-12 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <Link href="/" className="text-sm font-semibold text-slate-300 hover:text-white">
              ← Public site
            </Link>
            <div className="flex gap-2">
              <Link href="/login" className="rounded-xl border border-white/15 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-white/10">
                Staff workspace
              </Link>
              <Link href="/request-demo" className="rounded-xl bg-white px-4 py-2 text-sm font-bold text-slate-950 hover:bg-brand-50">
                Request demo
              </Link>
            </div>
          </div>
          <div className="mt-12 max-w-3xl">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-200">Pricing</p>
            <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">Clear starting points for freight back-office teams.</h1>
            <p className="mt-5 text-base leading-8 text-slate-300">
              Choose the plan level that matches your current operation. Stripe checkout is intentionally not enabled in this PR; each plan currently routes to demo or sales review so onboarding can match your billing, factoring, driver, and accounting process.
            </p>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <section className="rounded-3xl border border-slate-200 bg-white p-5 text-sm text-slate-700 shadow-soft">
          {isPilotMode ? (
            <p>
              Pilot access mode: pricing is presented for planning and qualification. Billing activation is handled after onboarding review.
            </p>
          ) : (
            <p>
              Live billing mode is enabled. Plan checkout opens Stripe in a new tab when configured; unavailable plans route to support or sales review.
            </p>
          )}
        </section>

        <section className="mt-10 grid gap-5 lg:grid-cols-3" aria-label="Pricing plans">
          {plans.map((plan) => {
            const isDisabledLive = !isPilotMode && !plan.external && plan.name !== "Fleet / Enterprise" && plan.cta === "Contact support";
            return (
              <article key={plan.name} className={`rounded-3xl border p-6 shadow-soft ${plan.highlighted ? "border-brand-300 bg-brand-50" : "border-slate-200 bg-white"}`}>
                {plan.highlighted ? <p className="mb-3 w-fit rounded-full bg-brand-600 px-3 py-1 text-xs font-bold text-white">Common growth path</p> : null}
                <h2 className="text-2xl font-bold text-slate-950">{plan.name}</h2>
                <p className="mt-1 text-sm font-medium text-slate-600">{plan.subtitle}</p>
                <p className="mt-5 text-3xl font-black text-slate-950">{plan.price}</p>
                <p className="mt-4 text-sm leading-6 text-slate-600">{plan.summary}</p>
                <ul className="mt-5 space-y-3 text-sm text-slate-700">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex gap-2"><span className="text-brand-700">•</span><span>{feature}</span></li>
                  ))}
                </ul>

                <a
                  href={plan.href || "/request-demo"}
                  target={plan.external ? "_blank" : undefined}
                  rel={plan.external ? "noopener noreferrer" : undefined}
                  className={`mt-6 inline-flex min-h-11 w-full items-center justify-center rounded-xl px-4 py-3 text-sm font-bold transition ${
                    plan.highlighted || plan.external || isPilotMode
                      ? "bg-brand-600 text-white hover:bg-brand-700"
                      : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  {plan.cta}
                </a>

                {isDisabledLive ? (
                  <p className="mt-3 text-xs text-slate-500">
                    Checkout is unavailable right now. Contact support to activate this plan.
                  </p>
                ) : null}
              </article>
            );
          })}
        </section>

        <section className="mt-10 rounded-3xl border border-slate-200 bg-white p-6 shadow-soft sm:p-8">
          <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <h2 className="text-2xl font-bold text-slate-950">What happens after a pricing conversation?</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                The onboarding review confirms your load volume, driver usage, packet requirements, factoring workflow, collections process, and accounting export needs before billing activation.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
              <Link href="/request-demo" className="rounded-xl bg-brand-600 px-5 py-3 text-center text-sm font-bold text-white hover:bg-brand-700">
                Request demo
              </Link>
              <Link href="/request-demo?intent=contact-sales" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-center text-sm font-bold text-slate-700 hover:bg-slate-100">
                Contact sales
              </Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
