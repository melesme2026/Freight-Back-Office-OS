"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type LoginResponse = {
  data?: {
    access_token?: string;
    token_type?: string;
  };
  message?: string;
};

const DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001";

function getApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (value && value.length > 0) {
    return value.replace(/\/+$/, "");
  }

  return "/api/v1";
}

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationId, setOrganizationId] = useState(DEFAULT_ORGANIZATION_ID);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const normalizedEmail = email.trim().toLowerCase();
    const normalizedOrganizationId = organizationId.trim();
    const normalizedPassword = password;

    if (!normalizedOrganizationId) {
      setErrorMessage("Organization ID is required.");
      return;
    }

    if (!normalizedEmail) {
      setErrorMessage("Email is required.");
      return;
    }

    if (!normalizedPassword) {
      setErrorMessage("Password is required.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/auth/login`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Organization-Id": normalizedOrganizationId,
        },
        body: JSON.stringify({
          email: normalizedEmail,
          password: normalizedPassword,
        }),
      });

      let payload: LoginResponse | null = null;

      try {
        payload = (await response.json()) as LoginResponse;
      } catch {
        payload = null;
      }

      if (!response.ok) {
        const message =
          payload?.message?.trim() ||
          "Unable to sign in. Please verify your credentials and try again.";
        throw new Error(message);
      }

      const accessToken = payload?.data?.access_token?.trim();
      const tokenType = payload?.data?.token_type?.trim() || "Bearer";

      if (!accessToken) {
        throw new Error("Login succeeded but no access token was returned.");
      }

      window.localStorage.setItem("fbos_access_token", accessToken);
      window.localStorage.setItem("fbos_token_type", tokenType);
      window.localStorage.setItem("fbos_organization_id", normalizedOrganizationId);
      window.localStorage.setItem("fbos_user_email", normalizedEmail);

      router.push("/dashboard");
      router.refresh();
    } catch (error) {
      const message =
        error instanceof Error && error.message
          ? error.message
          : "An unexpected error occurred while signing in.";
      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-950">Sign in</h1>
        <p className="mt-2 text-sm text-slate-600">
          Access the Freight Back Office OS operator dashboard.
        </p>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit} noValidate>
        <div>
          <label
            htmlFor="organizationId"
            className="mb-2 block text-sm font-medium text-slate-700"
          >
            Organization ID
          </label>
          <input
            id="organizationId"
            type="text"
            value={organizationId}
            onChange={(e) => setOrganizationId(e.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 transition placeholder:text-slate-400 focus:border-brand-500"
            placeholder="Organization UUID"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            disabled={isSubmitting}
          />
        </div>

        <div>
          <label
            htmlFor="email"
            className="mb-2 block text-sm font-medium text-slate-700"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 transition placeholder:text-slate-400 focus:border-brand-500"
            placeholder="you@example.com"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            disabled={isSubmitting}
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="mb-2 block text-sm font-medium text-slate-700"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 transition placeholder:text-slate-400 focus:border-brand-500"
            placeholder="Enter your password"
            disabled={isSubmitting}
          />
        </div>

        {errorMessage ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </section>
  );
}