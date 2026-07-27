/**
 * Phase U0 — the UI evidence harness.
 *
 * Sweeps pages × widths against the RUNNING dev stack, captures screenshots,
 * and programmatically detects the defect classes diagnosed in
 * docs/PHASE_U_PLAN.md:
 *   - overlap:    two card surfaces whose bounding rects intersect
 *   - h-overflow: a container scrolling horizontally without opting in
 *   - clipped:    prose cut off by a hidden-overflow box with no affordance
 *   - crushed:    text squeezed into an unreadably narrow column
 *
 * Manual gate (needs the stack; never CI) — the `validate_*` posture.
 * DoD for every UI PR: this audit exits 0 for the touched pages.
 *
 * Usage (from apps/web, stack running):
 *   pnpm run ui:audit                       # all pages, all widths
 *   pnpm run ui:audit -- --pages /dashboard # one page
 *   pnpm run ui:audit -- --widths 1280,1440
 * Output: .ui-audit/report.json + .ui-audit/<page>-<width>.png
 */
import { mkdirSync } from "node:fs";
import { writeFile } from "node:fs/promises";
import { chromium } from "playwright";

const ALL_PAGES = [
  "/dashboard",
  "/chart",
  "/signals",
  "/scenarios",
  "/journal",
  "/ledger",
  "/paper",
  "/calibration",
  "/validation",
  "/admin",
];
const ALL_WIDTHS = [390, 768, 1024, 1280, 1440, 1680, 1920];

const arg = (name) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : null;
};
// Accept "dashboard" or "/dashboard" (Git Bash mangles leading slashes into
// filesystem paths — pass bare names there).
const pages = (arg("pages")?.split(",") ?? ALL_PAGES).map((p) => {
  const bare = p.replace(/^.*[\\/]/, "").replace(/^\/?/, "");
  return `/${bare}`;
});
const widths = arg("widths")?.split(",").map(Number) ?? ALL_WIDTHS;
const base = arg("base") ?? "http://localhost:3000";
const outDir = arg("out") ?? ".ui-audit";
mkdirSync(outDir, { recursive: true });

/** Runs inside the page: returns {overlaps, hOverflow, clipped, crushed}. */
function auditPage() {
  const describe = (el) => {
    const cls = [...el.classList].slice(0, 3).join(".");
    const txt = (el.innerText ?? "").trim().slice(0, 40).replace(/\s+/g, " ");
    return `${el.tagName.toLowerCase()}${cls ? `.${cls}` : ""}${txt ? ` "${txt}"` : ""}`;
  };
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return (
      r.width > 0 &&
      r.height > 0 &&
      s.visibility !== "hidden" &&
      s.display !== "none"
    );
  };
  const main = document.querySelector("main") ?? document.body;

  // ── h-overflow ──
  const hOverflow = [];
  for (const el of [document.documentElement, main]) {
    if (el.scrollWidth > el.clientWidth + 4) {
      hOverflow.push(
        `${describe(el)} scrollW=${el.scrollWidth} clientW=${el.clientWidth}`,
      );
    }
  }

  // ── overlaps between card surfaces ──
  const cards = [...main.querySelectorAll("*")].filter((el) => {
    if (!visible(el)) return false;
    const r = el.getBoundingClientRect();
    if (r.width * r.height < 4000) return false;
    return [...el.classList].some((c) => c.includes("bg-surface-1"));
  });
  const overlaps = [];
  for (let i = 0; i < cards.length; i++) {
    for (let j = i + 1; j < cards.length; j++) {
      const a = cards[i];
      const b = cards[j];
      if (a.contains(b) || b.contains(a)) continue;
      const ra = a.getBoundingClientRect();
      const rb = b.getBoundingClientRect();
      const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (w > 8 && h > 8) {
        overlaps.push(
          `${describe(a)}  ×  ${describe(b)}  (${Math.round(w)}×${Math.round(h)}px)`,
        );
      }
    }
  }

  // ── clipped prose (hidden overflow, no affordance) ──
  const clipped = [];
  for (const el of main.querySelectorAll("*")) {
    if (!visible(el)) continue;
    const s = getComputedStyle(el);
    const text = (el.innerText ?? "").trim();
    if (text.length < 60) continue;
    const clipsY =
      el.scrollHeight > el.clientHeight + 6 &&
      (s.overflowY === "hidden" || s.overflowY === "clip");
    const hasClamp = s.webkitLineClamp && s.webkitLineClamp !== "none";
    const cls = [...el.classList].join(" ");
    if (
      clipsY &&
      !hasClamp &&
      !/overflow-y-(auto|scroll)|line-clamp/.test(cls)
    ) {
      clipped.push(
        `${describe(el)} scrollH=${el.scrollHeight} clientH=${el.clientHeight}`,
      );
    }
  }

  // ── content spill: children paint outside an overflow-visible card ──
  // (boxes don't intersect — the CONTENT escapes and overdraws neighbors;
  // this is the mechanism behind the observed card-over-card rendering).
  const spills = [];
  for (const el of cards) {
    const s = getComputedStyle(el);
    if (s.overflowY !== "visible" && s.overflowX !== "visible") continue;
    const spillY = el.scrollHeight - el.clientHeight;
    const spillX = el.scrollWidth - el.clientWidth;
    if (spillY > 12 || spillX > 12) {
      spills.push(
        `${describe(el)} spills ${spillX > 12 ? `${spillX}px right ` : ""}${spillY > 12 ? `${spillY}px below` : ""}`,
      );
    }
  }

  // ── crushed text columns ──
  const crushed = [];
  for (const el of main.querySelectorAll("*")) {
    if (!visible(el)) continue;
    if (el.children.length > 2) continue; // leaf-ish only
    const text = (el.innerText ?? "").trim();
    if (text.length < 15) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 80 && r.height > 60) {
      crushed.push(
        `${describe(el)} ${Math.round(r.width)}×${Math.round(r.height)}px`,
      );
    }
  }

  return {
    hOverflow,
    overlaps,
    spills: spills.slice(0, 12),
    clipped: clipped.slice(0, 12),
    crushed: crushed.slice(0, 12),
  };
}

const browser = await chromium.launch();
const report = {};
let defects = 0;

for (const width of widths) {
  const ctx = await browser.newContext({
    viewport: { width, height: width < 500 ? 844 : 1000 },
  });
  const page = await ctx.newPage();
  await page.addInitScript(() => {
    localStorage.setItem("goldeneye:walkthrough-completed", "1");
    localStorage.setItem("goldeneye:onboarding:seen", "1");
    localStorage.setItem("goldeneye:onboarding:dismissed", "1");
  });
  for (const path of pages) {
    const key = `${path}@${width}`;
    try {
      await page.goto(`${base}${path}`, {
        waitUntil: "networkidle",
        timeout: 90000,
      });
      await page.waitForTimeout(2200);
      const result = await page.evaluate(auditPage);
      const n =
        result.hOverflow.length +
        result.overlaps.length +
        result.spills.length +
        result.clipped.length +
        result.crushed.length;
      defects += n;
      report[key] = result;
      await page.screenshot({
        path: `${outDir}/${path.replaceAll("/", "_")}-${width}.png`,
      });
      const flag = n === 0 ? "OK " : `✗ ${n}`;
      console.log(
        `${flag}  ${key}  overlap=${result.overlaps.length} spill=${result.spills.length} hflow=${result.hOverflow.length} clip=${result.clipped.length} crush=${result.crushed.length}`,
      );
    } catch (e) {
      report[key] = { error: String(e).slice(0, 200) };
      defects += 1;
      console.log(`✗ ERR ${key}: ${String(e).slice(0, 120)}`);
    }
  }
  await ctx.close();
}
await browser.close();
await writeFile(`${outDir}/report.json`, JSON.stringify(report, null, 2));
console.log(
  `\n${defects === 0 ? "CLEAN" : `${defects} defect(s)`} — report: ${outDir}/report.json`,
);
process.exit(defects === 0 ? 0 : 1);
