import Link from "next/link";
import type { Route } from "next";

import { BrandLogo } from "@/components/ui/BrandLogo";

type AccessStateAction = {
  href: Route | string;
  label: string;
  primary?: boolean;
};

type AccessStateProps = {
  eyebrow: string;
  title: string;
  message: string;
  detail?: string;
  actions: AccessStateAction[];
};

export function AccessState({ eyebrow, title, message, detail, actions }: AccessStateProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-16 text-slate-900">
      <section className="w-full max-w-xl rounded-[1.75rem] border border-slate-200 bg-white p-8 text-center shadow-operational">
        <BrandLogo variant="operatingSystem" tone="light" className="mx-auto h-12 w-auto" priority />
        <p className="ops-eyebrow mt-8">{eyebrow}</p>
        <h1 className="mt-3 text-2xl font-extrabold tracking-tight text-slate-950">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{message}</p>
        {detail ? <p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p> : null}
        <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
          {actions.map((action) => (
            <Link
              key={`${action.href}-${action.label}`}
              href={action.href}
              className={
                action.primary
                  ? "rounded-xl bg-brand-950 px-5 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-900"
                  : "rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-100"
              }
            >
              {action.label}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
