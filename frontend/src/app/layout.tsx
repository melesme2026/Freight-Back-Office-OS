import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: {
    default: "Freight Back Office OS",
    template: "%s | Freight Back Office OS",
  },
  description: "Next-gen freight back office operating system",
  applicationName: "Freight Back Office OS",
  keywords: ["freight", "logistics", "trucking", "back office", "factoring"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {/* Global App Shell */}
        <div className="flex min-h-screen flex-col">
          {/* Top Navigation Placeholder (future: user menu, org switcher, etc.) */}
          <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-900">
                Freight Back Office OS
              </div>
              <div className="text-xs text-slate-500">
                V1
              </div>
            </div>
          </header>

          {/* Main Content */}
          <main className="flex-1">{children}</main>

          {/* Footer (lightweight for now) */}
          <footer className="border-t border-slate-200 bg-white">
            <div className="mx-auto max-w-7xl px-6 py-3 text-xs text-slate-500">
              © {new Date().getFullYear()} Freight Back Office OS
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}