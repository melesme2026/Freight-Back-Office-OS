import type { Route } from "next";

export type AppSurface = "public" | "staff" | "driver" | "externalPortal";

export type SurfaceConfig = {
  id: AppSurface;
  label: string;
  description: string;
  primaryRoute: Route;
  loginRoute?: Route;
  productionHost: string;
};

export const SURFACES = {
  public: {
    id: "public",
    label: "Public site",
    description: "Marketing, pricing, and request-access information for Freight Back Office OS.",
    primaryRoute: "/",
    productionHost: "www.adwafreight.com",
  },
  staff: {
    id: "staff",
    label: "Staff workspace",
    description: "Authenticated owner and staff operations for loads, drivers, documents, billing, settings, and team management.",
    primaryRoute: "/dashboard",
    loginRoute: "/login",
    productionHost: "app.adwafreight.com",
  },
  driver: {
    id: "driver",
    label: "Driver portal",
    description: "Invite-only driver access for assigned loads, paperwork uploads, and dispatcher support.",
    primaryRoute: "/driver-portal",
    loginRoute: "/driver-login",
    productionHost: "drivers.adwafreight.com",
  },
  externalPortal: {
    id: "externalPortal",
    label: "External load portal",
    description: "Scoped load packet access for approved external contacts.",
    primaryRoute: "/portal",
    productionHost: "portal.adwafreight.com",
  },
} as const satisfies Record<AppSurface, SurfaceConfig>;

export function getSurfaceForPath(pathname: string): AppSurface {
  if (pathname === "/dashboard" || pathname.startsWith("/dashboard/")) {
    return "staff";
  }

  if (pathname === "/driver-login" || pathname === "/driver-portal" || pathname.startsWith("/driver-portal/")) {
    return "driver";
  }

  if (pathname === "/portal" || pathname.startsWith("/portal/")) {
    return "externalPortal";
  }

  return "public";
}

export function getPublicEntryRoute(hostname?: string | null): Route {
  const normalizedHost = (hostname ?? "").trim().toLowerCase();

  if (normalizedHost === SURFACES.staff.productionHost) {
    return SURFACES.staff.loginRoute;
  }

  if (normalizedHost === SURFACES.driver.productionHost) {
    return SURFACES.driver.loginRoute;
  }

  return SURFACES.public.primaryRoute;
}
