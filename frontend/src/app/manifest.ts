import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ADWA Freight Driver",
    short_name: "ADWA Driver",
    description: "Mobile driver workflows for load documents, offline upload queue, ETA updates, and dispatch reminders.",
    start_url: "/driver-portal",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#f8fafc",
    theme_color: "#2563eb",
    categories: ["business", "productivity", "navigation"],
    icons: [
      { src: "/icons/driver-icon.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
      { src: "/icons/driver-icon.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Upload POD", short_name: "Upload", description: "Capture and upload a driver document", url: "/driver-portal/uploads", icons: [{ src: "/icons/driver-icon.svg", sizes: "any" }] },
      { name: "Assigned Loads", short_name: "Loads", description: "View assigned driver loads", url: "/driver-portal/loads", icons: [{ src: "/icons/driver-icon.svg", sizes: "any" }] },
    ],
  };
}
