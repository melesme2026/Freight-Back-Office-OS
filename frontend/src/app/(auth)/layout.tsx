import { BrandLogo } from "@/components/ui/BrandLogo";

export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <main className="min-h-screen brand-page-shell">
      <div className="mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-6 py-10 lg:grid-cols-[0.95fr_1.05fr] lg:py-16">
        <section className="hidden lg:block">
          <div className="max-w-xl rounded-[2rem] border border-white/10 bg-brand-950 p-8 text-white shadow-operational">
            <BrandLogo variant="operatingSystem" tone="dark" className="h-14 w-auto" priority />
            <p className="mt-10 text-xs font-extrabold uppercase tracking-[0.28em] text-route-200">Trusted freight finance operations</p>
            <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-white">
              A calmer control plane for billing packets, factoring, and cash-flow work.
            </h1>
            <div className="mt-8 grid gap-3 text-sm text-slate-200">
              {[
                "Route-aware document intake",
                "Invoice and packet readiness visibility",
                "Role-based driver and staff workflows",
              ].map((item) => (
                <div key={item} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </section>
        <div className="flex items-center justify-center">{children}</div>
      </div>
    </main>
  );
}
