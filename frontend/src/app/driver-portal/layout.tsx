"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearAuth, getAuthSession, onAuthChanged, type AuthSession } from "@/lib/auth";
import { AccessState } from "@/components/routing/AccessState";
import DriverMobileRuntime from "@/components/driver/DriverMobileRuntime";
import { canAccessDriverPortal } from "@/lib/rbac";
import { BrandLogo } from "@/components/ui/BrandLogo";

const DRIVER_NAV = [
  { href: "/driver-portal", label: "Overview", helper: "Next action" },
  { href: "/driver-portal/loads", label: "Loads", helper: "Assigned work" },
  { href: "/driver-portal/uploads", label: "Uploads", helper: "Send POD/BOL" },
  { href: "/driver-portal/support", label: "Support", helper: "Get help" },
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

  if (!isHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 text-sm text-slate-600 shadow-soft">
          Opening driver portal…
        </div>
      </div>
    );
  }

  if (session.accessToken && session.organizationId && !hasDriverAccess) {
    return (
      <AccessState
        eyebrow="Wrong portal"
        title="This is the driver portal"
        message="You are signed in with a staff workspace account. Staff and owner operations stay in the dashboard so driver-only load and upload screens remain separated."
        detail="Driver portal access requires an invited driver account from your carrier or dispatcher."
        actions={[{ href: "/dashboard", label: "Go to staff workspace", primary: true }, { href: "/", label: "Public site" }]}
      />
    );
  }

  if (!hasDriverAccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 text-sm text-slate-600 shadow-soft">
          Opening driver portal…
        </div>
      </div>
    );
  }

  return (
    <div className="safe-page min-h-screen brand-page-shell text-slate-900">
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-start gap-4">
            <BrandLogo variant="operatingSystem" tone="light" lockup="mark" className="mt-1 h-11 w-11 shrink-0" priority />
            <div>
              <div className="ops-eyebrow">Driver Portal</div>
              <div className="mt-1 text-lg font-bold text-slate-950">Driver-only workspace</div>
              <div className="text-sm text-slate-500">{session.userEmail ?? "Authenticated user"}</div>
              <Link
                href="/"
                className="mt-1 inline-flex text-xs font-semibold text-brand-700 hover:text-brand-800"
              >
                ← Public site
              </Link>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="touch-target rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            Log Out
          </button>
        </div>
        <nav aria-label="Driver portal sections" className="mobile-scroll-area mx-auto grid max-w-6xl grid-flow-col auto-cols-[minmax(8rem,1fr)] gap-2 overflow-x-auto px-4 pb-3 sm:auto-cols-fr sm:px-6">
          {DRIVER_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive(pathname, item.href) ? "page" : undefined}
              className={`touch-target rounded-2xl px-3 py-2 text-left text-xs font-semibold transition focus-visible:ring-2 focus-visible:ring-brand-500 ${
                isActive(pathname, item.href)
                  ? "bg-brand-950 text-white shadow-sm"
                  : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-brand-50"
              }`}
            >
              <span className="block whitespace-nowrap">{item.label}</span>
              <span className={`mt-0.5 block whitespace-nowrap text-[11px] ${isActive(pathname, item.href) ? "text-white/70" : "text-slate-500"}`}>{item.helper}</span>
            </Link>
          ))}
        </nav>
      </header>
      <DriverMobileRuntime />
      {children}
    </div>
  );
}
