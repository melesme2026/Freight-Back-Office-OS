const DRIVER_ROLES = new Set(["driver"]);
const TEAM_MANAGER_ROLES = new Set(["owner", "admin"]);
const OWNER_ONLY_ROLES = new Set(["owner"]);
const LEAD_PIPELINE_ROLES = new Set(["owner", "admin", "staff", "ops_manager", "ops_agent", "support_agent"]);

function isOwner(role: string): boolean {
  return role === "owner";
}

function isAdmin(role: string): boolean {
  return role === "admin";
}

function normalizeRole(role: string | null | undefined): string {
  return (role ?? "").trim().toLowerCase();
}

export function isDriverRole(role: string | null | undefined): boolean {
  return DRIVER_ROLES.has(normalizeRole(role));
}

export function canAccessDashboard(role: string | null | undefined): boolean {
  const normalized = normalizeRole(role);
  return normalized.length > 0 && !DRIVER_ROLES.has(normalized);
}

export function canAccessDriverPortal(role: string | null | undefined): boolean {
  return DRIVER_ROLES.has(normalizeRole(role));
}

export function canManageTeam(role: string | null | undefined): boolean {
  return TEAM_MANAGER_ROLES.has(normalizeRole(role));
}

export function canManageLeadPipeline(role: string | null | undefined): boolean {
  return LEAD_PIPELINE_ROLES.has(normalizeRole(role));
}

export function canAccessDashboardPath(role: string | null | undefined, pathname: string): boolean {
  const normalized = normalizeRole(role);
  if (!canAccessDashboard(normalized)) {
    return false;
  }

  if (pathname === "/dashboard/leads" || pathname.startsWith("/dashboard/leads/")) {
    return LEAD_PIPELINE_ROLES.has(normalized);
  }

  if (pathname === "/dashboard/team" || pathname.startsWith("/dashboard/team/")) {
    return TEAM_MANAGER_ROLES.has(normalized);
  }

  if (pathname === "/dashboard/settings" || pathname.startsWith("/dashboard/settings/")) {
    return OWNER_ONLY_ROLES.has(normalized) || isAdmin(normalized);
  }

  if (pathname === "/dashboard/billing/settings" || pathname.startsWith("/dashboard/billing/settings/")) {
    return OWNER_ONLY_ROLES.has(normalized);
  }

  return true;
}

export function canModifyTeamMember(
  actorRole: string | null | undefined,
  targetRole: string | null | undefined
): boolean {
  const actor = normalizeRole(actorRole);
  const target = normalizeRole(targetRole);

  if (isOwner(actor)) {
    return target !== "owner";
  }

  if (isAdmin(actor)) {
    return !["owner", "admin"].includes(target);
  }

  return false;
}

export function resolvePostLoginRoute(
  role: string | null | undefined
): "/dashboard" | "/dashboard/billing" | "/dashboard/support" | "/driver-portal" {
  const normalized = normalizeRole(role);

  if (DRIVER_ROLES.has(normalized)) {
    return "/driver-portal";
  }

  switch (normalized) {
    case "billing_admin":
      return "/dashboard/billing";
    case "support_agent":
      return "/dashboard/support";
    default:
      return "/dashboard";
  }
}
