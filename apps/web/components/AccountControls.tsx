"use client";

import { clerkEnabled } from "@/lib/clerk";
import { SignUpButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import { UserPlus } from "lucide-react";

/**
 * TopBar account affordance. Renders nothing when Clerk isn't configured (the
 * app stays open/anonymous). Otherwise: a "Sign up to save" CTA for signed-out
 * visitors and the Clerk user menu once signed in.
 */
export function AccountControls() {
  if (!clerkEnabled) return null;
  return (
    <>
      <SignedOut>
        <SignUpButton mode="modal">
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-sm border border-accent/50 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-accent transition-colors hover:bg-accent-soft hover:text-accent-bright"
          >
            <UserPlus size={12} strokeWidth={1.5} aria-hidden="true" />
            Sign up to save
          </button>
        </SignUpButton>
      </SignedOut>
      <SignedIn>
        <UserButton appearance={{ elements: { avatarBox: "h-6 w-6" } }} />
      </SignedIn>
    </>
  );
}
