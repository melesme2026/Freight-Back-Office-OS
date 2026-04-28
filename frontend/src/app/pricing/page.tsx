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
      subtitle: "Owner-operators and dispatchers replacing manual workflows",
      price: "$49/mo",
      summary:
        "For owner-operators and dispatchers replacing manual paperwork, texts, and email workflows.",
      href: isPilotMode ? "/signup" : starter.href,
      cta: isPilotMode ? "Start using now" : starter.configured ? "Start Starter" : "Contact support",
      external: !isPilotMode && starter.configured,
    },
    {
      name: "Growth",
      subtitle: "Dispatch teams managing multiple drivers",
      price: "$99/mo",
      summary:
        "For dispatchers managing multiple drivers who need structured document flow, invoicing, payment visibility, and follow-up tracking.",
      href: isPilotMode ? "/request-demo" : growth.href,
      cta: isPilotMode ? "Request onboarding" : growth.configured ? "Start Growth" : "Contact support",
      external: !isPilotMode && growth.configured,
    },
    {
      name: "Enterprise",
      subtitle: "Small fleets and multi-role operations",
      price: "Contact Sales",
      summary:
        "For fleets that need custom onboarding, workflow design, priority support, and future integrations.",
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
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-950">Simple freight back-office plans</h1>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Already running loads manually? Start with your next load and keep your current brokers,
            dispatch flow, and drivers.
          </p>
        </div>

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-700 shadow-soft">
          {isPilotMode ? (
            <p>
              Pilot access: start using the platform now. Billing is activated after onboarding.
            </p>
          ) : (
            <p>
              Live billing mode is enabled. Plan checkout opens Stripe in a new tab when configured.
            </p>
          )}
        </section>

        <section className="mt-10 grid gap-5 md:grid-cols-3">
          {plans.map((plan) => {
            const isDisabledLive = !isPilotMode && !plan.external && plan.name !== "Enterprise" && plan.cta === "Contact support";
            return (
              <article key={plan.name} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
                <h2 className="text-xl font-semibold text-slate-950">{plan.name}</h2>
                <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">{plan.subtitle}</p>
                <p className="mt-2 text-3xl font-bold text-slate-900">{plan.price}</p>
                <p className="mt-3 text-sm leading-6 text-slate-600">{plan.summary}</p>

                <a
                  href={plan.href || "/request-demo"}
                  target={plan.external ? "_blank" : undefined}
                  rel={plan.external ? "noopener noreferrer" : undefined}
                  className={`mt-6 inline-flex rounded-xl px-4 py-2 text-sm font-semibold transition ${
                    plan.external || isPilotMode
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

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-soft">
          <h2 className="text-lg font-semibold text-slate-900">What happens after signup?</h2>
          <p className="mt-2 text-sm text-slate-600">
            Add your next load, upload documents, generate the invoice, send the packet, and track payment follow-up from one workspace.
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            <Link href="/signup" className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
              Create workspace
            </Link>
            <Link href="/request-demo" className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Talk to onboarding team
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
