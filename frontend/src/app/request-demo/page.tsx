import Link from "next/link";

import { appConfig } from "@/lib/config";

export default function RequestDemoPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-12 text-slate-900">
      <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
        <p className="text-sm font-medium text-brand-700">Request Demo</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
          Book a Freight Back Office OS walkthrough
        </h1>
        <p className="mt-4 text-sm leading-6 text-slate-600">
          Tell us about your team size, current workflow, and rollout timeline. We will follow up to
          schedule a guided demo and onboarding call.
        </p>

        <div className="mt-8 grid gap-4 rounded-xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-700">
          <p>
            <span className="font-semibold">Primary contact:</span> mermerbrands@gmail.com
          </p>
          <p>
            <span className="font-semibold">What to include:</span> expected monthly load volume,
            current tooling, and required integrations.
          </p>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <a
            href={`${appConfig.pricing.enterpriseContact}?subject=Freight%20Back%20Office%20OS%20Demo%20Request`}
            className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            Email sales to request demo
          </a>
          <Link
            href="/pricing"
            className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            View pricing
          </Link>
          <Link
            href="/"
            className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Back to landing
          </Link>
        </div>
      </div>
    </main>
  );
}
