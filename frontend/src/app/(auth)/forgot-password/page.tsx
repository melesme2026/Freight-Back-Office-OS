"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { AuthNavigationLinks } from "../auth-navigation-links";

type ForgotPasswordResponse = {
  data?: {
    reset_requested?: boolean;
    reset_token?: string;
    reset_url?: string;
    email_status?: string;
  };
};

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [resetUrl, setResetUrl] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!email.trim()) {
      setErrorMessage("Email is required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      setResetToken(null);
      setResetUrl(null);
      setIsSuccess(false);

      const payload = await apiClient.post<ForgotPasswordResponse>("/auth/request-password-reset", {
        email: email.trim().toLowerCase(),
      });

      setIsSuccess(true);
      if (payload?.data?.reset_token) {
        setResetToken(payload.data.reset_token);
      }
      if (payload?.data?.reset_url) {
        setResetUrl(payload.data.reset_url);
      }
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to request password reset.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
      <h1 className="text-2xl font-bold text-slate-950">Forgot Password</h1>
      <p className="mt-2 text-sm text-slate-600">Request a password reset token for your account.</p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
        <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Account email" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting} />

        {errorMessage ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}

        {isSuccess ? (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Reset request accepted. {resetToken ? "Use the token below to complete reset." : "If your account exists, continue with your reset token."}
          </div>
        ) : null}

        {resetToken ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-700 break-all">
            <div className="font-semibold text-slate-900">Reset token</div>
            <div className="mt-1">{resetToken}</div>
            <Link href={`/reset-password?token=${encodeURIComponent(resetToken)}`} className="mt-2 inline-block font-semibold text-brand-700">
              Continue to Reset Password →
            </Link>
          </div>
        ) : null}

        {!resetToken && resetUrl ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-700 break-all">
            <div className="font-semibold text-slate-900">Reset link</div>
            <a href={resetUrl} className="mt-1 inline-block font-semibold text-brand-700">
              Continue to Reset Password →
            </a>
          </div>
        ) : null}

        <button type="submit" disabled={isSubmitting} className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
          {isSubmitting ? "Requesting..." : "Request reset"}
        </button>
      </form>

      <AuthNavigationLinks
        secondaryLinks={[
          { href: "/reset-password", label: "Reset password" },
        ]}
      />
    </section>
  );
}
