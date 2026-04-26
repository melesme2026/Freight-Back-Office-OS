"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

type FollowUpTask = {
  id: string;
  due_at?: string | null;
  priority?: string | null;
  task_type?: string | null;
  load_id?: string | null;
  title?: string | null;
  recommended_action?: string | null;
  status?: string | null;
};

export default function FollowUpsPage() {
  const [tasks, setTasks] = useState<FollowUpTask[]>([]);

  useEffect(() => {
    async function load() {
      const token = getAccessToken();
      const response = await apiClient.get<{ data: unknown }>("/follow-ups", { token: token ?? undefined });
      const rows = Array.isArray(response.data) ? response.data : [];
      setTasks(rows as FollowUpTask[]);
    }
    void load();
  }, []);

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <h1 className="text-2xl font-bold text-slate-950">Follow-Ups</h1>
        <p className="mt-2 text-sm text-slate-600">Internal reminders for payment overdue, reserve pending, and packet follow-up.</p>
        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Due date</th>
                <th className="px-3 py-2">Priority</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Load</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Recommended action</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id} className="border-t border-slate-200">
                  <td className="px-3 py-2">{task.due_at ? new Date(task.due_at).toLocaleDateString() : "—"}</td>
                  <td className="px-3 py-2">{(task.priority ?? "normal").replaceAll("_", " ")}</td>
                  <td className="px-3 py-2">{(task.task_type ?? "").replaceAll("_", " ")}</td>
                  <td className="px-3 py-2">{task.load_id?.slice(0, 8)}</td>
                  <td className="px-3 py-2">{task.title}</td>
                  <td className="px-3 py-2">{task.recommended_action}</td>
                  <td className="px-3 py-2">{task.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
