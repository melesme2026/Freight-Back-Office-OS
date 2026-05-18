import type { Metadata, Viewport } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: {
    default: "Freight Back Office OS",
    template: "%s | Freight Back Office OS",
  },
  description:
    "Freight Back Office OS helps carriers, dispatchers, and billing teams manage billing packets, factoring workflows, invoices, collections visibility, and freight back-office reporting.",
  applicationName: "Freight Back Office OS",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/brand/adwa-mark-light.svg", type: "image/svg+xml" }],
    shortcut: [{ url: "/brand/adwa-mark-light.svg", type: "image/svg+xml" }],
    apple: [{ url: "/brand/adwa-mark-light.svg", type: "image/svg+xml" }],
  },
  appleWebApp: {
    capable: true,
    title: "Adwa Freight OS",
    statusBarStyle: "default",
  },
  keywords: [
    "freight billing software",
    "billing packet management",
    "factoring workflow",
    "trucking back office",
    "freight document management",
    "collections visibility",
  ],
  metadataBase: new URL("https://www.adwafreight.com"),
  openGraph: {
    title: "Freight Back Office OS",
    description:
      "Freight billing packets, factoring workflows, invoices, collections visibility, and operational reporting for carriers and dispatch teams.",
    url: "https://www.adwafreight.com",
    siteName: "Freight Back Office OS",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Freight Back Office OS",
    description:
      "A freight back-office operating system for billing packets, factoring workflows, collections, and reporting.",
  },
};

export const viewport: Viewport = {
  themeColor: "#10233f",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-ops-canvas text-slate-900 antialiased">
        <div className="min-h-screen">{children}</div>
      </body>
    </html>
  );
}