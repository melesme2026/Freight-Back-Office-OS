"use client";

import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { AuthNavigationLinks } from "../auth-navigation-links";

function normalizeActivationToken(value: string): string {
  return value.replace(/\s+/g, "").trim();
}

function ActivateAccountPageContent() {
  const searchParams = useSearchParams();
  const tokenFromQuery = useMemo(() => searchParams.get("token") ?? "", [searchParams]);

  const [token, setToken] = useState(tokenFromQuery);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    if (tokenFromQuery.trim()) {
      setToken(tokenFromQuery);
    }
  }, [tokenFromQuery]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedToken = normalizeActivationToken(token);

    if (!normalizedToken || !password || !confirmPassword) {
      setErrorMessage("Activation token and password are required.");
      return;
    }

    if (password.length < 8) {
      setErrorMessage("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      setIsSuccess(false);

      await apiClient.post("/auth/activate-account", {
        token: normalizedToken,
        password,
      }, {
        authMode: "none",
        onUnauthorized: "throw",
      });

      setIsSuccess(true);
      setPassword("");
      setConfirmPassword("");
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to activate account.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
      <h1 className="text-2xl font-bold text-slate-950">Activate Account</h1>
      <p className="mt-2 text-sm text-slate-600">Complete your invited account setup by setting your password.</p>
      <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
        Activation requires a valid invite from your operations team. For driver access, staff must first create your driver profile and then send an invite to the same email address.
      </div>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
        {tokenFromQuery.trim() ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
            Activation token detected from your invite link.
          </div>
        ) : (
          <textarea value={token} onChange={(event) => setToken(event.target.value)} placeholder="Activation token" className="h-24 w-full rounded-xl border border-slate-300 px-4 py-3 text-xs" disabled={isSubmitting || isSuccess} />
        )}
        <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Create password" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting || isSuccess} />
        <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Confirm password" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting || isSuccess} />

        {errorMessage ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}
        {isSuccess ? (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Account activated. Use Driver Login for driver accounts, or Staff Login for operator accounts.
          </div>
        ) : null}

        <button type="submit" disabled={isSubmitting || isSuccess} className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
          {isSubmitting ? "Activating..." : "Activate account"}
        </button>
      </form>

      <AuthNavigationLinks />
    </section>
  );
}

export default function ActivateAccountPage() {
  return (
    <Suspense
      fallback={
        <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
          <p className="text-sm text-slate-600">Loading activation form...</p>
        </section>
      }
    >
      <ActivateAccountPageContent />
    </Suspense>
  );
}
