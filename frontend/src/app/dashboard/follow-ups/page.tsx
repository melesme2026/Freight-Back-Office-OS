"use client";

import { useEffect, useMemo, useState } from "react";

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [taskTypeFilter, setTaskTypeFilter] = useState("all");
  const [savingId, setSavingId] = useState<string | null>(null);

  async function loadTasks() {
    const token = getAccessToken();
    const response = await apiClient.get<{ data: unknown }>("/follow-ups", { token: token ?? undefined });
    const rows = Array.isArray(response.data) ? response.data : [];
    setTasks(rows as FollowUpTask[]);
  }

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        await loadTasks();
      } catch (caught: unknown) {
        setError(caught instanceof Error ? caught.message : "Failed to load follow-ups.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  async function runAction(taskId: string, action: "complete" | "cancel" | "snooze") {
    try {
      setSavingId(taskId);
      setError(null);
      const token = getAccessToken();
      if (action === "snooze") {
        const until = new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString();
        await apiClient.post(`/follow-ups/${encodeURIComponent(taskId)}/snooze`, { until }, { token: token ?? undefined });
      } else {
        await apiClient.post(`/follow-ups/${encodeURIComponent(taskId)}/${action}`, {}, { token: token ?? undefined });
      }
      await loadTasks();
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Failed to update follow-up task.");
    } finally {
      setSavingId(null);
    }
  }

  const filteredTasks = useMemo(() => tasks.filter((task) => {
    if (statusFilter !== "all" && (task.status ?? "") !== statusFilter) return false;
    if (priorityFilter !== "all" && (task.priority ?? "") !== priorityFilter) return false;
    if (taskTypeFilter !== "all" && (task.task_type ?? "") !== taskTypeFilter) return false;
    return true;
  }), [priorityFilter, statusFilter, taskTypeFilter, tasks]);

  const statuses = Array.from(new Set(tasks.map((task) => task.status).filter(Boolean))) as string[];
  const priorities = Array.from(new Set(tasks.map((task) => task.priority).filter(Boolean))) as string[];
  const taskTypes = Array.from(new Set(tasks.map((task) => task.task_type).filter(Boolean))) as string[];

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <h1 className="text-2xl font-bold text-slate-950">Follow-Ups</h1>
        <p className="mt-2 text-sm text-slate-600">Internal reminders for payment overdue, reserve pending, and packet follow-up.</p>

        <div className="mt-5 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-3">
          <label className="text-xs font-semibold uppercase text-slate-500">Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm">
              <option value="all">All</option>
              {statuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold uppercase text-slate-500">Priority
            <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm">
              <option value="all">All</option>
              {priorities.map((priority) => <option key={priority} value={priority}>{priority.replaceAll("_", " ")}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold uppercase text-slate-500">Task type
            <select value={taskTypeFilter} onChange={(event) => setTaskTypeFilter(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm">
              <option value="all">All</option>
              {taskTypes.map((taskType) => <option key={taskType} value={taskType}>{taskType.replaceAll("_", " ")}</option>)}
            </select>
          </label>
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
          {loading ? <div className="p-4 text-sm text-slate-500">Loading follow-up tasks…</div> : null}
          {error ? <div className="border-b border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}
          {!loading && filteredTasks.length === 0 ? <div className="p-4 text-sm text-slate-600">{tasks.length === 0 ? "No follow-ups yet. Create a load, upload docs, generate an invoice, then use follow-ups for overdue or reserve-pending actions." : "No follow-up tasks match current filters."}</div> : null}
          {!loading && filteredTasks.length > 0 ? (
            <div className="overflow-x-auto">
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
                    <th className="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTasks.map((task) => (
                    <tr key={task.id} className="border-t border-slate-200">
                      <td className="px-3 py-2">{task.due_at ? new Date(task.due_at).toLocaleDateString() : "—"}</td>
                      <td className="px-3 py-2">{(task.priority ?? "normal").replaceAll("_", " ")}</td>
                      <td className="px-3 py-2">{(task.task_type ?? "").replaceAll("_", " ")}</td>
                      <td className="px-3 py-2">{task.load_id?.slice(0, 8)}</td>
                      <td className="px-3 py-2">{task.title}</td>
                      <td className="px-3 py-2">{task.recommended_action}</td>
                      <td className="px-3 py-2">{task.status?.replaceAll("_", " ")}</td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2">
                          <button disabled={savingId === task.id} onClick={() => void runAction(task.id, "complete")} className="rounded border border-slate-300 px-2 py-1 text-xs">Complete</button>
                          <button disabled={savingId === task.id} onClick={() => void runAction(task.id, "snooze")} className="rounded border border-slate-300 px-2 py-1 text-xs">Snooze</button>
                          <button disabled={savingId === task.id} onClick={() => void runAction(task.id, "cancel")} className="rounded border border-slate-300 px-2 py-1 text-xs">Cancel</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
