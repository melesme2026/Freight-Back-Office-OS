"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  clearAuth,
  getAuthSession,
  onAuthChanged,
  type AuthSession,
} from "@/lib/auth";
import { canAccessDashboardPath, canManageLeadPipeline } from "@/lib/rbac";
import { WORKSPACE_NAV_ITEMS, WORKSPACE_NAV_SECTIONS, type WorkspaceNavItem } from "@/lib/navigation";
import { AccessState } from "@/components/routing/AccessState";
import { BrandLogo, BrandMark } from "@/components/ui/BrandLogo";

function canShowNavItem(item: WorkspaceNavItem, role: string | null): boolean {
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

function NavLink({ item, pathname, onNavigate }: { item: WorkspaceNavItem; pathname: string; onNavigate?: () => void }) {
  const active = isActivePath(pathname, item.href);

  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={`group flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 ${
        active
          ? "bg-brand-950 text-white shadow-sm"
          : "text-slate-700 hover:bg-brand-50 hover:text-brand-950"
      }`}
    >
      <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs ${active ? "bg-white/15 text-white" : "bg-slate-100 text-slate-500 group-hover:bg-white"}`} aria-hidden="true">
        {item.icon}
      </span>
      <span className="min-w-0 flex-1 truncate">{item.label}</span>
      {item.placeholder ? (
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${active ? "bg-white/15 text-white" : "bg-slate-100 text-slate-500"}`}>
          Soon
        </span>
      ) : null}
    </Link>
  );
}

function GroupedNavigation({ role, pathname, onNavigate, mobile = false }: { role: string | null; pathname: string; onNavigate?: () => void; mobile?: boolean }) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  return (
    <nav aria-label="Workspace sections" className="space-y-5">
      {WORKSPACE_NAV_SECTIONS.map((section) => {
        const visibleItems = section.items.filter((item) => canShowNavItem(item, role));
        if (visibleItems.length === 0) return null;
        const isCollapsed = Boolean(collapsed[section.id]);

        return (
          <section key={section.id} aria-labelledby={`nav-${section.id}`} className="space-y-2">
            <button
              id={`nav-${section.id}`}
              type="button"
              onClick={() => mobile ? setCollapsed((current) => ({ ...current, [section.id]: !isCollapsed })) : undefined}
              aria-expanded={!isCollapsed}
              className={`flex w-full items-center justify-between rounded-lg px-2 py-1 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400 ${mobile ? "hover:bg-slate-100" : "cursor-default"}`}
            >
              <span>{section.label}</span>
              {mobile ? <span aria-hidden="true">{isCollapsed ? "+" : "−"}</span> : null}
            </button>
            <div className={isCollapsed && mobile ? "hidden" : "space-y-1"}>
              {visibleItems.map((item) => (
                <NavLink key={item.href} item={item} pathname={pathname} onNavigate={onNavigate} />
              ))}
            </div>
          </section>
        );
      })}
    </nav>
  );
}

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
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
    setMobileNavOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mounted) return;

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
    const activeItem = WORKSPACE_NAV_ITEMS.find((item) => isActivePath(pathname, item.href));
    return activeItem?.label ?? "Dashboard";
  }, [pathname]);

  function handleLogout() {
    clearAuth();
    router.replace("/login?reason=logged_out");
  }

  if (!mounted) return null;
  if (!session.accessToken || !session.organizationId) return null;

  if (accessDenied || !canAccessDashboardPath(session.userRole, pathname)) {
    return (
      <AccessState
        eyebrow="Forbidden staff workspace route"
        title="This staff workspace area is restricted"
        message="Your account is signed in, but it does not include permission for this owner or staff-only dashboard area. No driver portal or public-site access is granted from here."
        detail="If this looks wrong, ask an owner or administrator to update your Freight Back Office OS role."
        actions={[{ href: "/dashboard", label: "Back to staff workspace", primary: true }, { href: "/", label: "Public site" }]}
      />
    );
  }

  return (
    <div className="safe-page min-h-screen brand-page-shell text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-slate-200/80 bg-white/95 shadow-soft xl:flex xl:flex-col">
          <div className="border-b border-slate-200 px-5 py-5">
            <Link href="/dashboard" className="block" aria-label="Adwa Freight OS dashboard">
              <BrandLogo variant="operatingSystem" tone="light" className="h-11 w-auto" priority />
            </Link>
            <div className="mt-4 ops-eyebrow">Staff workspace</div>
            <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <div className="font-semibold text-slate-900">{session.userEmail ?? "Signed-in user"}</div>
              <div className="mt-1 truncate">Org: {session.organizationId}</div>
            </div>
            <Link href="/" className="mt-3 inline-flex text-xs font-bold text-brand-700 hover:text-brand-900">← Public site</Link>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-4">
            <GroupedNavigation role={session.userRole} pathname={pathname} />
          </div>

          <div className="border-t border-slate-200 p-3">
            <button type="button" onClick={handleLogout} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-brand-500">
              Log Out
            </button>
          </div>
        </aside>

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
            <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
              <div className="min-w-0">
                <div className="ops-eyebrow">Staff workspace</div>
                <p className="mt-1 truncate text-xl font-bold text-slate-950">{pageTitle}</p>
              </div>

              <div className="flex items-center gap-3">
                <div className="hidden text-right md:block">
                  <div className="text-sm font-medium text-slate-900">{session.userEmail ?? "Signed-in user"}</div>
                  <div className="text-xs text-slate-500">Organization active</div>
                </div>
                <button type="button" onClick={() => setMobileNavOpen(true)} aria-expanded={mobileNavOpen} aria-controls="mobile-workspace-navigation" className="touch-target rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-brand-500 xl:hidden">
                  Menu
                </button>
              </div>
            </div>
          </header>

          {mobileNavOpen ? (
            <div className="fixed inset-0 z-50 xl:hidden" role="dialog" aria-modal="true" aria-label="Workspace navigation">
              <button type="button" className="absolute inset-0 bg-slate-950/40" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />
              <div id="mobile-workspace-navigation" className="absolute inset-y-0 left-0 flex w-full max-w-sm flex-col bg-white shadow-2xl">
                <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <BrandMark tone="light" className="h-10 w-10" />
                      <div>
                        <div className="ops-eyebrow">Staff workspace</div>
                        <div className="mt-1 text-lg font-bold text-slate-950">Navigate workspace</div>
                      </div>
                    </div>
                    <button type="button" onClick={() => setMobileNavOpen(false)} className="touch-target rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 focus-visible:ring-2 focus-visible:ring-brand-500">
                      Close
                    </button>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto px-4 py-5">
                  <GroupedNavigation role={session.userRole} pathname={pathname} onNavigate={() => setMobileNavOpen(false)} mobile />
                </div>
                <div className="border-t border-slate-200 p-4">
                  <button type="button" onClick={handleLogout} className="touch-target w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">
                    Log Out
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          <main className="min-w-0 flex-1 overflow-x-clip">{children}</main>
        </div>
      </div>
    </div>
  );
}
