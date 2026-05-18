import type { HTMLAttributes, ReactNode } from "react";

function join(...classes: Array<string | undefined | false>): string {
  return classes.filter(Boolean).join(" ");
}

export function OperationalCard({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={join("brand-card p-5", className)} {...props} />;
}

export function KpiPanel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={join("brand-kpi-card", className)} {...props} />;
}

export function EmptyState({
  eyebrow = "No work queued",
  title,
  children,
  action,
  steps,
  className,
}: {
  eyebrow?: string;
  title: string;
  children: ReactNode;
  action?: ReactNode;
  steps?: string[];
  className?: string;
}) {
  return (
    <section className={join("brand-card-muted p-6 text-left sm:p-8", className)}>
      <div className="mx-auto max-w-2xl text-center">
        <p className="ops-eyebrow">{eyebrow}</p>
        <h2 className="mt-3 text-xl font-extrabold tracking-tight text-slate-950 sm:text-2xl">{title}</h2>
        <div className="mt-3 text-sm leading-6 text-slate-600">{children}</div>
      </div>
      {steps && steps.length > 0 ? (
        <ol className="mx-auto mt-5 grid max-w-3xl gap-3 text-left text-sm text-slate-700 sm:grid-cols-3">
          {steps.map((step, index) => (
            <li key={step} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <span className="mb-2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
                {index + 1}
              </span>
              <span className="block leading-5">{step}</span>
            </li>
          ))}
        </ol>
      ) : null}
      {action ? <div className="mt-6 flex justify-center">{action}</div> : null}
    </section>
  );
}

export function StatusChip({
  tone = "info",
  children,
}: {
  tone?: "info" | "success" | "warning" | "danger";
  children: ReactNode;
}) {
  const toneClass = {
    info: "status-chip-info",
    success: "status-chip-success",
    warning: "status-chip-warning",
    danger: "status-chip-danger",
  }[tone];

  return <span className={join("brand-chip", toneClass)}>{children}</span>;
}
