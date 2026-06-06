import { clerkMiddleware } from "@clerk/nextjs/server";
import { type NextRequest, NextResponse } from "next/server";

// Accounts are optional. When Clerk isn't configured the middleware is a plain
// passthrough so the app runs open/anonymous. When it is, clerkMiddleware makes
// the session available — but no routes are protected here (open access; only
// write/save actions require sign-in, enforced in the API).
const enabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

export default enabled
  ? clerkMiddleware()
  : (_req: NextRequest) => NextResponse.next();

export const config = {
  matcher: [
    // Skip Next internals and static files; run on app routes + API.
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|png|gif|svg|ico|webp|woff2?)).*)",
    "/(api|trpc)(.*)",
  ],
};
