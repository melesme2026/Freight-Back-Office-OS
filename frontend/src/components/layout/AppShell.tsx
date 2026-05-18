import Link from "next/link";
import { ReactNode } from "react";

import { BrandLogo } from "@/components/ui/BrandLogo";

type AppShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/command-center", label: "Command Center" },
  { href: "/dashboard/loads", label: "Loads" },
  { href: "/dashboard/review-queue", label: "Review Queue" },
  { href: "/dashboard/customers", label: "Customers" },
  { href: "/dashboard/brokers", label: "Brokers" },
  { href: "/dashboard/billing", label: "Billing" },
  { href: "/dashboard/factoring", label: "Factoring" },
  { href: "/dashboard/support", label: "Support" },
] as const;

export function AppShell({ title, subtitle, children }: AppShellProps) {
  return (
    <div className="min-h-screen brand-page-shell text-slate-900">
      <div className="border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/dashboard" aria-label="Adwa Freight OS dashboard">
            <BrandLogo variant="operatingSystem" tone="light" className="h-11 w-auto" />
          </Link>

          <nav className="hidden gap-5 md:flex">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm font-semibold text-slate-600 hover:text-brand-950"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">{title}</h1>
          {subtitle ? <p className="mt-2 text-sm leading-6 text-slate-600">{subtitle}</p> : null}
        </header>

        {children}
      </div>
    </div>
  );
}
