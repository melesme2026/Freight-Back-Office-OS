"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getAccessToken, getOrganizationId, getUserRole } from "@/lib/auth";
import { canAccessDriverPortal } from "@/lib/rbac";

export default function DriverPortalLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const router = useRouter();
  const accessToken = getAccessToken();
  const organizationId = getOrganizationId();
  const userRole = getUserRole();

  useEffect(() => {
    if (!accessToken || !organizationId) {
      router.replace("/login");
      return;
    }

    if (!canAccessDriverPortal(userRole)) {
      router.replace("/dashboard");
    }
  }, [accessToken, organizationId, userRole, router]);

  if (!accessToken || !organizationId || !canAccessDriverPortal(userRole)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 text-sm text-slate-600 shadow-soft">
          Redirecting...
        </div>
      </div>
    );
  }

  return children;
}
