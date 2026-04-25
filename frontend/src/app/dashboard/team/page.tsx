"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type StaffMember = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  last_login_at?: string | null;
};

type InviteResponse = {
  data?: {
    email_status?: string;
    message?: string;
    activation_url?: string;
  };
};

const STAFF_ROLES = [
  { value: "admin", label: "Admin" },
  { value: "ops_manager", label: "Operations Manager" },
  { value: "ops_agent", label: "Operations Agent" },
  { value: "billing_admin", label: "Billing Admin" },
  { value: "support_agent", label: "Support Agent" },
  { value: "viewer", label: "Viewer" },
];

function formatDateTime(value?: string | null): string {
  if (!value) return "Never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Never";
  return date.toLocaleString();
}

export default function TeamPage() {
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("ops_agent");
  const [isInviting, setIsInviting] = useState(false);
  const [inviteStatus, setInviteStatus] = useState<string | null>(null);
  const [activationUrl, setActivationUrl] = useState<string | null>(null);

  const token = getAccessToken();
  const organizationId = getOrganizationId();

  async function loadStaff() {
    if (!token || !organizationId) {
      setErrorMessage("Missing session context. Please sign in again.");
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      const payload = await apiClient.get<{ data?: StaffMember[] }>("/staff-users?page=1&page_size=200", {
        token,
        organizationId,
      });
      setStaffMembers(payload?.data ?? []);
      setErrorMessage(null);
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load team members.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadStaff();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleInviteStaff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !organizationId) {
      setErrorMessage("Missing session context. Please sign in again.");
      return;
    }
    if (!inviteName.trim() || !inviteEmail.trim()) {
      setInviteStatus("Full name and email are required.");
      return;
    }

    try {
      setIsInviting(true);
      setInviteStatus(null);
      setActivationUrl(null);
      const payload = await apiClient.post<InviteResponse>(
        "/auth/invite-user",
        {
          full_name: inviteName.trim(),
          email: inviteEmail.trim().toLowerCase(),
          role: inviteRole,
          organization_id: organizationId,
        },
        { token, organizationId }
      );

      const message = payload?.data?.message?.trim();
      const emailStatus = payload?.data?.email_status?.trim();
      setInviteStatus(message ?? `Invite processed. Email status: ${emailStatus ?? "unknown"}.`);
      setActivationUrl(payload?.data?.activation_url?.trim() || null);
      setInviteName("");
      setInviteEmail("");
      await loadStaff();
    } catch (error: unknown) {
      setInviteStatus(error instanceof Error ? error.message : "Unable to send invite.");
    } finally {
      setIsInviting(false);
    }
  }

  async function handleCopyActivationLink() {
    if (!activationUrl) return;
    try {
      await navigator.clipboard.writeText(activationUrl);
      setInviteStatus("Activation link copied. Share it directly with the invited team member.");
    } catch {
      setInviteStatus("Activation link is shown below. Copy it manually.");
    }
  }

  const activeCount = useMemo(() => staffMembers.filter((member) => member.is_active).length, [staffMembers]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Dashboard / Team</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Team Workspace</h1>
          <p className="mt-2 text-sm text-slate-600">
            Invite office staff from this workspace. Driver onboarding remains in each driver profile after the driver record is created.
          </p>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">Invite staff member</h2>
          <p className="mt-1 text-sm text-slate-600">
            Choose a role and send activation access. If email is disabled, copy the activation link and send it manually.
          </p>

          <form onSubmit={(event) => void handleInviteStaff(event)} className="mt-4 grid gap-4 md:grid-cols-2">
            <input
              value={inviteName}
              onChange={(event) => setInviteName(event.target.value)}
              placeholder="Staff full name"
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
              disabled={isInviting}
            />
            <input
              type="email"
              value={inviteEmail}
              onChange={(event) => setInviteEmail(event.target.value)}
              placeholder="staff@company.com"
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
              disabled={isInviting}
            />
            <select
              value={inviteRole}
              onChange={(event) => setInviteRole(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
              disabled={isInviting}
            >
              {STAFF_ROLES.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
            <button
              type="submit"
              disabled={isInviting}
              className="rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {isInviting ? "Sending invite..." : "Invite staff"}
            </button>
          </form>

          {inviteStatus ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              {inviteStatus}
            </div>
          ) : null}

          {activationUrl ? (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p className="font-semibold">Manual activation link</p>
              <p className="mt-1 break-all">{activationUrl}</p>
              <button
                type="button"
                onClick={() => void handleCopyActivationLink()}
                className="mt-3 rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-semibold text-amber-900"
              >
                Copy Link
              </button>
            </div>
          ) : null}
        </section>

        {errorMessage ? (
          <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
            <h2 className="text-lg font-semibold text-slate-950">Team members</h2>
            <div className="text-xs text-slate-500">Active: {activeCount} / {staffMembers.length}</div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-6 py-3 font-semibold">Name</th>
                  <th className="px-6 py-3 font-semibold">Email</th>
                  <th className="px-6 py-3 font-semibold">Role</th>
                  <th className="px-6 py-3 font-semibold">Activation</th>
                  <th className="px-6 py-3 font-semibold">Last Login</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500">Loading team members...</td>
                  </tr>
                ) : staffMembers.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500">No staff users found yet.</td>
                  </tr>
                ) : (
                  staffMembers.map((member) => (
                    <tr key={member.id}>
                      <td className="px-6 py-4 text-slate-900">{member.full_name}</td>
                      <td className="px-6 py-4 text-slate-700">{member.email}</td>
                      <td className="px-6 py-4 text-slate-700">{member.role.replaceAll("_", " ")}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${member.is_active ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                          {member.is_active ? "Active" : "Pending activation"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-700">{formatDateTime(member.last_login_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
