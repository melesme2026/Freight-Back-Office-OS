"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { clearAuth, getAccessToken, getUserRole, setAuthSession } from "@/lib/auth";
import { resolvePostLoginRoute } from "@/lib/rbac";

type LoginResponse = {
  data?: {
    access_token?: string;
    token_type?: string;
    user?: {
      role?: string;
    };
  };
  message?: string;
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  } | null;
};

const DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001";

function normalizeText(value: string): string {
  return value.trim();
}

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

function isValidEmail(value: string): boolean {
  const normalized = normalizeEmail(value);
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized);
}

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationId, setOrganizationId] = useState(DEFAULT_ORGANIZATION_ID);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  // 🔥 Auto-redirect if already logged in
  useEffect(() => {
    const token = getAccessToken();
    const userRole = getUserRole();

    if (token) {
      router.replace(resolvePostLoginRoute(userRole));
    } else {
      setIsCheckingSession(false);
    }
  }, [router]);

  const normalizedOrganizationId = useMemo(
    () => normalizeText(organizationId),
    [organizationId]
  );

  const normalizedEmail = useMemo(() => normalizeEmail(email), [email]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!normalizedOrganizationId) {
      setErrorMessage("Organization ID is required.");
      return;
    }

    if (!normalizedEmail) {
      setErrorMessage("Email is required.");
      return;
    }

    if (!isValidEmail(normalizedEmail)) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!password) {
      setErrorMessage("Password is required.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      clearAuth();

      const payload = await apiClient.post<LoginResponse>(
        "/auth/login",
        {
          email: normalizedEmail,
          password,
        },
        {
          organizationId: normalizedOrganizationId,
        }
      );

      const accessToken = payload?.data?.access_token?.trim();
      const tokenType = payload?.data?.token_type?.trim() || "Bearer";
      const userRole = payload?.data?.user?.role?.trim().toLowerCase() || null;

      if (!accessToken) {
        throw new Error("Login succeeded but no access token was returned.");
      }

      setAuthSession({
        accessToken,
        tokenType,
        organizationId: normalizedOrganizationId,
        userEmail: normalizedEmail,
        userRole,
      });

      router.replace(resolvePostLoginRoute(userRole));
      router.refresh();
    } catch (error: unknown) {
      const message =
        error instanceof Error && error.message
          ? error.message
          : "Unable to sign in. Please verify your credentials and try again.";

      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  // 🔥 Prevent flicker while checking session
  if (isCheckingSession) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-4 text-sm text-slate-600 shadow-soft">
          Checking session...
        </div>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">
            Sign in
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Access the Freight Back Office OS operator dashboard.
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit} noValidate>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              Organization ID
            </label>
            <input
              type="text"
              value={organizationId}
              onChange={(e) => setOrganizationId(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
              disabled={isSubmitting}
            />
          </div>

          {errorMessage && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
