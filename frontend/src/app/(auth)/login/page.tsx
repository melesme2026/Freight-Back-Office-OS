"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError, apiClient } from "@/lib/api-client";
import { clearAuth, getAccessToken, getOrganizationId, getUserRole, setAuthSession } from "@/lib/auth";
import { isDriverRole } from "@/lib/rbac";
import { resolvePostLoginRoute } from "@/lib/rbac";
import { AuthNavigationLinks } from "../auth-navigation-links";

type LoginResponse = {
  data?: {
    access_token?: string;
    token_type?: string;
    user?: {
      role?: string;
      organization_id?: string;
    };
  };
  message?: string;
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  } | null;
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

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [showAdvancedLogin, setShowAdvancedLogin] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [organizationOptions, setOrganizationOptions] = useState<LoginOrganizationOption[]>([]);

  // 🔥 Auto-redirect if already logged in
  useEffect(() => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    const userRole = getUserRole();

    if (token && organizationId) {
      router.replace(resolvePostLoginRoute(userRole));
    } else if (token && !organizationId) {
      clearAuth();
      setIsCheckingSession(false);
    } else {
      setIsCheckingSession(false);
    }
  }, [router]);

  const normalizedOrganizationId = useMemo(
    () => normalizeText(organizationId),
    [organizationId]
  );

  const normalizedEmail = useMemo(() => normalizeEmail(email), [email]);

  async function loginWithOrganization(selectedOrganizationId?: string) {
    const normalizedSelectedOrganizationId = normalizeText(selectedOrganizationId ?? normalizedOrganizationId);
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      clearAuth();

      const payload = await apiClient.post<LoginResponse>(
        "/auth/login",
        {
          email: normalizedEmail,
          password,
          ...(normalizedSelectedOrganizationId ? { organization_id: normalizedSelectedOrganizationId } : {}),
        },
        { onUnauthorized: "throw" }
      );

      const accessToken = payload?.data?.access_token?.trim();
      const tokenType = payload?.data?.token_type?.trim() || "Bearer";
      const userRole = payload?.data?.user?.role?.trim().toLowerCase() || null;
      const resolvedOrganizationId = normalizeText(payload?.data?.user?.organization_id ?? "");

      if (!accessToken) {
        throw new Error("Login succeeded but no access token was returned.");
      }
      if (!resolvedOrganizationId) {
        throw new Error("Login succeeded but no organization context was returned.");
      }

      if (isDriverRole(userRole)) {
        throw new Error("This account is a driver account for the selected workspace. Use Driver Login instead.");
      }

      setAuthSession({
        accessToken,
        tokenType,
        organizationId: resolvedOrganizationId,
        userEmail: normalizedEmail,
        userRole,
      });

      router.replace(resolvePostLoginRoute(userRole));
      router.refresh();
    } catch (error: unknown) {
      if (error instanceof ApiClientError) {
        if (error.code === "multiple_organizations") {
          const organizations = Array.isArray(error.details?.organizations)
            ? (error.details.organizations as LoginOrganizationOption[])
            : [];
          setOrganizationOptions(organizations);
          setErrorMessage("This email is linked to multiple workspaces. Select the workspace you want to access.");
        } else if (error.status === 401) {
          setErrorMessage("Invalid email or password.");
        } else {
          setErrorMessage(error.message || "Unable to sign in. Please verify your credentials and try again.");
        }
      } else {
        setErrorMessage("Unable to sign in. Please verify your credentials and try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

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

    setOrganizationOptions([]);
    await loginWithOrganization();
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
          <p className="mt-2 text-xs text-slate-500">
            Driver account? Use Driver Login. Driver accounts are staff-invited only.
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit} noValidate>
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

          {organizationOptions.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="mb-2 text-sm font-medium text-slate-800">
                This email is linked to multiple workspaces. Select the workspace you want to access.
              </p>
              <div className="space-y-2">
                {organizationOptions.map((option) => (
                  <button
                    key={option.organization_id}
                    type="button"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-left text-sm hover:border-brand-500"
                    disabled={isSubmitting}
                    onClick={async () => {
                      setOrganizationId(option.organization_id);
                      if (option.role === "driver") {
                        setErrorMessage(
                          "This account is a driver account for the selected workspace. Use Driver Login instead."
                        );
                        return;
                      }
                      setShowAdvancedLogin(true);
                      setErrorMessage(null);
                      await loginWithOrganization(option.organization_id);
                    }}
                  >
                    {getWorkspaceLabel(option)}
                  </button>
                ))}
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <button
              type="button"
              className="text-xs font-semibold text-slate-700 hover:text-slate-900"
              onClick={() => setShowAdvancedLogin((current) => !current)}
            >
              {showAdvancedLogin ? "Hide" : "Show"} Advanced / Admin login
            </button>
            {showAdvancedLogin ? (
              <div className="mt-3">
                <label className="mb-2 block text-xs font-medium text-slate-700">Organization ID override</label>
                <input
                  type="text"
                  value={organizationId}
                  onChange={(e) => setOrganizationId(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
                  placeholder="Optional: only for multi-org/admin debugging"
                  disabled={isSubmitting}
                />
              </div>
            ) : null}
          </div>
        </form>
        <AuthNavigationLinks
          secondaryLinks={[
            { href: "/signup", label: "Create account" },
          ]}
        />
      </section>
    </main>
  );
}
