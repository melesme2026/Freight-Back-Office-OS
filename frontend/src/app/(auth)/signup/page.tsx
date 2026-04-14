"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { clearAuth, getAccessToken, getOrganizationId, getUserRole, setAuthSession } from "@/lib/auth";
import { resolvePostLoginRoute } from "@/lib/rbac";

type SignupResponse = {
  data?: {
    access_token?: string;
    token_type?: string;
    user?: {
      organization_id?: string;
      role?: string;
      email?: string;
    };
  };
};

export default function SignupPage() {
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    const userRole = getUserRole();

    if (token && organizationId) {
      router.replace(resolvePostLoginRoute(userRole));
      return;
    }

    if (token && !organizationId) {
      clearAuth();
    }

    setIsCheckingSession(false);
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!fullName.trim() || !organizationName.trim() || !email.trim() || !password || !confirmPassword) {
      setErrorMessage("All fields are required.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      clearAuth();

      const payload = await apiClient.post<SignupResponse>("/auth/signup", {
        full_name: fullName.trim(),
        organization_name: organizationName.trim(),
        email: email.trim().toLowerCase(),
        password,
        confirm_password: confirmPassword,
      });

      const accessToken = payload?.data?.access_token?.trim();
      const tokenType = payload?.data?.token_type?.trim() || "Bearer";
      const role = payload?.data?.user?.role?.trim().toLowerCase() || "owner";
      const organizationId = payload?.data?.user?.organization_id?.trim();
      const normalizedEmail = payload?.data?.user?.email?.trim().toLowerCase() || email.trim().toLowerCase();

      if (!accessToken || !organizationId) {
        throw new Error("Signup succeeded but session details were incomplete.");
      }

      setAuthSession({
        accessToken,
        tokenType,
        organizationId,
        userEmail: normalizedEmail,
        userRole: role,
      });

      router.replace(resolvePostLoginRoute(role));
      router.refresh();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to complete signup.");
    } finally {
      setIsSubmitting(false);
    }
  }

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
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
      <h1 className="text-2xl font-bold text-slate-950">Create Staff Account</h1>
      <p className="mt-2 text-sm text-slate-600">
        Create your organization workspace and owner account.
      </p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
        <input type="text" placeholder="Full name" value={fullName} onChange={(event) => setFullName(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting} />
        <input type="text" placeholder="Company / organization" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting} />
        <input type="email" placeholder="Work email" value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting} />
        <input type="password" placeholder="Password (min 8 chars)" value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting} />
        <input type="password" placeholder="Confirm password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isSubmitting} />

        {errorMessage ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div>
        ) : null}

        <button type="submit" disabled={isSubmitting} className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
          {isSubmitting ? "Creating account..." : "Create account"}
        </button>
      </form>

      <div className="mt-4 text-xs text-slate-600">
        Already have an account? <Link href="/login" className="font-semibold text-brand-700">Sign in</Link>
      </div>
    </section>
  );
}
