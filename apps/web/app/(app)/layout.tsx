import { AccountControls } from "@/components/AccountControls";
import { MobileNav } from "@/components/MobileNav";
import { ProfileSync } from "@/components/ProfileSync";
import { SideNav } from "@/components/SideNav";
import { ThemeSwitcher } from "@/components/ThemeSwitcher";
import { InstrumentSwitcher } from "@/components/instruments/InstrumentSwitcher";
import { GettingStarted } from "@/components/onboarding/GettingStarted";
import { GettingStartedChip } from "@/components/onboarding/GettingStartedChip";
import { WalkthroughButton } from "@/components/onboarding/WalkthroughButton";
import { WalkthroughProvider } from "@/components/onboarding/WalkthroughProvider";
import { WelcomeModal } from "@/components/onboarding/WelcomeModal";
import { clerkEnabled } from "@/lib/clerk";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import Link from "next/link";
import { DISCLAIMER } from "../../lib/strings";
import { Providers } from "../providers";

// The (app) routes all fetch live data on render; static prerender at build
// time would either fail (no API reachable) or freeze API responses into HTML.
// Force per-request server rendering so deploys don't need the API alive at
// build time and pages always serve fresh data.
export const dynamic = "force-dynamic";

function Wordmark() {
  return (
    <Link href="/dashboard" className="inline-flex items-baseline gap-2 group">
      <span
        className="font-serif font-light text-[22px] leading-none text-ink-1 tracking-[-0.02em] group-hover:opacity-90"
        style={{ fontVariationSettings: '"opsz" 72, "SOFT" 30' }}
      >
        Gold
        <span
          className="text-accent-bright"
          style={{
            fontStyle: "italic",
            fontVariationSettings: '"opsz" 72, "SOFT" 80',
          }}
        >
          e
        </span>
        neye
      </span>
      <span
        aria-hidden="true"
        className="font-mono text-[9px] uppercase tracking-eyebrow text-accent-deep relative -top-[2px]"
      >
        Terminal
      </span>
    </Link>
  );
}

function TopBar() {
  return (
    <header className="flex h-12 items-center justify-between border-b border-line-1 bg-surface-1 px-4 gap-3 lg:px-6 lg:gap-4">
      <MobileNav />
      <Wordmark />
      <InstrumentSwitcher className="ml-auto" />
      <ThemeSwitcher />
      <GettingStartedChip />
      <WalkthroughButton />
      <button
        type="button"
        className="text-ink-3 hover:text-accent transition-colors"
        aria-label="Alerts"
      >
        <svg
          aria-hidden="true"
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
      </button>
      <AccountControls />
    </header>
  );
}

function DisclaimerFooter() {
  return (
    <footer className="border-t border-line-1 bg-surface-1 px-6 py-2 text-xs text-ink-3">
      {DISCLAIMER}
    </footer>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <ThemeProvider>
        <WalkthroughProvider>
          <div className="flex h-screen flex-col bg-surface-0 text-ink-1">
            <TopBar />
            <div className="flex flex-1 overflow-hidden">
              <SideNav />
              <main className="flex-1 overflow-auto p-6">{children}</main>
            </div>
            <DisclaimerFooter />
          </div>
          <WelcomeModal />
          <GettingStarted />
          {clerkEnabled && <ProfileSync />}
        </WalkthroughProvider>
      </ThemeProvider>
    </Providers>
  );
}
