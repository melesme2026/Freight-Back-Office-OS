const settingsSections = [
  {
    title: "Organization",
    description: "Manage organization profile, branding, and contact defaults.",
    status: "Planned after V1",
  },
  {
    title: "Notifications",
    description: "Configure notification channels, templates, and reminder behavior.",
    status: "Planned after V1",
  },
  {
    title: "Billing Preferences",
    description: "Set invoice defaults, billing contacts, and payment collection options.",
    status: "Planned after V1",
  },
  {
    title: "Security",
    description: "Review authentication, API access, and future role-based controls.",
    status: "Planned after V1",
  },
] as const;

export default function SettingsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Dashboard / Settings</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Settings</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Manage organization-wide defaults, billing preferences, communication settings, and
            future security controls.
          </p>
        </div>

        <section className="grid gap-5 md:grid-cols-2">
          {settingsSections.map((section) => (
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

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">V1 note</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Settings in V1 are intentionally lightweight. The goal is to provide a stable operating
            baseline first, then expand into full multi-tenant admin controls, permissions, and
            advanced configuration later.
          </p>
        </section>
      </div>
    </main>
  );
}