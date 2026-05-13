import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Goldeneye — Research Terminal",
  description:
    "Decision-support and paper-trading terminal for commodity markets — research, scenario analysis, and explainable forecasting.",
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
