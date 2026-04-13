"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type OrganizationSettings = {
  id: string;
  name: string;
  slug: string;
  legal_name: string;
  email: string;
  phone: string;
  timezone: string;
  currency_code: string;
  is_active: boolean;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asText(value: unknown, fallback = ""): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

function asBoolean(value: unknown): boolean {
  return value === true || value === "true" || value === 1 || value === "1";
}

function normalizeOrganization(payload: unknown): OrganizationSettings | null {
  const root = asRecord(payload);
  const data = asRecord(root?.data) ?? root;

  if (!data) {
    return null;
  }

  const id = asText(data.id);
  if (!id) {
    return null;
  }

  return {
    id,
    name: asText(data.name),
    slug: asText(data.slug),
    legal_name: asText(data.legal_name),
    email: asText(data.email),
    phone: asText(data.phone),
    timezone: asText(data.timezone, "America/Toronto"),
    currency_code: asText(data.currency_code, "USD"),
    is_active: asBoolean(data.is_active),
  };
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<OrganizationSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!organizationId) {
      setErrorMessage("Missing organization context.");
      setIsLoading(false);
      return;
    }

    let mounted = true;

    async function loadSettings() {
      try {
        setIsLoading(true);
        setErrorMessage(null);
        setSuccessMessage(null);

        const payload = await apiClient.get<unknown>(`/organizations/${organizationId}`, {
          token: token ?? undefined,
          organizationId: organizationId ?? undefined,
        });

        if (!mounted) return;
        const normalized = normalizeOrganization(payload);
        if (!normalized) {
          throw new Error("Unexpected organization settings response.");
        }
        setSettings(normalized);
      } catch (error: unknown) {
        if (!mounted) return;
        setSettings(null);
        setErrorMessage(
          error instanceof Error ? error.message : "Failed to load organization settings."
        );
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    void loadSettings();

    return () => {
      mounted = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!settings || !organizationId) {
      setErrorMessage("Settings context is unavailable.");
      return;
    }

    try {
      setIsSaving(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      const payload = await apiClient.patch<unknown>(
        `/organizations/${organizationId}`,
        {
          name: settings.name,
          slug: settings.slug,
          legal_name: settings.legal_name || null,
          email: settings.email || null,
          phone: settings.phone || null,
          timezone: settings.timezone,
          currency_code: settings.currency_code,
          is_active: settings.is_active,
        },
        {
          token: token ?? undefined,
          organizationId: organizationId ?? undefined,
        }
      );

      const normalized = normalizeOrganization(payload);
      if (normalized) {
        setSettings(normalized);
      }
      setSuccessMessage("Settings updated successfully.");
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to update settings.");
    } finally {
      setIsSaving(false);
    }
  }

  function updateField<K extends keyof OrganizationSettings>(field: K, value: OrganizationSettings[K]) {
    setSettings((current) => (current ? { ...current, [field]: value } : current));
    setSuccessMessage(null);
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Dashboard / Settings</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Organization Settings</h1>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        {successMessage ? (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {successMessage}
          </div>
        ) : null}

        {isLoading ? (
          <section className="rounded-2xl border border-slate-200 bg-white px-6 py-8 text-sm text-slate-600 shadow-soft">
            Loading settings...
          </section>
        ) : settings ? (
          <form
            onSubmit={(event) => void handleSubmit(event)}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
          >
            <div className="grid gap-5 md:grid-cols-2">
              <label className="text-sm text-slate-700">
                Name
                <input
                  value={settings.name}
                  onChange={(event) => updateField("name", event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="text-sm text-slate-700">
                Slug
                <input
                  value={settings.slug}
                  onChange={(event) => updateField("slug", event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="text-sm text-slate-700">
                Legal name
                <input
                  value={settings.legal_name}
                  onChange={(event) => updateField("legal_name", event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="text-sm text-slate-700">
                Email
                <input
                  type="email"
                  value={settings.email}
                  onChange={(event) => updateField("email", event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="text-sm text-slate-700">
                Phone
                <input
                  value={settings.phone}
                  onChange={(event) => updateField("phone", event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="text-sm text-slate-700">
                Timezone
                <input
                  value={settings.timezone}
                  onChange={(event) => updateField("timezone", event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="text-sm text-slate-700">
                Currency code
                <input
                  value={settings.currency_code}
                  onChange={(event) => updateField("currency_code", event.target.value.toUpperCase())}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                  maxLength={3}
                />
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={settings.is_active}
                  onChange={(event) => updateField("is_active", event.target.checked)}
                />
                Organization active
              </label>
            </div>

            <button
              type="submit"
              disabled={isSaving}
              className="mt-6 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {isSaving ? "Saving..." : "Save settings"}
            </button>
          </form>
        ) : (
          <section className="rounded-2xl border border-slate-200 bg-white px-6 py-8 text-sm text-slate-600 shadow-soft">
            Settings unavailable.
          </section>
        )}
      </div>
    </main>
  );
}
