const supportTickets = [
  {
    id: "ticket-1001",
    subject: "Invoice still missing for LOAD-1001",
    priority: "high",
    status: "open",
    createdAt: "2026-03-23 09:20 AM",
  },
  {
    id: "ticket-1002",
    subject: "Need help confirming payment status",
    priority: "medium",
    status: "in_progress",
    createdAt: "2026-03-22 03:10 PM",
  },
];

function priorityBadge(priority: string) {
  switch (priority) {
    case "high":
      return "bg-rose-100 text-rose-800";
    case "medium":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function statusBadge(status: string) {
  switch (status) {
    case "open":
      return "bg-blue-100 text-blue-800";
    case "in_progress":
      return "bg-amber-100 text-amber-800";
    case "resolved":
      return "bg-emerald-100 text-emerald-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function DriverSupportPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Driver Portal / Support</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Support</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Open support requests for missing documents, billing questions, or operational issues.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            New Ticket
          </button>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr,1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="mb-4 text-lg font-semibold text-slate-950">My Tickets</h2>
            <div className="space-y-3">
              {supportTickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className="rounded-xl border border-slate-200 px-4 py-4"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">{ticket.subject}</div>
                      <div className="mt-1 text-xs text-slate-500">{ticket.id}</div>
                    </div>

                    <div className="flex gap-2">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${priorityBadge(ticket.priority)}`}
                      >
                        {ticket.priority}
                      </span>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(ticket.status)}`}
                      >
                        {ticket.status.replace("_", " ")}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 text-xs text-slate-500">
                    Created: {ticket.createdAt}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">When to open support</h2>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                <li>• Missing invoice or document not showing up</li>
                <li>• Load status looks incorrect</li>
                <li>• Payment status seems wrong</li>
                <li>• Need help with upload issues</li>
              </ul>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">V1 note</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                In V1, support is intentionally simple and focused on visibility. Ticket messaging
                and threaded conversations can be expanded later.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}