import Link from "next/link";
import { ReactNode } from "react";

type AppShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/loads", label: "Loads" },
  { href: "/dashboard/review-queue", label: "Review Queue" },
  { href: "/dashboard/customers", label: "Customers" },
  { href: "/dashboard/billing", label: "Billing" },
  { href: "/dashboard/support", label: "Support" },
] as const;

export function AppShell({ title, subtitle, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/dashboard" className="text-lg font-bold text-slate-950">
            Freight Back Office OS
          </Link>

          <nav className="hidden gap-5 md:flex">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm font-medium text-slate-600 hover:text-slate-950"
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