import { AccessState } from "@/components/routing/AccessState";

export default function NotFound() {
  return (
    <AccessState
      eyebrow="Route not found"
      title="We could not find that Freight Back Office OS page"
      message="Public site, staff workspace, and driver portal routes are intentionally separated. Use the correct entry point below to continue."
      detail="Staff workspace routes live under /dashboard, driver routes live under /driver-portal, and public information stays on the marketing site."
      actions={[
        { href: "/", label: "Public site", primary: true },
        { href: "/login", label: "Staff workspace" },
        { href: "/driver-login", label: "Driver portal" },
      ]}
    />
  );
}
