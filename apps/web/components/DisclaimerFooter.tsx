import { DISCLAIMER } from "../lib/strings";

export function DisclaimerFooter() {
  return (
    <footer className="fixed bottom-0 left-0 right-0 bg-surface-1 border-t border-line-1 px-6 py-2 text-xs text-ink-3 z-50">
      {DISCLAIMER}
    </footer>
  );
}
