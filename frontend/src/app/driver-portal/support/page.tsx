const supportSections = [
  {
    title: "My Tickets",
    description:
      "Driver-facing support tickets will appear here once the driver portal is wired to live support request data.",
    status: "Planned after V1",
  },
  {
    title: "Operational Help",
    description:
      "Drivers will be able to request help for missing documents, load issues, and billing questions after support APIs are release-ready.",
    status: "Planned after V1",
  },
  {
    title: "Support Guidance",
    description:
      "Self-service guidance and issue routing can be expanded once the underlying ticket creation and tracking flows are fully wired.",
    status: "Planned after V1",
  },
] as const;

const supportExamples = [
  "Missing invoice or document not showing up",
  "Load status looks incorrect",
  "Payment status seems wrong",
  "Need help with upload issues",
] as const;

export default function DriverSupportPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Support</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Support</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Support visibility in the driver portal is intentionally lightweight in V1 to avoid
            showing hardcoded ticket data or unsupported ticket creation flows.
          </p>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr,1fr]">
          <section className="grid gap-5">
            {supportSections.map((section) => (
              <div
                key={section.title}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <h2 className="text-lg font-semibold text-slate-950">{section.title}</h2>
                  <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                    {section.status}
                  </span>
                </div>

                <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
              </div>
            ))}
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">When to open support</h2>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                {supportExamples.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">V1 note</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Live ticket subjects, priorities, statuses, timestamps, and ticket creation should
                only be shown after the driver portal is connected to real support endpoints with
                proper session-scoped access control and response normalization.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}