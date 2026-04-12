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
        <div className="min-h-screen">{children}</div>
      </body>
    </html>
  );
}