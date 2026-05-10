import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NGTI — Natural Gas Trading Intelligence",
  description: "Research and paper-trading terminal for natural gas markets.",
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
