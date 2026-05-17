import type { Route } from "next";

export type WorkspaceRole =
  | "owner"
  | "admin"
  | "dispatcher"
  | "billing"
  | "collections"
  | "accounting"
  | "driver_support";

export type WorkspaceNavItem = {
  href: Route;
  label: string;
  icon: string;
  description: string;
  futureRoles: WorkspaceRole[];
  placeholder?: boolean;
};

export type WorkspaceNavSection = {
  id: "operations" | "finance" | "relationships" | "intelligence" | "administration";
  label: string;
  items: WorkspaceNavItem[];
};

export const WORKSPACE_NAV_SECTIONS: WorkspaceNavSection[] = [
  {
    id: "operations",
    label: "Operations",
    items: [
      { href: "/dashboard", label: "Overview", icon: "⌘", description: "Command center snapshot", futureRoles: ["owner", "admin", "dispatcher", "billing", "collections", "accounting", "driver_support"] },
      { href: "/dashboard/loads", label: "Loads", icon: "▣", description: "Active freight work", futureRoles: ["owner", "admin", "dispatcher", "billing", "driver_support"] },
      { href: "/dashboard/documents", label: "Documents", icon: "□", description: "Paperwork intake", futureRoles: ["owner", "admin", "dispatcher", "billing", "driver_support"] },
      { href: "/dashboard/review-queue", label: "Review Queue", icon: "✓", description: "Exceptions and validation", futureRoles: ["owner", "admin", "dispatcher", "billing"] },
      { href: "/dashboard/drivers", label: "Drivers", icon: "◉", description: "Driver coordination", futureRoles: ["owner", "admin", "dispatcher", "driver_support"] },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    items: [
      { href: "/dashboard/billing", label: "Billing", icon: "$", description: "Invoice readiness", futureRoles: ["owner", "admin", "billing", "collections", "accounting"] },
      { href: "/dashboard/factoring", label: "Factoring", icon: "◆", description: "Funding workflow", futureRoles: ["owner", "admin", "billing", "collections", "accounting"] },
      { href: "/dashboard/money", label: "Money", icon: "↗", description: "Cash movement", futureRoles: ["owner", "admin", "collections", "accounting"] },
      { href: "/dashboard/accounting", label: "Accounting", icon: "≡", description: "Books handoff", futureRoles: ["owner", "admin", "accounting"] },
    ],
  },
  {
    id: "relationships",
    label: "Relationships",
    items: [
      { href: "/dashboard/customers", label: "Customers", icon: "◇", description: "Customer accounts", futureRoles: ["owner", "admin", "dispatcher", "billing"] },
      { href: "/dashboard/brokers", label: "Brokers", icon: "◈", description: "Broker profiles", futureRoles: ["owner", "admin", "dispatcher", "billing", "collections"] },
      { href: "/dashboard/leads", label: "Leads", icon: "+", description: "Pipeline", futureRoles: ["owner", "admin"] },
    ],
  },
  {
    id: "intelligence",
    label: "Intelligence",
    items: [
      { href: "/dashboard/analytics", label: "Analytics", icon: "◌", description: "Operational reporting", futureRoles: ["owner", "admin", "dispatcher", "billing", "collections", "accounting"] },
      { href: "/dashboard/command-center", label: "Operational Insights", icon: "◎", description: "Future-ready insights workspace", futureRoles: ["owner", "admin", "dispatcher", "billing", "collections"], placeholder: true },
    ],
  },
  {
    id: "administration",
    label: "Administration",
    items: [
      { href: "/dashboard/team", label: "Team", icon: "●", description: "Workspace access", futureRoles: ["owner", "admin"] },
      { href: "/dashboard/notifications", label: "Notifications", icon: "•", description: "Alerts and reminders", futureRoles: ["owner", "admin", "dispatcher", "billing", "collections", "driver_support"] },
      { href: "/dashboard/support", label: "Support", icon: "?", description: "Issue escalation", futureRoles: ["owner", "admin", "dispatcher", "billing", "collections", "driver_support"] },
      { href: "/dashboard/settings", label: "Settings", icon: "⚙", description: "Carrier configuration", futureRoles: ["owner", "admin"] },
    ],
  },
];

export const WORKSPACE_NAV_ITEMS = WORKSPACE_NAV_SECTIONS.flatMap((section) => section.items);
