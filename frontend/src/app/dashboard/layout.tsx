"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  clearAuth,
  getAuthSession,
  onAuthChanged,
  type AuthSession,
} from "@/lib/auth";
import { canAccessDashboardPath, canManageLeadPipeline } from "@/lib/rbac";

type NavItem = {
  href: Route;
  label: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/loads", label: "Loads" },
  { href: "/dashboard/review-queue", label: "Review Queue" },
  { href: "/dashboard/documents", label: "Documents" },
  { href: "/dashboard/customers", label: "Customers" },
  { href: "/dashboard/brokers", label: "Brokers" },
  { href: "/dashboard/drivers", label: "Drivers" },
  { href: "/dashboard/team", label: "Team" },
  { href: "/dashboard/leads", label: "Leads" },
  { href: "/dashboard/billing", label: "Billing" },
  { href: "/dashboard/factoring", label: "Factoring" },
  { href: "/dashboard/money", label: "Money" },
  { href: "/dashboard/accounting", label: "Accounting" },
  { href: "/dashboard/onboarding", label: "Onboarding" },
  { href: "/dashboard/notifications", label: "Notifications" },
  { href: "/dashboard/support", label: "Support" },
  { href: "/dashboard/settings", label: "Settings" },
];

function canShowNavItem(item: NavItem, role: string | null): boolean {
  if (item.href === "/dashboard/leads") {
    return canManageLeadPipeline(role);
  }

  return canAccessDashboardPath(role, item.href);
}

function isActivePath(pathname: string, href: string): boolean {
  if (href === "/dashboard") {
    return pathname === "/dashboard";
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [session, setSession] = useState<AuthSession>(() => ({
    accessToken: null,
    tokenType: "Bearer",
    organizationId: null,
    userEmail: null,
    userRole: null,
    driverId: null,
  }));
  const [accessDenied, setAccessDenied] = useState(false);

  useEffect(() => {
    setMounted(true);
    setSession(getAuthSession());
    return onAuthChanged(() => setSession(getAuthSession()));
  }, []);

  useEffect(() => {
    if (!mounted) {
      return;
    }

    if (!session.accessToken || !session.organizationId) {
      router.replace("/login?session=expired");
      return;
    }

    if (!canAccessDashboardPath(session.userRole, pathname)) {
      if (session.userRole === "driver") {
        router.replace("/driver-portal");
        return;
      }
      setAccessDenied(true);
      return;
    }

    setAccessDenied(false);
  }, [mounted, pathname, router, session.accessToken, session.organizationId, session.userRole]);

  const pageTitle = useMemo(() => {
    const activeItem = NAV_ITEMS.find((item) => isActivePath(pathname, item.href));
    return activeItem?.label ?? "Dashboard";
  }, [pathname]);

  function handleLogout() {
    clearAuth();
    router.replace("/");
  }

  if (!mounted) {
    return null;
  }

  if (!session.accessToken || !session.organizationId) {
    return null;
  }

  if (accessDenied || !canAccessDashboardPath(session.userRole, pathname)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="max-w-md rounded-2xl border border-amber-200 bg-white p-6 text-center shadow-soft">
          <h1 className="text-lg font-bold text-slate-950">Access denied</h1>
          <p className="mt-2 text-sm text-slate-600">Your account does not have permission to view this dashboard area.</p>
          <button
            type="button"
            onClick={() => router.replace("/dashboard")}
            className="mt-4 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Back to dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="safe-page min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white xl:flex xl:flex-col">
          <div className="border-b border-slate-200 px-6 py-5">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">
              Freight Back Office OS
            </div>
            <div className="mt-2 text-lg font-bold text-slate-950">Dashboard</div>
            <div className="mt-3 space-y-1 text-xs text-slate-500">
              <div>{session.userEmail ?? "Signed-in user"}</div>
              <div className="break-all">Org: {session.organizationId}</div>
            </div>
            <Link
              href="/"
              className="mt-3 inline-flex text-xs font-semibold text-brand-700 hover:text-brand-800"
            >
              ← Back to landing
            </Link>
          </div>

          <nav className="flex-1 space-y-1 px-3 py-4">
            {NAV_ITEMS.filter((item) => canShowNavItem(item, session.userRole)).map((item) => {
              const active = isActivePath(pathname, item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-xl px-3 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-slate-200 p-3">
            <button
              type="button"
              onClick={handleLogout}
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Log Out
            </button>
          </div>
        </aside>

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="border-b border-slate-200 bg-white">
            <div className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">
                  Operations Workspace
                </div>
                <p className="mt-1 text-xl font-bold text-slate-950">{pageTitle}</p>
              </div>

              <div className="flex w-full items-center justify-between gap-3 sm:w-auto">
                <div className="hidden text-right md:block">
                  <div className="text-sm font-medium text-slate-900">
                    {session.userEmail ?? "Signed-in user"}
                  </div>
                  <div className="text-xs text-slate-500">Organization active</div>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="touch-target xl:hidden rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Log Out
                </button>
              </div>
            </div>

            <nav aria-label="Dashboard sections" className="mobile-scroll-area flex gap-2 overflow-x-auto border-t border-slate-100 px-4 py-3 xl:hidden">
              {NAV_ITEMS.filter((item) => canShowNavItem(item, session.userRole)).map((item) => {
                const active = isActivePath(pathname, item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`touch-target inline-flex shrink-0 items-center whitespace-nowrap rounded-full px-3 py-2 text-xs font-semibold transition ${
                      active
                        ? "bg-brand-600 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </header>

          <main className="min-w-0 flex-1 overflow-x-clip">{children}</main>
        </div>
      </div>
    </div>
  );
}
