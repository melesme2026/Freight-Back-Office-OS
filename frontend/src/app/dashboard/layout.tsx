"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";

import {
  clearAuth,
  getAccessToken,
  getOrganizationId,
  getUserEmail,
  getUserRole,
} from "@/lib/auth";
import { canAccessDashboard } from "@/lib/rbac";

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
  { href: "/dashboard/drivers", label: "Drivers" },
  { href: "/dashboard/billing", label: "Billing" },
  { href: "/dashboard/onboarding", label: "Onboarding" },
  { href: "/dashboard/notifications", label: "Notifications" },
  { href: "/dashboard/support", label: "Support" },
  { href: "/dashboard/settings", label: "Settings" },
];

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

  const accessToken = getAccessToken();
  const organizationId = getOrganizationId();
  const userRole = getUserRole();
  const userEmail = getUserEmail();

  useEffect(() => {
    if (!accessToken || !organizationId) {
      router.replace("/login");
      return;
    }

    if (!canAccessDashboard(userRole)) {
      router.replace("/driver-portal");
    }
  }, [accessToken, organizationId, userRole, router]);

  const pageTitle = useMemo(() => {
    const activeItem = NAV_ITEMS.find((item) => isActivePath(pathname, item.href));
    return activeItem?.label ?? "Dashboard";
  }, [pathname]);

  function handleLogout() {
    clearAuth();
    router.replace("/");
  }

  if (!accessToken || !organizationId || !canAccessDashboard(userRole)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 text-sm text-slate-600 shadow-soft">
          Redirecting...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white xl:flex xl:flex-col">
          <div className="border-b border-slate-200 px-6 py-5">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">
              Freight Back Office OS
            </div>
            <div className="mt-2 text-lg font-bold text-slate-950">Dashboard</div>
            <div className="mt-3 space-y-1 text-xs text-slate-500">
              <div>{userEmail ?? "Signed-in user"}</div>
              <div className="break-all">Org: {organizationId}</div>
            </div>
            <Link
              href="/"
              className="mt-3 inline-flex text-xs font-semibold text-brand-700 hover:text-brand-800"
            >
              ← Back to landing
            </Link>
          </div>

          <nav className="flex-1 space-y-1 px-3 py-4">
            {NAV_ITEMS.map((item) => {
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
            <div className="flex items-center justify-between px-6 py-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">
                  Operations Workspace
                </div>
                <h1 className="mt-1 text-xl font-bold text-slate-950">{pageTitle}</h1>
              </div>

              <div className="flex items-center gap-3">
                <div className="hidden text-right md:block">
                  <div className="text-sm font-medium text-slate-900">
                    {userEmail ?? "Signed-in user"}
                  </div>
                  <div className="text-xs text-slate-500">Organization active</div>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="xl:hidden rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Log Out
                </button>
              </div>
            </div>

            <div className="flex gap-2 overflow-x-auto border-t border-slate-100 px-4 py-3 xl:hidden">
              {NAV_ITEMS.map((item) => {
                const active = isActivePath(pathname, item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`whitespace-nowrap rounded-full px-3 py-2 text-xs font-semibold transition ${
                      active
                        ? "bg-brand-600 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </header>

          <div className="min-w-0 flex-1">{children}</div>
        </div>
      </div>
    </div>
  );
}
