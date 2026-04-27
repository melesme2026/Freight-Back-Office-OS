import { appConfig } from "@/lib/config";

export function BillingModeNotice() {
  if (appConfig.billing.mode === "live") {
    return (
      <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
        Live billing mode is active. Subscription checkout and account billing should follow your Stripe configuration.
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
      Pilot access is active. Your team can use the platform now, and billing is activated after onboarding.
    </section>
  );
}
