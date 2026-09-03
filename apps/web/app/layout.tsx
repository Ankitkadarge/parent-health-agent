import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Parent Health Agent — WhatsApp family health setup",
  description:
    "A private beta that verifies family members and guides a short diabetes and medication setup over WhatsApp.",
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
