"use client";

import { clerkEnabled } from "@/lib/clerk";
import { SignInButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";

/**
 * Landing-page (home) auth affordance, styled for the chrome bar. Renders
 * nothing when Clerk isn't configured (the app stays open/anonymous). Signed
 * out: a "Sign in" link (the Clerk modal also offers sign-up). Signed in: the
 * Clerk user menu. The Clerk sign-in modal lands you back on the home page;
 * "Enter Terminal →" then carries your session into the app.
 */
export function LandingAccountControls() {
  if (!clerkEnabled) return null;
  return (
    <>
      <SignedOut>
        <SignInButton mode="modal">
          <button
            type="button"
            className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3 hover:text-accent transition-colors"
          >
            Sign in
          </button>
        </SignInButton>
      </SignedOut>
      <SignedIn>
        <UserButton appearance={{ elements: { avatarBox: "h-6 w-6" } }} />
      </SignedIn>
    </>
  );
}
