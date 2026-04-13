"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

const SALES_EMAIL = "mermerbrands@gmail.com";

function encodeMailto(value: string): string {
  return encodeURIComponent(value);
}

export default function RequestDemoPage() {
  const [isContactSales, setIsContactSales] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const title = useMemo(
    () => (isContactSales ? "Contact Sales" : "Request Demo"),
    [isContactSales]
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const intent = (params.get("intent") ?? "demo").toLowerCase();
    setIsContactSales(intent === "contact-sales");
  }, []);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    const trimmedCompany = company.trim();
    const trimmedNotes = notes.trim();

    const subject = isContactSales
      ? `Freight Back Office OS Sales Request — ${trimmedCompany || trimmedName}`
      : `Freight Back Office OS Demo Request — ${trimmedCompany || trimmedName}`;

    const bodyLines = [
      `Request type: ${isContactSales ? "Contact Sales" : "Request Demo"}`,
      "",
      `Full name: ${trimmedName}`,
      `Work email: ${trimmedEmail}`,
      `Company: ${trimmedCompany}`,
      "",
      "Notes:",
      trimmedNotes || "No additional notes provided.",
    ];

    const mailtoUrl = `mailto:${SALES_EMAIL}?subject=${encodeMailto(
      subject
    )}&body=${encodeMailto(bodyLines.join("\n"))}`;

    window.location.href = mailtoUrl;
    setSubmitted(true);
  }

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-12 text-slate-900">
      <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
        <p className="text-sm font-medium text-brand-700">{title}</p>

        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
          {isContactSales
            ? "Talk to Freight Back Office OS sales"
            : "Book a Freight Back Office OS walkthrough"}
        </h1>

        <p className="mt-4 text-sm leading-6 text-slate-600">
          {isContactSales
            ? "Share your rollout scope and target timeline. We will open a real email draft so your request can be sent directly to sales."
            : "Tell us about your team size, workflow, and rollout timeline. We will open a real email draft so your demo request can be sent directly to the team."}
        </p>

        {submitted ? (
          <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Your email draft was opened so you can send your request directly to{" "}
            <span className="font-semibold">{SALES_EMAIL}</span>.
          </div>
        ) : null}

        <form className="mt-8 grid gap-4" onSubmit={onSubmit}>
          <input
            type="text"
            placeholder="Full name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="rounded-xl border border-slate-300 px-4 py-3 text-sm"
          />

          <input
            type="email"
            placeholder="Work email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded-xl border border-slate-300 px-4 py-3 text-sm"
          />

          <input
            type="text"
            placeholder="Company"
            required
            value={company}
            onChange={(event) => setCompany(event.target.value)}
            className="rounded-xl border border-slate-300 px-4 py-3 text-sm"
          />

          <textarea
            placeholder="Monthly load volume, integrations needed, or questions"
            rows={4}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className="rounded-xl border border-slate-300 px-4 py-3 text-sm"
          />

          <button
            type="submit"
            className="w-fit rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            {isContactSales ? "Email sales request" : "Email demo request"}
          </button>
        </form>

        <div className="mt-8 flex flex-wrap gap-3">
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