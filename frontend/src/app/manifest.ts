import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Adwa Freight OS",
    short_name: "Adwa OS",
    description: "Premium freight operations workflows for driver documents, billing packets, factoring, invoices, and dispatch coordination.",
    start_url: "/driver-portal",
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
      { name: "Upload POD", short_name: "Upload", description: "Capture and upload a driver document", url: "/driver-portal/uploads", icons: [{ src: "/brand/adwa-mark-light.svg", sizes: "any", type: "image/svg+xml" }] },
      { name: "Assigned Loads", short_name: "Loads", description: "View assigned driver loads", url: "/driver-portal/loads", icons: [{ src: "/brand/adwa-mark-light.svg", sizes: "any", type: "image/svg+xml" }] },
    ],
  };
}
