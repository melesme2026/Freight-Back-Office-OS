"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@demo-freight.com");
  const [password, setPassword] = useState("ChangeMe123!");
  const [organizationId, setOrganizationId] = useState(
    "00000000-0000-0000-0000-000000000001"
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);

    try {
      router.push("/dashboard");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-950">
          Sign in
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Access the Freight Back Office OS operator dashboard.
        </p>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
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
          />
        </div>

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