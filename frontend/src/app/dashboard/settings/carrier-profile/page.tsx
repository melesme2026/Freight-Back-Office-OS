"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getUserRole } from "@/lib/auth";

type CarrierProfile = {
  legal_name: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  phone: string;
  email: string;
  mc_number: string;
  dot_number: string;
  remit_to_name: string;
  remit_to_address: string;
  remit_to_notes: string;
};

const EMPTY: CarrierProfile = {
  legal_name: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  zip: "",
  country: "USA",
  phone: "",
  email: "",
  mc_number: "",
  dot_number: "",
  remit_to_name: "",
  remit_to_address: "",
  remit_to_notes: "",
};

export default function CarrierProfilePage() {
  const [profile, setProfile] = useState<CarrierProfile>(EMPTY);
  const [exists, setExists] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const token = getAccessToken() ?? undefined;
  const role = (getUserRole() || "").toLowerCase();
  const canEdit = role === "owner" || role === "admin";

  useEffect(() => {
    let mounted = true;
    async function fetchProfile() {
      try {
        setIsLoading(true);
        setError(null);
        const response = await apiClient.get<{ data?: Partial<CarrierProfile> }>("/carrier-profile", {
          token,
        });
        if (!mounted) return;
        setProfile({ ...EMPTY, ...(response?.data ?? {}) } as CarrierProfile);
        setExists(true);
      } catch {
        if (!mounted) return;
        setProfile(EMPTY);
        setExists(false);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }
    void fetchProfile();
    return () => {
      mounted = false;
    };
  }, [token]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canEdit) {
      setError("Only owner/admin can update carrier profile.");
      return;
    }
    try {
      setIsSaving(true);
      setError(null);
      setSuccess(null);
      const method = exists ? apiClient.patch : apiClient.post;
      const response = await method<{ data?: Partial<CarrierProfile> }>("/carrier-profile", profile, { token });
      setProfile({ ...EMPTY, ...(response?.data ?? {}) } as CarrierProfile);
      setExists(true);
      setSuccess("Carrier profile saved.");
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Failed to save carrier profile.");
    } finally {
      setIsSaving(false);
    }
  }

  const set = (key: keyof CarrierProfile, value: string) => setProfile((p) => ({ ...p, [key]: value }));

  if (isLoading) return <main className="p-6">Loading...</main>;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-4xl px-6 py-10">
        <p className="text-sm font-medium text-brand-700">Dashboard / Settings / Carrier Profile</p>
        <h1 className="text-3xl font-bold">Carrier Profile</h1>
        <p className="mt-2 text-sm text-slate-600">Single source of truth for invoice carrier details.</p>
        {error ? <div className="mt-4 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div> : null}
        {success ? <div className="mt-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{success}</div> : null}
        <form onSubmit={(event) => void handleSubmit(event)} className="mt-6 grid gap-4 rounded-2xl border bg-white p-6">
          <input placeholder="Company Name" value={profile.legal_name} onChange={(e) => set("legal_name", e.target.value)} className="rounded border p-2" />
          <input placeholder="Address Line 1" value={profile.address_line1} onChange={(e) => set("address_line1", e.target.value)} className="rounded border p-2" />
          <input placeholder="Address Line 2" value={profile.address_line2} onChange={(e) => set("address_line2", e.target.value)} className="rounded border p-2" />
          <div className="grid gap-3 md:grid-cols-3">
            <input placeholder="City" value={profile.city} onChange={(e) => set("city", e.target.value)} className="rounded border p-2" />
            <input placeholder="State" value={profile.state} onChange={(e) => set("state", e.target.value)} className="rounded border p-2" />
            <input placeholder="ZIP" value={profile.zip} onChange={(e) => set("zip", e.target.value)} className="rounded border p-2" />
          </div>
          <input placeholder="Phone" value={profile.phone} onChange={(e) => set("phone", e.target.value)} className="rounded border p-2" />
          <input placeholder="Email" value={profile.email} onChange={(e) => set("email", e.target.value)} className="rounded border p-2" />
          <input placeholder="MC Number" value={profile.mc_number} onChange={(e) => set("mc_number", e.target.value)} className="rounded border p-2" />
          <input placeholder="DOT Number" value={profile.dot_number} onChange={(e) => set("dot_number", e.target.value)} className="rounded border p-2" />
          <input placeholder="Remit-To Name" value={profile.remit_to_name} onChange={(e) => set("remit_to_name", e.target.value)} className="rounded border p-2" />
          <textarea placeholder="Remit-To Address" value={profile.remit_to_address} onChange={(e) => set("remit_to_address", e.target.value)} className="rounded border p-2" rows={3} />
          <textarea placeholder="Remit-To Instructions" value={profile.remit_to_notes} onChange={(e) => set("remit_to_notes", e.target.value)} className="rounded border p-2" rows={3} />
          <button disabled={!canEdit || isSaving} className="rounded bg-brand-600 px-4 py-2 font-semibold text-white disabled:opacity-60">
            {isSaving ? "Saving..." : "Save Carrier Profile"}
          </button>
        </form>
      </div>
    </main>
  );
}
