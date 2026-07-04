import type { Metadata } from "next";

import { AppChrome } from "@/components/chrome";
import "./globals.css";

export const metadata: Metadata = {
  title: "AFP Revit BOM System",
  description: "Revit BOM, product mapping, and export workflow",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
