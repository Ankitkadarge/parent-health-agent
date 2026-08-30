import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Parent Health Agent — Stay connected to your parent's health",
  description:
    "A WhatsApp companion that checks in on your parent's health so you don't have to worry alone.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
