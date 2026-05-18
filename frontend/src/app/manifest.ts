import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Freight Back Office OS",
    short_name: "Freight OS",
    description: "Freight back-office workflows for staff workspaces, driver paperwork, billing packets, factoring, invoices, and dispatch coordination.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#f6f8fb",
    theme_color: "#10233f",
    categories: ["business", "productivity", "navigation"],
    icons: [
      { src: "/brand/adwa-mark-light.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
      { src: "/icons/driver-icon.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Staff workspace", short_name: "Staff", description: "Open the authenticated staff workspace", url: "/login", icons: [{ src: "/brand/adwa-mark-light.svg", sizes: "any", type: "image/svg+xml" }] },
      { name: "Driver portal", short_name: "Driver", description: "Open driver load and document workflows", url: "/driver-login", icons: [{ src: "/icons/driver-icon.svg", sizes: "any", type: "image/svg+xml" }] },
      { name: "Request demo", short_name: "Demo", description: "Request demo or access", url: "/request-demo", icons: [{ src: "/brand/adwa-mark-light.svg", sizes: "any", type: "image/svg+xml" }] },
    ],
  };
}
