import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Freight Back Office OS | Freight billing, packets, factoring, and collections",
  description:
    "A freight back-office operating system for carriers, dispatchers, and billing teams that need cleaner billing packets, factoring workflows, invoices, collections visibility, and operational reporting.",
  alternates: {
    canonical: "https://www.adwafreight.com",
  },
  openGraph: {
    title: "Freight Back Office OS",
    description:
      "Run freight billing packets, document uploads, factoring workflows, invoices, collections, and back-office reporting from one operational workspace.",
    url: "https://www.adwafreight.com",
    siteName: "Freight Back Office OS",
    type: "website",
  },
};

const featureGroups = [
  {
    title: "Billing packet management",
    description:
      "Keep rate confirmations, BOLs, invoices, PODs, and supporting documents organized around the load they belong to.",
  },
  {
    title: "Document uploads and review",
    description:
      "Collect paperwork from operators and drivers, then flag missing, duplicate, or review-ready documents before billing starts.",
  },
  {
    title: "Invoice generation",
    description:
      "Create invoice-ready records from operational load data so billing teams are not rebuilding the same details in spreadsheets.",
  },
  {
    title: "Factoring workflows",
    description:
      "Track packet readiness, submission status, exceptions, and follow-up work when freight invoices move through factoring partners.",
  },
  {
    title: "Packet intelligence",
    description:
      "Surface what is missing, what needs review, and which packets are ready for invoice, factoring, or collections action.",
  },
  {
    title: "Analytics and reporting",
    description:
      "Give owners and operators a clearer view of load status, billing progress, document health, and back-office workload.",
  },
  {
    title: "Collections visibility",
    description:
      "Track payment follow-ups, aging work, and operational notes so teams know which invoices need attention next.",
  },
  {
    title: "Accounting exports",
    description:
      "Prepare cleaner accounting handoffs with structured invoice, customer, and payment context for back-office reconciliation.",
  },
  {
    title: "Driver workflows and notifications",
    description:
      "Support driver-facing paperwork handoff and operational notifications without forcing billing teams to chase every update manually.",
  },
];

const workflowSteps = [
  "Add or import the load",
  "Upload ratecon, BOL, POD, and supporting files",
  "Review packet readiness and exceptions",
  "Generate invoice and factoring packet",
  "Track collections, payment follow-up, and accounting export",
];

const screenshotPanels = [
  {
    label: "Analytics dashboard",
    title: "Operational visibility",
    copy: "Monitor load progress, document exceptions, billing status, and back-office workload before small issues become cash-flow delays.",
    metrics: ["Loads in progress", "Packet readiness", "Billing exceptions"],
  },
  {
    label: "Packet intelligence",
    title: "Missing-document control",
    copy: "See which loads are invoice-ready, which need driver paperwork, and which require manual review before submission.",
    metrics: ["Ratecon", "BOL / POD", "Invoice ready"],
  },
  {
    label: "Factoring workflow",
    title: "Submission tracking",
    copy: "Coordinate factoring packets, status changes, exceptions, and follow-ups without losing context across email threads.",
    metrics: ["Ready", "Submitted", "Follow-up"],
  },
];

const plans = [
  {
    name: "Starter",
    price: "$49/mo",
    audience: "Owner-operators and lean dispatch offices",
    cta: "Request Starter demo",
    href: "/request-demo?plan=starter",
    features: [
      "Load and document workspace",
      "Billing packet readiness",
      "Invoice workflow foundation",
      "Driver paperwork handoff",
    ],
  },
  {
    name: "Growth",
    price: "$99/mo",
    audience: "Dispatch teams and growing carrier operations",
    cta: "Request Growth demo",
    href: "/request-demo?plan=growth",
    featured: true,
    features: [
      "Multi-driver operational views",
      "Factoring workflow tracking",
      "Collections and follow-up visibility",
      "Analytics and accounting export support",
    ],
  },
  {
    name: "Fleet / Enterprise",
    price: "Contact sales",
    audience: "Fleets that need rollout planning and workflow design",
    cta: "Contact sales",
    href: "/request-demo?intent=contact-sales&plan=fleet",
    features: [
      "Custom onboarding plan",
      "Workflow mapping for teams",
      "Operational reporting alignment",
      "Integration planning for future phases",
    ],
  },
];

const faqs = [
  {
    question: "Does Freight Back Office OS replace my factoring company?",
    answer:
      "No. It helps your team organize packet readiness, invoice context, submission status, and follow-up work around the factoring workflow you already use.",
  },
  {
    question: "How fast can a small carrier get started?",
    answer:
      "Most teams can begin with a walkthrough, workspace setup, and their next active loads. Rollout timing depends on driver count, document process, and accounting requirements.",
  },
  {
    question: "Can drivers use it from a phone?",
    answer:
      "Yes. Driver-facing workflows are designed for mobile paperwork handoff and operational updates, while staff users keep the full back-office view.",
  },
  {
    question: "What documents can we manage?",
    answer:
      "Teams can organize common freight paperwork such as rate confirmations, BOLs, PODs, invoices, and supporting files needed for billing or factoring packets.",
  },
  {
    question: "Can we export accounting information?",
    answer:
      "The platform supports structured accounting-export workflows so billing, customer, invoice, and payment context can move into downstream back-office processes.",
  },
  {
    question: "Do you claim plug-and-play integrations with every TMS or factoring provider?",
    answer:
      "No. Current onboarding focuses on the operational workflow first. Specific integrations should be reviewed during the demo and planned based on your tools.",
  },
];

export default function HomePage() {
  return (
    <main className="safe-page min-h-screen bg-slate-950 text-white">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/90 backdrop-blur">
        <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8" aria-label="Public navigation">
          <Link href="/" className="flex items-center gap-3 font-semibold tracking-tight">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-500 text-sm font-bold text-white shadow-soft">FB</span>
            <span className="hidden text-sm uppercase tracking-[0.2em] text-slate-200 sm:inline">Freight Back Office OS</span>
          </Link>
          <div className="hidden items-center gap-6 text-sm font-medium text-slate-300 lg:flex">
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#workflow" className="hover:text-white">Workflow</a>
            <a href="#pricing" className="hover:text-white">Pricing</a>
            <a href="#faq" className="hover:text-white">FAQ</a>
          </div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Link href="/login" className="hidden rounded-xl px-4 py-2 text-slate-300 hover:bg-white/10 hover:text-white sm:inline-flex">App login</Link>
            <Link href="/driver-login" className="hidden rounded-xl px-4 py-2 text-slate-300 hover:bg-white/10 hover:text-white md:inline-flex">Driver Login</Link>
            <Link href="/request-demo" className="rounded-xl bg-white px-4 py-2 text-slate-950 shadow-soft transition hover:bg-brand-50">Request demo</Link>
          </div>
        </nav>
      </header>

      <section className="relative overflow-hidden border-b border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(55,125,255,0.32),_transparent_34%),radial-gradient(circle_at_80%_20%,_rgba(14,165,233,0.16),_transparent_28%)]" />
        <div className="relative mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-[1.02fr_0.98fr] lg:px-8 lg:py-24">
          <div className="max-w-3xl">
            <div className="inline-flex max-w-full items-center rounded-full border border-brand-300/30 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand-100">
              Freight billing, packets, factoring, and collections
            </div>
            <h1 className="mt-6 text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
              A cleaner freight back office for paperwork, billing packets, invoices, factoring, and collections.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
              Freight Back Office OS gives carriers, dispatchers, and billing teams one calm workspace for driver document handoff, invoice-ready billing packets, factoring status, collections follow-up, and accounting-export preparation.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link href="/request-demo" className="touch-target inline-flex items-center justify-center rounded-xl bg-brand-500 px-6 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-400">
                Request a demo
              </Link>
              <a href="#workflow" className="touch-target inline-flex items-center justify-center rounded-xl border border-white/20 bg-white/10 px-6 py-3 text-sm font-bold text-white transition hover:bg-white/15">
                See the workflow
              </a>
            </div>
            <dl className="mt-10 grid gap-4 sm:grid-cols-3">
              {[
                ["Packet-first", "Built around freight paperwork readiness"],
                ["Factoring-aware", "Track submission and exception status"],
                ["Mobile-ready", "Driver handoff and staff review on any screen"],
              ].map(([term, detail]) => (
                <div key={term} className="rounded-2xl border border-white/10 bg-white/10 p-4">
                  <dt className="text-sm font-bold text-white">{term}</dt>
                  <dd className="mt-1 text-xs leading-5 text-slate-300">{detail}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/10 p-3 shadow-2xl backdrop-blur">
            <div className="rounded-[1.5rem] bg-slate-50 p-4 text-slate-950 sm:p-6">
              <div className="flex items-center justify-between gap-4 border-b border-slate-200 pb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">Operations board</p>
                  <h2 className="mt-1 text-lg font-bold">Packet readiness</h2>
                </div>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">Live workflow</span>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                {[
                  ["Ready to invoice", "Ready", "bg-emerald-50 text-emerald-700"],
                  ["Needs docs", "Review", "bg-amber-50 text-amber-700"],
                  ["Follow-up due", "Action", "bg-sky-50 text-sky-700"],
                ].map(([label, value, tone]) => (
                  <div key={label} className={`rounded-2xl p-4 ${tone}`}>
                    <p className="text-xs font-semibold">{label}</p>
                    <p className="mt-2 text-2xl font-black">{value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-5 space-y-3">
                {[
                  ["LOAD-1048", "BOL received • invoice queued", "Ready"],
                  ["LOAD-1051", "Missing signed POD", "Needs review"],
                  ["LOAD-1054", "Factoring packet submitted", "Follow-up"],
                ].map(([load, detail, status]) => (
                  <div key={load} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-bold text-slate-950">{load}</p>
                      <p className="text-sm text-slate-600">{detail}</p>
                    </div>
                    <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white py-16 text-slate-950 sm:py-20" id="features">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-700">Operational feature set</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Built for the work after a load is booked.</h2>
            <p className="mt-4 text-base leading-8 text-slate-600">The product presentation is intentionally practical: load documents, packets, invoices, factoring coordination, collections follow-up, accounting handoff, and team visibility.</p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featureGroups.map((feature) => (
              <article key={feature.title} className="rounded-3xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
                <h3 className="text-lg font-bold text-slate-950">{feature.title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">{feature.description}</p>
              </article>
            ))}
          </div>
          <div className="mt-10 rounded-3xl bg-slate-950 p-6 text-white sm:p-8">
            <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
              <div>
                <h3 className="text-2xl font-bold">Want to see it with your billing workflow?</h3>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">Bring your load volume, driver count, document flow, and factoring process to the demo. The walkthrough focuses on your operating reality, not a generic SaaS tour.</p>
              </div>
              <Link href="/request-demo" className="touch-target inline-flex items-center justify-center rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white hover:bg-brand-400">Request demo</Link>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-slate-50 py-16 text-slate-950 sm:py-20" id="workflow">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-start">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-700">Workflow walkthrough</p>
              <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">From load handoff to invoice follow-up.</h2>
              <p className="mt-4 text-base leading-8 text-slate-600">Freight Back Office OS keeps each operational step visible so staff, dispatch, drivers, and billing are not relying on memory or scattered message threads.</p>
              <ol className="mt-8 space-y-3">
                {workflowSteps.map((step, index) => (
                  <li key={step} className="flex gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">{index + 1}</span>
                    <span className="pt-1 text-sm font-semibold text-slate-800">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
            <div className="grid gap-4">
              {screenshotPanels.map((panel) => (
                <article key={panel.label} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">{panel.label}</p>
                      <h3 className="mt-2 text-xl font-bold">{panel.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{panel.copy}</p>
                    </div>
                    <div className="grid min-w-40 gap-2">
                      {panel.metrics.map((metric) => (
                        <span key={metric} className="rounded-full bg-slate-100 px-3 py-2 text-xs font-bold text-slate-700">{metric}</span>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white py-16 text-slate-950 sm:py-20" id="pricing">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-700">Pricing structure</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Plans for small teams now, flexible for billing automation later.</h2>
            <p className="mt-4 text-base leading-8 text-slate-600">Checkout is not implemented in this PR. Pricing cards route visitors into the existing request-demo and contact-sales workflow.</p>
          </div>
          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {plans.map((plan) => (
              <article key={plan.name} className={`rounded-3xl border p-6 shadow-soft ${plan.featured ? "border-brand-300 bg-brand-50" : "border-slate-200 bg-white"}`}>
                {plan.featured ? <p className="mb-3 w-fit rounded-full bg-brand-600 px-3 py-1 text-xs font-bold text-white">Most common for growing teams</p> : null}
                <h3 className="text-2xl font-bold">{plan.name}</h3>
                <p className="mt-1 text-sm text-slate-600">{plan.audience}</p>
                <p className="mt-5 text-3xl font-black">{plan.price}</p>
                <ul className="mt-5 space-y-3 text-sm text-slate-700">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex gap-2"><span className="text-brand-700">•</span><span>{feature}</span></li>
                  ))}
                </ul>
                <a href={plan.href} className={`touch-target mt-6 inline-flex w-full items-center justify-center rounded-xl px-5 py-3 text-sm font-bold transition ${plan.featured ? "bg-brand-600 text-white hover:bg-brand-700" : "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50"}`}>{plan.cta}</a>
              </article>
            ))}
          </div>
          <div className="mt-6 text-center">
            <Link href="/pricing" className="text-sm font-bold text-brand-700 hover:text-brand-800">View dedicated pricing page →</Link>
          </div>
        </div>
      </section>

      <section className="bg-slate-50 py-16 text-slate-950 sm:py-20" id="onboarding">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-700">Onboarding</p>
              <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">A practical rollout for real freight operations.</h2>
              <p className="mt-4 text-base leading-8 text-slate-600">The request-demo flow starts a conversation about load volume, document collection, factoring process, driver usage, and accounting needs. From there, teams can start with active loads and expand the workflow as confidence grows.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {[
                ["1", "Request demo", "Share fleet size, load volume, and the workflows you want to clean up."],
                ["2", "Map the workflow", "Review document intake, packet readiness, invoice handoff, and follow-up ownership."],
                ["3", "Set up workspace", "Configure team access, drivers, customers, brokers, and starting operational data."],
                ["4", "Roll out by load", "Begin with current loads, then expand reporting, factoring tracking, and accounting exports."],
              ].map(([number, title, copy]) => (
                <article key={title} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-950 text-sm font-bold text-white">{number}</span>
                  <h3 className="mt-4 text-lg font-bold">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{copy}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white py-16 text-slate-950 sm:py-20" aria-labelledby="social-proof-title">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-soft sm:p-8 lg:p-10">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-200">Social proof structure</p>
            <h2 id="social-proof-title" className="mt-3 text-3xl font-bold tracking-tight">Designed to earn trust without fabricated claims.</h2>
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {[
                ["Operational review", "Use this card for verified customer feedback after pilots and approvals."],
                ["Implementation note", "Reserve space for documented onboarding outcomes, not inflated enterprise claims."],
                ["Workflow result", "Future proof points can describe measurable packet, billing, or follow-up improvements when validated."],
              ].map(([title, copy]) => (
                <article key={title} className="rounded-2xl border border-white/10 bg-white/10 p-5">
                  <h3 className="font-bold">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{copy}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-slate-50 py-16 text-slate-950 sm:py-20" id="faq">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-700">FAQ</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Practical questions from freight operators.</h2>
          </div>
          <div className="mt-10 grid gap-4 lg:grid-cols-2">
            {faqs.map((faq) => (
              <article key={faq.question} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-lg font-bold">{faq.question}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">{faq.answer}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-slate-950 text-white">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1fr_auto] lg:px-8">
          <div>
            <h2 className="text-xl font-bold">Freight Back Office OS</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">Public marketing website for www.adwafreight.com. Authenticated operations stay under the app experience at app.adwafreight.com routes such as login and dashboard.</p>
          </div>
          <div className="grid gap-3 text-sm font-semibold sm:grid-cols-2 lg:text-right">
            <a href="#features" className="text-slate-300 hover:text-white">Features</a>
            <a href="#pricing" className="text-slate-300 hover:text-white">Pricing</a>
            <Link href="/request-demo" className="text-slate-300 hover:text-white">Request demo</Link>
            <Link href="/driver-login" className="text-slate-300 hover:text-white">Driver Login</Link>
            <Link href="/login" className="text-slate-300 hover:text-white">App login</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
