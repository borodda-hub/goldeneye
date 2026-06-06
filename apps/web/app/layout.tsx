import { clerkEnabled } from "@/lib/clerk";
import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Goldeneye — Research Terminal",
  description:
    "Decision-support and paper-trading terminal for commodity markets — research, scenario analysis, and explainable forecasting.",
};

// No-flash theme: set <html data-theme> from the stored choice before first
// paint, so a non-default theme doesn't flash the default palette on load.
// (The default "goldeneye" omits the attribute and uses :root.)
const themeScript = `(function(){try{var t=localStorage.getItem('goldeneye:theme');if(t&&['slate','phosphor','ember','onyx','indigo','mauve','abyss','nord'].indexOf(t)>-1){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const tree = (
    <html lang="en">
      <head>
        {/* biome-ignore lint/security/noDangerouslySetInnerHtml: static, no user data */}
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
  // Accounts are optional: only mount ClerkProvider when keys are configured, so
  // the app runs fully open/anonymous without them.
  return clerkEnabled ? <ClerkProvider>{tree}</ClerkProvider> : tree;
}
