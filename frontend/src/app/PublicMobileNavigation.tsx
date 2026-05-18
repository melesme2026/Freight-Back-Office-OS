"use client";

import Link from "next/link";
import { useState } from "react";

const mobileLinks = [
  { href: "/#features", label: "Features" },
  { href: "/#workflow", label: "Workflow" },
  { href: "/pricing", label: "Pricing" },
  { href: "/#faq", label: "FAQ" },
  { href: "/login", label: "Staff workspace" },
  { href: "/driver-login", label: "Driver portal" },
  { href: "/request-demo?intent=request-access", label: "Request access" },
  { href: "/request-demo", label: "Request demo", primary: true },
] as const;

export function PublicMobileNavigation() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative lg:hidden">
      <button
        type="button"
        className="touch-target inline-flex items-center justify-center rounded-xl border border-white/15 px-3 py-2 text-sm font-semibold text-slate-100 transition hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-brand-200"
        aria-controls="public-mobile-navigation"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span className="sr-only">Open public navigation menu</span>
        <span aria-hidden="true" className="flex flex-col gap-1">
          <span className="block h-0.5 w-5 rounded-full bg-current" />
          <span className="block h-0.5 w-5 rounded-full bg-current" />
          <span className="block h-0.5 w-5 rounded-full bg-current" />
        </span>
      </button>

      {isOpen ? (
        <div
          id="public-mobile-navigation"
          className="absolute right-0 top-full mt-3 w-64 rounded-2xl border border-white/10 bg-slate-900 p-3 text-sm font-semibold text-slate-100 shadow-2xl"
        >
          <div className="grid gap-1">
            {mobileLinks.map((link) => {
              const className = "primary" in link && link.primary
                ? "rounded-xl bg-white px-4 py-3 text-center text-slate-950 shadow-soft transition hover:bg-brand-50"
                : "rounded-xl px-4 py-3 transition hover:bg-white/10 hover:text-white";

              return (
                <Link key={link.href} href={link.href} className={className} onClick={() => setIsOpen(false)}>
                  {link.label}
                </Link>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
