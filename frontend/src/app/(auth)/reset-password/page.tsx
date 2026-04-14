"use client";

import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { AuthNavigationLinks } from "../auth-navigation-links";

function ResetPasswordPageContent() {
  const searchParams = useSearchParams();
  const tokenFromQuery = useMemo(() => searchParams.get("token") ?? "", [searchParams]);

  const [token, setToken] = useState(tokenFromQuery);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token.trim() || !newPassword || !confirmPassword) {
      setErrorMessage("Token and password fields are required.");
      return;
    }

    if (newPassword.length < 8) {
      setErrorMessage("New password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      setIsSuccess(false);

      await apiClient.post("/auth/reset-password", {
        token: token.trim(),
        new_password: newPassword,
      });

      setIsSuccess(true);
      setNewPassword("");
      setConfirmPassword("");
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to reset password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
      <h1 className="text-2xl font-bold text-slate-950">Reset Password</h1>
      <p className="mt-2 text-sm text-slate-600">Set a new password using your reset token.</p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
        <textarea value={token} onChange={(event) => setToken(event.target.value)} placeholder="Reset token" className="h-24 w-full rounded-xl border border-slate-300 px-4 py-3 text-xs" disabled={isSubmitting || isSuccess} />
        <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="New password" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting || isSuccess} />
        <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Confirm new password" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting || isSuccess} />

        {errorMessage ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}
        {isSuccess ? (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Password reset complete. You can now sign in with your new password.
          </div>
        ) : null}

        <button type="submit" disabled={isSubmitting || isSuccess} className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
          {isSubmitting ? "Resetting..." : "Reset password"}
        </button>
      </form>

      <AuthNavigationLinks
        secondaryLinks={[
          { href: "/login", label: "Back to login" },
        ]}
      />
    </section>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
          <p className="text-sm text-slate-600">Loading reset form...</p>
        </section>
      }
    >
      <ResetPasswordPageContent />
    </Suspense>
  );
}
