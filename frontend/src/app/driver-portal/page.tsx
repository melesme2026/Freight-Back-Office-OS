import Link from "next/link";

const driverPortalSections = [
  {
    title: "Uploads",
    description: "Send rate cons, BOLs, invoices, and supporting paperwork.",
    href: "/driver-portal/uploads",
    status: "Available in V1 shell",
  },
  {
    title: "Loads",
    description:
      "View load-related workspace sections and prepare for live driver-scoped load visibility.",
    href: "/driver-portal/loads",
    status: "Available in V1 shell",
  },
  {
    title: "Billing",
    description:
      "Review billing workspace sections for future invoice and payment visibility.",
    href: "/driver-portal/billing",
    status: "Available in V1 shell",
  },
  {
    title: "Support",
    description:
      "Access support guidance and future driver-facing issue tracking workflows.",
    href: "/driver-portal/support",
    status: "Available in V1 shell",
  },
] as const;

const rolloutNotes = [
  "Driver-scoped live data should only appear after backend APIs and access control are fully wired.",
  "Avoid showing hardcoded counts for loads, uploads, invoices, payments, or support tickets.",
  "Keep the portal stable, navigable, and production-safe for V1 rollout.",
] as const;

export default function DriverPortalPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Driver Workspace
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Upload paperwork, view load-related workflow areas, review billing sections, and access
            support guidance without needing the full operator dashboard.
          </p>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">V1 portal status</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            The driver portal is intentionally lightweight in V1. Navigation is available, but live
            driver-specific counts and transactional records should only be shown after the portal
            is fully connected to real backend data.
          </p>

          <ul className="mt-4 space-y-2 text-sm leading-6 text-slate-600">
            {rolloutNotes.map((note) => (
              <li key={note}>• {note}</li>
            ))}
          </ul>
        </section>

        <section className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {driverPortalSections.map((section) => (
            <Link
              key={section.title}
              href={section.href}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300"
            >
              <div className="flex items-start justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-950">{section.title}</h2>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                  {section.status}
                </span>
              </div>

              <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
            </Link>
          ))}
        </section>
      </div>
    </main>
  );
}