import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Parent Health Agent — Stay connected to your parent's health",
  description:
    "A WhatsApp companion that checks in on your parent's health so you don't have to worry alone.",
};

export const viewport: Viewport = {
  themeColor: "#fbf8f2",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
