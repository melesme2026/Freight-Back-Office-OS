"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearAuth, getAuthSession, onAuthChanged, type AuthSession } from "@/lib/auth";
import DriverMobileRuntime from "@/components/driver/DriverMobileRuntime";
import { canAccessDriverPortal } from "@/lib/rbac";

const DRIVER_NAV = [
  { href: "/driver-portal", label: "Overview" },
  { href: "/driver-portal/loads", label: "Loads" },
  { href: "/driver-portal/uploads", label: "Uploads" },
  { href: "/driver-portal/support", label: "Support" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/driver-portal") {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function DriverPortalLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const router = useRouter();
  const pathname = usePathname();
  const [isHydrated, setIsHydrated] = useState(false);

  const [session, setSession] = useState<AuthSession>(() => ({
    accessToken: null,
    tokenType: "Bearer",
    organizationId: null,
    userEmail: null,
    userRole: null,
    driverId: null,
  }));

  useEffect(() => {
    setSession(getAuthSession());
    setIsHydrated(true);
    return onAuthChanged(() => setSession(getAuthSession()));
  }, []);

  const hasDriverAccess = Boolean(
    session.accessToken && session.organizationId && canAccessDriverPortal(session.userRole)
  );

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (!session.accessToken || !session.organizationId) {
      router.replace("/driver-login?session=expired");
      return;
    }

    if (!canAccessDriverPortal(session.userRole)) {
      router.replace("/dashboard");
      return;
    }

    if (pathname.startsWith("/driver-portal/billing")) {
      router.replace("/driver-portal/loads");
    }
  }, [isHydrated, pathname, router, session.accessToken, session.organizationId, session.userRole]);

  function handleLogout() {
    clearAuth();
    router.replace("/driver-login?reason=logged_out");
  }

  if (!isHydrated || !hasDriverAccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 text-sm text-slate-600 shadow-soft">
          Redirecting...
        </div>
      </div>
    );
  }

  return (
    <div className="safe-page min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">Driver Portal</div>
            <div className="text-sm text-slate-500">{session.userEmail ?? "Authenticated user"}</div>
            <Link
              href="/"
              className="mt-1 inline-flex text-xs font-semibold text-brand-700 hover:text-brand-800"
            >
              ← Back to landing
            </Link>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="touch-target rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Log Out
          </button>
        </div>
        <nav aria-label="Driver portal sections" className="mobile-scroll-area mx-auto flex max-w-6xl gap-2 overflow-x-auto px-4 pb-3 sm:px-6">
          {DRIVER_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`touch-target inline-flex shrink-0 items-center whitespace-nowrap rounded-full px-3 py-2 text-xs font-semibold transition ${
                isActive(pathname, item.href)
                  ? "bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>
      <DriverMobileRuntime />
      {children}
    </div>
  );
}
