const notifications = [
  {
    id: "notif-1001",
    channel: "whatsapp",
    direction: "outbound",
    messageType: "missing_document",
    recipient: "Demo Driver",
    status: "sent",
    subject: "Missing invoice for LOAD-1001",
    createdAt: "2026-03-23 09:25 AM",
  },
  {
    id: "notif-1002",
    channel: "email",
    direction: "outbound",
    messageType: "billing_reminder",
    recipient: "billing@demo-freight.com",
    status: "queued",
    subject: "Invoice reminder for INV-1005",
    createdAt: "2026-03-23 10:10 AM",
  },
  {
    id: "notif-1003",
    channel: "in_app",
    direction: "inbound",
    messageType: "support_update",
    recipient: "Ops Dashboard",
    status: "delivered",
    subject: "Support ticket updated",
    createdAt: "2026-03-23 11:02 AM",
  },
];

function statusBadge(status: string) {
  switch (status) {
    case "sent":
      return "bg-emerald-100 text-emerald-800";
    case "queued":
      return "bg-amber-100 text-amber-800";
    case "delivered":
      return "bg-blue-100 text-blue-800";
    case "failed":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function NotificationsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Notifications</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Notifications</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Track outbound and inbound operational notifications across WhatsApp, email, and
              in-app channels.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            New Notification
          </button>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Total today</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">18</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Queued</div>
            <div className="mt-2 text-3xl font-bold text-amber-600">4</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Sent</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">11</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Failed</div>
            <div className="mt-2 text-3xl font-bold text-rose-700">1</div>
          </div>
        </section>

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Notification</th>
                  <th className="px-5 py-4 font-semibold">Channel</th>
                  <th className="px-5 py-4 font-semibold">Direction</th>
                  <th className="px-5 py-4 font-semibold">Recipient</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Created</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {notifications.map((notification) => (
                  <tr key={notification.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{notification.subject}</div>
                      <div className="text-xs text-slate-500">{notification.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{notification.channel}</td>
                    <td className="px-5 py-4 text-slate-700">{notification.direction}</td>
                    <td className="px-5 py-4 text-slate-700">{notification.recipient}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(notification.status)}`}
                      >
                        {notification.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{notification.createdAt}</td>
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