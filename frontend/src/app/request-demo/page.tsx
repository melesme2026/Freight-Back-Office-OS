"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { buildApiUrl } from "@/lib/config";

const SALES_EMAIL = "mermerbrands@gmail.com";

export default function RequestDemoPage() {
  const [isContactSales, setIsContactSales] = useState(false);
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
    setIsContactSales(intent === "contact-sales");
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }
    setIsSubmitting(true);
    setStatusMessage(null);
    setStatusTone("success");

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
          message: notes || null,
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
    <main className="min-h-screen bg-slate-50 px-6 py-12 text-slate-900">
      <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
        <p className="text-sm font-medium text-brand-700">{title}</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
          {isContactSales ? "Talk to Freight Back Office OS sales" : "Book a Freight Back Office OS walkthrough"}
        </h1>

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
          <input type="text" placeholder="Full name" required value={name} onChange={(event) => setName(event.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" />
          <input type="email" placeholder="Work email" required value={email} onChange={(event) => setEmail(event.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" />
          <input type="text" placeholder="Company" required value={company} onChange={(event) => setCompany(event.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" />
          <input type="tel" placeholder="Phone (optional)" value={phone} onChange={(event) => setPhone(event.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" />
          <input type="text" placeholder="Fleet size (optional)" value={fleetSize} onChange={(event) => setFleetSize(event.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" />
          <textarea placeholder="Monthly load volume, integrations needed, or questions" rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" />
          <button type="submit" disabled={isSubmitting} className="w-fit rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-70">
            {isSubmitting ? "Submitting..." : isContactSales ? "Submit sales request" : "Submit demo request"}
          </button>
        </form>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/pricing" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">View pricing</Link>
          <Link href="/" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">Back to landing</Link>
        </div>
      </div>
    </main>
  );
}
