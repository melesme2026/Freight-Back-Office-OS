"use client";

import { SESSION_EXPIRED_MESSAGE } from "@/lib/notification-copy";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError, apiClient } from "@/lib/api-client";
import { clearAuth, getAccessToken, getOrganizationId, getUserRole, setAuthSession } from "@/lib/auth";
import { isDriverRole, resolvePostLoginRoute } from "@/lib/rbac";
import { AuthNavigationLinks } from "../(auth)/auth-navigation-links";
import { BrandLogo } from "@/components/ui/BrandLogo";

type LoginResponse = {
  data?: {
    access_token?: string;
    token_type?: string;
    user?: {
      role?: string;
      organization_id?: string;
      driver_id?: string;
    };
  };
};

type LoginOrganizationOption = {
  organization_id: string;
  organization_name?: string;
  role?: string;
};

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

function getWorkspaceLabel(option: LoginOrganizationOption): string {
  const explicitName = normalizeText(option.organization_name ?? "");
  if (explicitName) {
    return explicitName;
  }
  const organizationId = normalizeText(option.organization_id);
  const suffix = organizationId.slice(-4);
  return suffix ? `Workspace ending in ${suffix}` : "Workspace";
}

export default function DriverLoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [organizationOptions, setOrganizationOptions] = useState<LoginOrganizationOption[]>([]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const reason = params.get("reason");
    const session = params.get("session");
    if (reason === "logged_out") {
      setStatusMessage("You have been signed out.");
    } else if (session === "expired") {
      setErrorMessage(SESSION_EXPIRED_MESSAGE);
    }
    setSessionNotice(null);

    const token = getAccessToken();
    const organizationId = getOrganizationId();
    const userRole = getUserRole();

    if (token && organizationId && isDriverRole(userRole)) {
      router.replace("/driver-portal");
    } else if (token && organizationId) {
      setSessionNotice("You are signed in to the staff app. To use the Driver portal, sign out of the staff session or open a private browser window.");
      setIsCheckingSession(false);
    } else if (token && !organizationId) {
      clearAuth();
      setIsCheckingSession(false);
    } else {
      setIsCheckingSession(false);
    }
  }, [router]);

  const normalizedEmail = useMemo(() => normalizeEmail(email), [email]);

  function handleStaffLogout() {
    clearAuth();
    setSessionNotice(null);
    setErrorMessage(null);
    setStatusMessage("You have been signed out.");
    setIsCheckingSession(false);
  }

  async function loginWithOrganization(selectedOrganizationId?: string) {
    const normalizedSelectedOrganizationId = normalizeText(selectedOrganizationId ?? "");
    setIsSubmitting(true);
    setErrorMessage(null);
    setStatusMessage(null);

    try {
      clearAuth();
      const payload = await apiClient.post<LoginResponse>(
        "/auth/driver-login",
        {
          email: normalizedEmail,
          password,
          ...(normalizedSelectedOrganizationId ? { organization_id: normalizedSelectedOrganizationId } : {}),
        },
        { onUnauthorized: "throw", timeoutMs: 10_000 }
      );

      const accessToken = payload?.data?.access_token?.trim();
      const tokenType = payload?.data?.token_type?.trim() || "Bearer";
      const userRole = payload?.data?.user?.role?.trim().toLowerCase() || null;
      const resolvedOrganizationId = normalizeText(payload?.data?.user?.organization_id ?? "");
      const resolvedDriverId = normalizeText(payload?.data?.user?.driver_id ?? "");

      if (!accessToken) {
        throw new Error("Login succeeded but no access token was returned.");
      }
      if (!resolvedOrganizationId) {
        throw new Error("Login succeeded but no organization context was returned.");
      }

      if (!isDriverRole(userRole)) {
        throw new Error("This account uses the Staff workspace. Switch to the staff sign-in page to continue.");
      }

      setAuthSession({
        accessToken,
        tokenType,
        organizationId: resolvedOrganizationId,
        userEmail: normalizedEmail,
        userRole,
        driverId: resolvedDriverId || null,
      });

      router.replace("/driver-portal");
      router.refresh();
    } catch (error: unknown) {
      if (error instanceof ApiClientError) {
        if (error.code === "multiple_organizations") {
          const organizations = Array.isArray(error.details?.organizations)
            ? (error.details.organizations as LoginOrganizationOption[])
            : [];
          setOrganizationOptions(organizations);
          setErrorMessage("This email is linked to multiple workspaces. Choose which workspace to access.");
        } else if (error.status === 403) {
          setErrorMessage("Driver account is not activated. Please contact your dispatcher.");
        } else if (error.status === 401) {
          setErrorMessage("Driver account not found or password is incorrect.");
        } else if (error.code === "client_timeout") {
          setErrorMessage("Driver login is taking longer than expected. Check your connection and try again.");
        } else if (error.message === "Use Staff Login") {
          setErrorMessage("This account uses the Staff workspace. Switch to the staff sign-in page to continue.");
        } else {
          setErrorMessage(error.message || "Sign-in could not be completed. Verify your credentials and try again.");
        }
      } else if (error instanceof Error && (error.message === "Use Staff Login" || error.message === "This account uses the Staff workspace. Switch to the staff sign-in page to continue.")) {
        setErrorMessage("This account uses the Staff workspace. Switch to the staff sign-in page to continue.");
      } else {
        setErrorMessage("Sign-in could not be completed. Verify your credentials and try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    if (!normalizedEmail || !isValidEmail(normalizedEmail)) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!password) {
      setErrorMessage("Password is required.");
      return;
    }

    setOrganizationOptions([]);
    await loginWithOrganization();
  }

  if (isCheckingSession) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-4 text-sm text-slate-600 shadow-soft">
          Checking session…
        </div>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center brand-page-shell px-6 py-10">
      <section className="w-full max-w-md rounded-[1.75rem] border border-slate-200/90 bg-white/95 p-6 shadow-operational backdrop-blur sm:p-8">
        <div className="mb-7">
          <BrandLogo variant="operatingSystem" tone="light" className="mb-7 h-12 w-auto" priority />
          <p className="ops-eyebrow">Driver Portal</p>
          <h1 className="mt-3 text-2xl font-extrabold tracking-tight text-slate-950">Driver sign in</h1>
          <p className="mt-2 text-sm text-slate-600">Access assigned loads, document uploads, and dispatcher updates.</p>
          <p className="mt-2 text-xs text-slate-500">
            Driver accounts are invite-only. If you were not invited by staff, contact your dispatcher.
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit} noValidate>
          <div>
            <label className="brand-label">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="brand-input" disabled={isSubmitting} />
          </div>

          <div>
            <label className="brand-label">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="brand-input" disabled={isSubmitting} />
          </div>

          {sessionNotice && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p>{sessionNotice}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleStaffLogout}
                  className="rounded-lg bg-amber-700 px-3 py-2 text-xs font-bold text-white hover:bg-amber-800"
                >
                  Sign out and use the Driver portal
                </button>
                <button
                  type="button"
                  onClick={() => router.replace(resolvePostLoginRoute(getUserRole()))}
                  className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-100"
                >
                  Return to staff app
                </button>
              </div>
            </div>
          )}

          {statusMessage && <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{statusMessage}</div>}

          {errorMessage && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{errorMessage}</div>}

          {organizationOptions.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <h2 className="mb-1 text-sm font-semibold text-slate-900">Select workspace</h2>
              <p className="mb-2 text-sm text-slate-700">
                This email is linked to multiple workspaces. Choose which workspace to access.
              </p>
              <div className="space-y-2">
                {organizationOptions.map((option) => (
                  <button
                    key={option.organization_id}
                    type="button"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-left text-sm hover:border-brand-500"
                    disabled={isSubmitting}
                    onClick={async () => {
                      if (option.role && option.role !== "driver") {
                        setErrorMessage("This account uses the Staff workspace. Switch to the staff sign-in page to continue.");
                        return;
                      }
                      setErrorMessage(null);
                      await loginWithOrganization(option.organization_id);
                    }}
                  >
                    <div className="font-semibold text-slate-900">{getWorkspaceLabel(option)}</div>
                    <div className="text-xs text-slate-500">Role: {(option.role ?? "driver").toString()}</div>
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="mt-3 text-xs font-semibold text-slate-700 underline"
                onClick={() => {
                  setOrganizationOptions([]);
                  setErrorMessage(null);
                }}
                disabled={isSubmitting}
              >
                Back / Edit email
              </button>
            </div>
          )}

          <button type="submit" disabled={isSubmitting} className="brand-button-primary w-full">
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <AuthNavigationLinks
          secondaryLinks={[
            { href: "/activate-account", label: "Activate invited account" },
          ]}
        />
      </section>
    </main>
  );
}
