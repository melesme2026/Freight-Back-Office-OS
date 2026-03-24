const tickets = [
  {
    id: "ticket-1001",
    subject: "Missing invoice for LOAD-1001",
    priority: "high",
    status: "open",
    assignedTo: "Ops Review",
    relatedEntity: "LOAD-1001",
    createdAt: "2026-03-23 09:20 AM",
  },
  {
    id: "ticket-1002",
    subject: "Customer billing email update needed",
    priority: "medium",
    status: "in_progress",
    assignedTo: "Billing Team",
    relatedEntity: "cust-1001",
    createdAt: "2026-03-23 10:05 AM",
  },
  {
    id: "ticket-1003",
    subject: "Failed payment retry follow-up",
    priority: "high",
    status: "escalated",
    assignedTo: "Finance Ops",
    relatedEntity: "INV-1003",
    createdAt: "2026-03-23 11:35 AM",
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
    case "escalated":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function SupportPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Support</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Support</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Track operational tickets, escalations, billing issues, and load-related support
              follow-up in one place.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            New Ticket
          </button>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Open Tickets</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">8</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">In Progress</div>
            <div className="mt-2 text-3xl font-bold text-amber-700">3</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Escalated</div>
            <div className="mt-2 text-3xl font-bold text-rose-700">2</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Resolved Today</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">5</div>
          </div>
        </section>

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Ticket</th>
                  <th className="px-5 py-4 font-semibold">Priority</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Assigned To</th>
                  <th className="px-5 py-4 font-semibold">Related Entity</th>
                  <th className="px-5 py-4 font-semibold">Created</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {tickets.map((ticket) => (
                  <tr key={ticket.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{ticket.subject}</div>
                      <div className="text-xs text-slate-500">{ticket.id}</div>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${priorityBadge(ticket.priority)}`}
                      >
                        {ticket.priority}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(ticket.status)}`}
                      >
                        {ticket.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{ticket.assignedTo}</td>
                    <td className="px-5 py-4 text-slate-700">{ticket.relatedEntity}</td>
                    <td className="px-5 py-4 text-slate-700">{ticket.createdAt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}