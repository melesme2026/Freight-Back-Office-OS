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
}: {
  eyebrow?: string;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="brand-card-muted p-8 text-center">
      <p className="ops-eyebrow">{eyebrow}</p>
      <h2 className="mt-3 text-2xl font-extrabold tracking-tight text-slate-950">{title}</h2>
      <div className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">{children}</div>
      {action ? <div className="mt-6">{action}</div> : null}
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
