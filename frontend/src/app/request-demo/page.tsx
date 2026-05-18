"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { BrandLogo } from "@/components/ui/BrandLogo";
import { buildApiUrl } from "@/lib/config";

const SALES_EMAIL = "mermerbrands@gmail.com";

const profileOptions = [
  "Carrier / fleet owner",
  "Owner-operator",
  "Dispatcher / dispatch office",
  "Broker / customer operations",
  "Factoring or back-office partner",
] as const;

const workflowOptions = [
  "Billing packets and invoice readiness",
  "Driver paperwork collection",
  "Factoring submission tracking",
  "Collections and payment follow-up",
  "Pilot workspace setup",
] as const;

const timelineOptions = [
  "This week",
  "Next 2 weeks",
  "This month",
  "Researching for later",
] as const;

type RequestIntent = "demo" | "contact-sales" | "request-access";

function normalizeIntent(value: string | null): RequestIntent {
  const normalized = (value ?? "demo").toLowerCase();
  if (normalized === "contact-sales") {
    return "contact-sales";
  }
  if (normalized === "request-access") {
    return "request-access";
  }
  return "demo";
}

export default function RequestDemoPage() {
  const [requestIntent, setRequestIntent] = useState<RequestIntent>("demo");
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"success" | "error">("success");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [phone, setPhone] = useState("");
  const [fleetSize, setFleetSize] = useState("");
  const [profile, setProfile] = useState<(typeof profileOptions)[number]>(profileOptions[0]);
  const [workflow, setWorkflow] = useState<(typeof workflowOptions)[number]>(workflowOptions[0]);
  const [timeline, setTimeline] = useState<(typeof timelineOptions)[number]>(timelineOptions[1]);
  const [notes, setNotes] = useState("");

  const requestCopy = useMemo(() => {
    if (requestIntent === "contact-sales") {
      return {
        eyebrow: "Contact Sales",
        heading: "Talk through your freight back-office rollout.",
        formTitle: "Submit a sales request",
        cta: "Submit sales request",
        success: "Sales request received. We will review your workflow and follow up with practical next steps.",
      };
    }

    if (requestIntent === "request-access") {
      return {
        eyebrow: "Request access",
        heading: "Request pilot access for an operational workspace.",
        formTitle: "Submit an access request",
        cta: "Request access",
        success: "Access request received. We will review fit and follow up with onboarding next steps.",
      };
    }

    return {
      eyebrow: "Request demo",
      heading: "Book a freight back-office walkthrough.",
      formTitle: "Submit a demo request",
      cta: "Submit demo request",
      success: "Demo request received. We will contact you shortly with the next step.",
    };
  }, [requestIntent]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setRequestIntent(normalizeIntent(params.get("intent")));

    const plan = params.get("plan")?.trim();
    setSelectedPlan(plan && plan.length > 0 ? plan : null);
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
      `Intent: ${requestCopy.eyebrow}`,
      selectedPlan ? `Plan interest: ${selectedPlan}` : null,
      `Profile: ${profile}`,
      `Primary workflow: ${workflow}`,
      `Preferred timeline: ${timeline}`,
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
          message: messageParts.join("\n\n"),
        }),
      });

      if (!response.ok) {
        throw new Error("failed");
      }

      setStatusTone("success");
      setStatusMessage(requestCopy.success);
      setName("");
      setEmail("");
      setCompany("");
      setPhone("");
      setFleetSize("");
      setProfile(profileOptions[0]);
      setWorkflow(workflowOptions[0]);
      setTimeline(timelineOptions[1]);
      setNotes("");
    } catch {
      setStatusTone("error");
      setStatusMessage(`We could not save your request. Please email ${SALES_EMAIL}.`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="safe-page min-h-screen bg-slate-50 text-slate-900">
      <section className="bg-slate-950 px-4 py-8 text-white sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3" aria-label="Freight Back Office OS home">
            <BrandLogo variant="operatingSystem" tone="dark" className="h-11 w-auto" priority />
          </Link>
          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
            <Link href="/" className="rounded-xl px-4 py-2 text-slate-300 hover:bg-white/10 hover:text-white">
              Public site
            </Link>
            <Link href="/pricing" className="rounded-xl border border-white/15 px-4 py-2 text-slate-200 hover:bg-white/10">
              View pricing
            </Link>
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[0.82fr_1.18fr] lg:px-8">
        <aside className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft lg:sticky lg:top-8 lg:self-start">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-700">{requestCopy.eyebrow}</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{requestCopy.heading}</h1>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Share just enough context for a practical conversation: load volume, driver count, billing packet process, factoring workflow, collections follow-up, and accounting export needs.
          </p>

          <div className="mt-6 grid gap-3 text-sm text-slate-700">
            {[
              ["What we review", "Document intake, invoice readiness, factoring status, driver handoff, and rollout expectations."],
              ["Pilot-friendly", "We can start with active loads and a focused team before expanding workflows."],
              ["No checkout required", "Pricing interest routes into the lead workflow so onboarding can match your operation."],
            ].map(([title, copy]) => (
              <div key={title} className="rounded-2xl bg-slate-50 p-4">
                <p className="font-bold text-slate-950">{title}</p>
                <p className="mt-1 leading-6">{copy}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 rounded-2xl border border-brand-100 bg-brand-50 p-4 text-sm text-brand-950">
            <p className="font-bold">Prefer email?</p>
            <p className="mt-1 leading-6">
              Send workflow details to <a href={`mailto:${SALES_EMAIL}`} className="font-bold underline decoration-brand-300 underline-offset-4">{SALES_EMAIL}</a>.
            </p>
          </div>
        </aside>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft sm:p-8" aria-labelledby="request-demo-heading">
          <p className="text-sm font-medium text-brand-700">Public request intake</p>
          <h2 id="request-demo-heading" className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            {requestCopy.formTitle}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Required fields are limited to name, email, and company. The rest helps us tailor the walkthrough.
          </p>
          {selectedPlan ? (
            <p className="mt-3 w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] text-slate-700">
              Plan interest: {selectedPlan}
            </p>
          ) : null}

          {statusMessage ? (
            <div
              className={`mt-6 rounded-2xl border px-4 py-4 text-sm leading-6 ${
                statusTone === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                  : "border-amber-200 bg-amber-50 text-amber-900"
              }`}
              role="status"
            >
              <p className="font-bold">{statusTone === "success" ? "Request received" : "Request not saved"}</p>
              <p className="mt-1">{statusMessage}</p>
            </div>
          ) : null}

          <form className="mt-8 grid gap-5" onSubmit={onSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Full name
                <input type="text" required autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} className="brand-input min-h-11" />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Work email
                <input type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="brand-input min-h-11" />
              </label>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Company
                <input type="text" required autoComplete="organization" value={company} onChange={(event) => setCompany(event.target.value)} className="brand-input min-h-11" />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Phone <span className="font-normal text-slate-500">(optional)</span>
                <input type="tel" autoComplete="tel" value={phone} onChange={(event) => setPhone(event.target.value)} className="brand-input min-h-11" />
              </label>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Your role
                <select value={profile} onChange={(event) => setProfile(event.target.value as typeof profile)} className="brand-input min-h-11">
                  {profileOptions.map((option) => <option key={option}>{option}</option>)}
                </select>
              </label>
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Fleet size <span className="font-normal text-slate-500">(optional)</span>
                <input type="text" placeholder="Example: 3 trucks, 12 drivers" value={fleetSize} onChange={(event) => setFleetSize(event.target.value)} className="brand-input min-h-11" />
              </label>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Main workflow
                <select value={workflow} onChange={(event) => setWorkflow(event.target.value as typeof workflow)} className="brand-input min-h-11">
                  {workflowOptions.map((option) => <option key={option}>{option}</option>)}
                </select>
              </label>
              <label className="grid gap-2 text-sm font-semibold text-slate-700">
                Timeline
                <select value={timeline} onChange={(event) => setTimeline(event.target.value as typeof timeline)} className="brand-input min-h-11">
                  {timelineOptions.map((option) => <option key={option}>{option}</option>)}
                </select>
              </label>
            </div>

            <label className="grid gap-2 text-sm font-semibold text-slate-700">
              Workflow notes <span className="font-normal text-slate-500">(optional)</span>
              <textarea placeholder="Monthly load volume, factoring workflow, driver document process, accounting exports, or questions" rows={5} value={notes} onChange={(event) => setNotes(event.target.value)} className="brand-input" />
            </label>

            <div className="flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs leading-5 text-slate-500">
                No payment step. No CRM handoff. This creates a lead for a focused onboarding conversation.
              </p>
              <button type="submit" disabled={isSubmitting} className="brand-button-primary min-h-11 w-full bg-brand-600 hover:bg-brand-700 sm:w-fit">
                {isSubmitting ? "Submitting..." : requestCopy.cta}
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
