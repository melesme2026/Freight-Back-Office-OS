const DRIVER_ROLES = new Set(["driver"]);
const TEAM_MANAGER_ROLES = new Set(["owner", "admin"]);

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
  return !isDriverRole(role);
}

export function canAccessDriverPortal(role: string | null | undefined): boolean {
  return DRIVER_ROLES.has(normalizeRole(role));
}

export function canManageTeam(role: string | null | undefined): boolean {
  return TEAM_MANAGER_ROLES.has(normalizeRole(role));
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
