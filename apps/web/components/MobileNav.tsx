"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { NAV_ITEMS } from "./SideNav";

/**
 * Mobile navigation: a hamburger trigger (shown only below `lg`, where the
 * persistent `SideNav` is hidden) that opens the same nav as a slide-out drawer
 * over the content. Closes on route change, scrim tap, or Escape. On desktop the
 * trigger is hidden and the persistent sidebar is used instead.
 */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close the drawer whenever the route changes.
  // biome-ignore lint/correctness/useExhaustiveDependencies: pathname is the intentional trigger dependency; the body doesn't read it.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Escape to close + lock body scroll while open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        aria-label="Open navigation menu"
        aria-expanded={open}
        onClick={() => setOpen(true)}
        className="-ml-1 mr-1 flex items-center text-ink-2 transition-colors hover:text-accent lg:hidden"
      >
        <Menu size={18} strokeWidth={1.5} aria-hidden="true" />
      </button>

      {open && (
        <div className="fixed inset-0 z-[70] lg:hidden">
          {/* scrim */}
          <button
            type="button"
            aria-label="Close navigation menu"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          {/* drawer */}
          <nav className="absolute left-0 top-0 flex h-full w-64 max-w-[82vw] flex-col border-r border-line-1 bg-surface-1 pt-3 shadow-2xl">
            <div className="flex items-center justify-between border-b border-line-1 px-4 pb-3">
              <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-4">
                Navigate
              </span>
              <button
                type="button"
                aria-label="Close navigation menu"
                onClick={() => setOpen(false)}
                className="text-ink-3 transition-colors hover:text-accent"
              >
                <X size={16} strokeWidth={1.5} aria-hidden="true" />
              </button>
            </div>
            <div className="flex flex-col overflow-y-auto py-2">
              {NAV_ITEMS.map(({ href, label, Icon }) => {
                const active =
                  pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <Link
                    key={href}
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={`group flex items-center gap-3 border-l-2 px-5 py-3 text-sm transition-colors ${
                      active
                        ? "border-accent bg-surface-2 text-accent"
                        : "border-transparent text-ink-2 hover:bg-surface-2 hover:text-ink-1"
                    }`}
                  >
                    <Icon
                      size={16}
                      strokeWidth={1.5}
                      aria-hidden="true"
                      className={
                        active
                          ? "text-accent"
                          : "text-ink-4 transition-colors group-hover:text-ink-2"
                      }
                    />
                    {label}
                  </Link>
                );
              })}
            </div>
          </nav>
        </div>
      )}
    </>
  );
}
