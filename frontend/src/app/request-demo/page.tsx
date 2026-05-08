"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { buildApiUrl } from "@/lib/config";

const SALES_EMAIL = "mermerbrands@gmail.com";

export default function RequestDemoPage() {
  const [isContactSales, setIsContactSales] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"success" | "error">("success");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [phone, setPhone] = useState("");
  const [fleetSize, setFleetSize] = useState("");
  const [notes, setNotes] = useState("");

  const title = useMemo(() => (isContactSales ? "Contact Sales" : "Request Demo"), [isContactSales]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const intent = (params.get("intent") ?? "demo").toLowerCase();
    const plan = params.get("plan");
    setIsContactSales(intent === "contact-sales");
    setSelectedPlan(plan ? plan.trim() : null);
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }
    setIsSubmitting(true);
    setStatusMessage(null);
    setStatusTone("success");

    const messageParts = [
      selectedPlan ? `Plan interest: ${selectedPlan}` : null,
      notes || null,
    ].filter(Boolean);

    try {
      const response = await fetch(buildApiUrl("/demo-requests"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: name,
          email,
          company,
          phone: phone || null,
          fleet_size: fleetSize || null,
          message: messageParts.length > 0 ? messageParts.join("\n\n") : null,
        }),
      });

      if (!response.ok) {
        throw new Error("failed");
      }

      setStatusTone("success");
      setStatusMessage("Demo request received. We’ll contact you shortly.");
      setName("");
      setEmail("");
      setCompany("");
      setPhone("");
      setFleetSize("");
      setNotes("");
    } catch {
      setStatusTone("error");
      setStatusMessage(`We couldn’t save your request. Please email ${SALES_EMAIL}.`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="safe-page min-h-screen bg-slate-50 text-slate-900">
      <section className="bg-slate-950 px-4 py-10 text-white sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4">
          <Link href="/" className="text-sm font-semibold text-slate-300 hover:text-white">
            ← Back to marketing site
          </Link>
          <Link href="/pricing" className="rounded-xl border border-white/15 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-white/10">
            View pricing
          </Link>
        </div>
      </section>

      <div className="mx-auto grid max-w-5xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[0.85fr_1.15fr] lg:px-8">
        <aside className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft lg:sticky lg:top-8 lg:self-start">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-700">{title}</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
            {isContactSales ? "Talk to Freight Back Office OS sales" : "Book a freight back-office walkthrough"}
          </h1>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Share enough context for a practical walkthrough: load volume, driver count, billing packet process, factoring workflow, collections follow-up, and accounting export needs.
          </p>
          <div className="mt-6 space-y-3 text-sm text-slate-700">
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="font-bold text-slate-950">What we will review</p>
              <p className="mt-1 leading-6">Document intake, invoice readiness, factoring status, driver handoff, and rollout expectations.</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="font-bold text-slate-950">No Stripe checkout yet</p>
              <p className="mt-1 leading-6">Pricing interest is routed into the existing lead workflow for onboarding review.</p>
            </div>
          </div>
        </aside>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft sm:p-8" aria-labelledby="request-demo-heading">
          <p className="text-sm font-medium text-brand-700">Conversion form</p>
          <h2 id="request-demo-heading" className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            {isContactSales ? "Submit a sales request" : "Submit a demo request"}
          </h2>
          {selectedPlan ? <p className="mt-2 text-sm text-slate-600">Plan interest: <span className="font-semibold capitalize text-slate-900">{selectedPlan}</span></p> : null}

          {statusMessage ? (
            <div
              className={`mt-6 rounded-xl border px-4 py-3 text-sm ${
                statusTone === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-amber-200 bg-amber-50 text-amber-800"
              }`}
            >
              {statusMessage}
            </div>
          ) : null}

          <form className="mt-8 grid gap-4" onSubmit={onSubmit}>
            <label className="grid gap-2 text-sm font-semibold text-slate-700">
              Full name
              <input type="text" required value={name} onChange={(event) => setName(event.target.value)} className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 text-sm font-normal outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-slate-700">
              Work email
              <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 text-sm font-normal outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-slate-700">
              Company
              <input type="text" required value={company} onChange={(event) => setCompany(event.target.value)} className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 text-sm font-normal outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Phone <span className="font-normal text-slate-500">(optional)</span>
                <input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 text-sm font-normal outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Fleet size <span className="font-normal text-slate-500">(optional)</span>
                <input type="text" value={fleetSize} onChange={(event) => setFleetSize(event.target.value)} className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 text-sm font-normal outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
              </label>
            </div>
            <label className="grid gap-2 text-sm font-semibold text-slate-700">
              Workflow notes <span className="font-normal text-slate-500">(optional)</span>
              <textarea placeholder="Monthly load volume, factoring workflow, driver document process, accounting exports, or questions" rows={5} value={notes} onChange={(event) => setNotes(event.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-normal outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
            </label>
            <button type="submit" disabled={isSubmitting} className="min-h-11 w-full rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-70 sm:w-fit">
              {isSubmitting ? "Submitting..." : isContactSales ? "Submit sales request" : "Submit demo request"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
