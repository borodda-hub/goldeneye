/**
 * Whether Clerk auth is configured. Accounts are an *optional* layer: with no
 * publishable key the app runs fully open/anonymous (the demo + local dev work
 * untouched); set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY (+ CLERK_SECRET_KEY) to light
 * up sign-up. The flag is a build-time NEXT_PUBLIC_ value, so it's safe to read
 * in both server and client components.
 */
export const clerkEnabled = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY,
);
