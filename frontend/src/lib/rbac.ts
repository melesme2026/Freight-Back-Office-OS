const DRIVER_ROLES = new Set(["driver"]);

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
