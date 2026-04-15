import type { Route } from "next";
import Link from "next/link";

type AuthNavigationLink = {
  href: Route;
  label: string;
};

type AuthNavigationLinksProps = {
  secondaryLinks?: AuthNavigationLink[];
};

const PRIMARY_LINKS: AuthNavigationLink[] = [
  { href: "/", label: "Back to Home" },
  { href: "/login", label: "Staff Login" },
  { href: "/driver-login", label: "Driver Login" },
];

export function AuthNavigationLinks({ secondaryLinks = [] }: AuthNavigationLinksProps) {
  return (
    <div className="mt-4 space-y-2 text-xs">
      <div className="flex flex-wrap gap-3">
        {PRIMARY_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="font-semibold text-brand-700 hover:text-brand-800"
          >
            {link.label}
          </Link>
        ))}
      </div>

      {secondaryLinks.length > 0 ? (
        <div className="flex flex-wrap gap-3 text-slate-600">
          {secondaryLinks.map((link) => (
            <Link
              key={`${link.href}-${link.label}`}
              href={link.href}
              className="font-semibold text-brand-700 hover:text-brand-800"
            >
              {link.label}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}