"use client";

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
        "1 organization, document uploads, load workflow tracking, invoice PDF generation, notifications, and billing-lite support.",
      href: starter.href,
      cta: starter.configured ? "Start Starter" : "Setup required",
      external: starter.configured,
      unavailableNote: starter.configured ? undefined : "Starter Stripe payment link is not configured yet.",
    },
    {
      name: "Growth",
      price: "$99/mo",
      summary:
        "Everything in Starter, better fit for active teams, higher operational capacity, and priority support.",
      href: growth.href,
      cta: growth.configured ? "Start Growth" : "Setup required",
      external: growth.configured,
      unavailableNote: growth.configured ? undefined : "Growth Stripe payment link is not configured yet.",
    },
    {
      name: "Enterprise",
      price: "Contact us",
      summary: "Custom onboarding, custom pricing, and contact-led setup.",
      href: appConfig.pricing.enterpriseContact,
      cta: "Contact Sales",
      external: true,
    },
  ];

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-medium text-brand-700">Pricing</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-950">Simple organization billing for V1</h1>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Billing is organization-scoped. Admin teams subscribe or use manual activation while driver workflows remain operational.
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
                rel={plan.external ? "noreferrer" : undefined}
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
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
