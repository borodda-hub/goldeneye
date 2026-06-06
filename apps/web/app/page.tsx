import Link from "next/link";
import { LandingAccountControls } from "../components/LandingAccountControls";
import { GoldItalic } from "../components/typography/GoldItalic";

export const metadata = {
  title: "Goldeneye — Decision Infrastructure for the Probabilistic Era",
  description:
    "A research and paper-trading terminal for analysts who think in distributions, not directions. Built for commodity markets first.",
};

// ── small primitives — kept inline so the landing reads top-to-bottom ─────

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
      <span
        aria-hidden="true"
        className="inline-block w-[18px] h-px bg-accent"
      />
      {children}
    </span>
  );
}

function GoldRule({ className = "" }: { className?: string }) {
  return <hr className={`border-0 border-t border-accent-deep ${className}`} />;
}

function PrimaryCta({
  href,
  children,
}: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-eyebrow border border-accent bg-accent-soft px-5 py-3 text-accent-bright hover:bg-accent hover:text-bg transition-colors"
    >
      {children}
    </Link>
  );
}

function GhostCta({
  href,
  children,
}: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-eyebrow border border-line-2 px-5 py-3 text-ink-2 hover:bg-surface-2 hover:text-ink-1 transition-colors"
    >
      {children}
    </Link>
  );
}

// ── page ─────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-bg text-ink-1">
      {/* ── Chrome bar ──────────────────────────────────────────────── */}
      <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4 font-mono text-[10px] uppercase tracking-eyebrow text-ink-3 pointer-events-none">
        <div className="flex items-center gap-6">
          <span className="inline-flex items-center gap-2 pointer-events-auto">
            <span
              aria-hidden="true"
              className="inline-block w-1.5 h-1.5 rounded-full bg-accent"
              style={{ boxShadow: "0 0 8px var(--gold)" }}
            />
            Status · Live · v1.0
          </span>
        </div>
        <div className="flex items-center gap-6 pointer-events-auto">
          <LandingAccountControls />
          <Link
            href="/dashboard"
            className="hover:text-accent transition-colors"
          >
            Enter Terminal →
          </Link>
        </div>
      </div>

      {/* ── Cover ──────────────────────────────────────────────────── */}
      <section className="relative flex flex-col items-center justify-center min-h-screen px-8 text-center">
        {/* Radial spotlight + scan lines for the cover only */}
        <div
          aria-hidden="true"
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse 900px 500px at 50% 45%, rgba(201,163,92,0.12), transparent 60%), radial-gradient(ellipse 600px 300px at 50% 100%, rgba(201,163,92,0.04), transparent)",
          }}
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "repeating-linear-gradient(0deg, transparent 0, transparent 3px, rgba(255,255,255,0.012) 3px, rgba(255,255,255,0.012) 4px)",
          }}
        />

        <div className="relative z-10 flex flex-col items-center gap-6 max-w-4xl">
          <Eyebrow>Decision Infrastructure · Goldeneye Capital</Eyebrow>

          <h1
            className="font-serif font-light text-[120px] md:text-[172px] leading-[0.85] tracking-[-0.04em]"
            style={{ fontVariationSettings: '"opsz" 144, "SOFT" 30' }}
          >
            Gold
            <GoldItalic>e</GoldItalic>
            neye
          </h1>

          <p
            className="font-serif italic text-xl md:text-2xl text-ink-2 max-w-2xl mt-2"
            style={{ fontVariationSettings: '"opsz" 36, "SOFT" 60' }}
          >
            A terminal for analysts who think in{" "}
            <GoldItalic>distributions</GoldItalic>, not directions.
          </p>

          <div className="flex items-center gap-3 mt-8">
            <PrimaryCta href="/dashboard">Enter Terminal →</PrimaryCta>
            <GhostCta href="#thesis">Read the thesis</GhostCta>
          </div>

          <span className="font-mono text-[11px] tracking-[0.32em] uppercase text-accent mt-12">
            Chicago · 2026
          </span>
        </div>
      </section>

      {/* ── Thesis ─────────────────────────────────────────────────── */}
      <section
        id="thesis"
        className="px-8 md:px-32 py-32 max-w-[1400px] mx-auto"
      >
        <div className="flex flex-col gap-8 max-w-[1100px]">
          <Eyebrow>01 · Thesis</Eyebrow>
          <h2
            className="font-serif font-light text-[56px] md:text-[88px] leading-[1.02] tracking-[-0.025em]"
            style={{ fontVariationSettings: '"opsz" 144, "SOFT" 50' }}
          >
            The era of certainty is <GoldItalic>over</GoldItalic>. The decade
            ahead belongs to those who can reason in{" "}
            <GoldItalic>distributions</GoldItalic>.
          </h2>
          <div className="flex items-center gap-6 mt-8 font-mono text-[11px] tracking-[0.2em] uppercase text-ink-3">
            <span className="block w-[60px] h-px bg-accent" />
            Goldeneye Founding Memo
          </div>
        </div>
      </section>

      <GoldRule className="mx-8 md:mx-32 max-w-[1400px] xl:mx-auto" />

      {/* ── Problem ────────────────────────────────────────────────── */}
      <section className="px-8 md:px-32 py-32 max-w-[1400px] mx-auto">
        <div className="flex justify-between items-end mb-12">
          <div className="flex flex-col gap-4 max-w-2xl">
            <Eyebrow>02 · The Problem</Eyebrow>
            <h2 className="font-serif font-light text-[40px] md:text-[56px] leading-[1.02] tracking-[-0.015em]">
              The analyst is drowning in inputs and starved for{" "}
              <GoldItalic>structure</GoldItalic>.
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 border-t border-l border-line-1">
          {PROBLEM_FORCES.map((force, i) => (
            <article
              key={force.name}
              className="border-r border-b border-line-1 bg-surface-1 hover:bg-surface-2 transition-colors p-6 flex flex-col justify-between min-h-[180px]"
            >
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-accent">
                {String(i + 1).padStart(2, "0")} ·{" "}
                <span className="text-accent-deep">{force.tag}</span>
              </span>
              <h3 className="font-serif text-[22px] leading-tight text-ink-1 mt-auto">
                {force.name}
              </h3>
              <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-ink-3 mt-3">
                {force.detail}
              </p>
            </article>
          ))}
        </div>

        <div className="flex flex-wrap gap-16 mt-12 pt-8 border-t border-line-1">
          {PROBLEM_STATS.map((stat) => (
            <div key={stat.label} className="flex flex-col gap-2">
              <span
                className="font-serif text-[56px] md:text-[64px] leading-none text-accent-bright tracking-[-0.02em]"
                style={{ fontVariationSettings: '"opsz" 96' }}
              >
                {stat.value}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-3 max-w-[280px] leading-relaxed">
                {stat.label}
              </span>
            </div>
          ))}
        </div>
      </section>

      <GoldRule className="mx-8 md:mx-32 max-w-[1400px] xl:mx-auto" />

      {/* ── Capabilities ───────────────────────────────────────────── */}
      <section className="px-8 md:px-32 py-32 max-w-[1400px] mx-auto">
        <div className="flex flex-col gap-4 mb-16 max-w-3xl">
          <Eyebrow>03 · What we built</Eyebrow>
          <h2 className="font-serif font-light text-[40px] md:text-[56px] leading-[1.02] tracking-[-0.015em]">
            A terminal designed to make <GoldItalic>reasoning</GoldItalic> the
            product — not the byproduct.
          </h2>
        </div>

        <div className="flex flex-col gap-24">
          {CAPABILITIES.map((cap, i) => (
            <article
              key={cap.title}
              className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-8 md:gap-16 items-start"
            >
              <div className="flex flex-col gap-3">
                <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-accent-deep">
                  Capability {String(i + 1).padStart(2, "0")}
                </span>
                <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-accent">
                  {cap.tag}
                </span>
              </div>
              <div className="flex flex-col gap-4">
                <h3 className="font-serif text-[28px] md:text-[36px] leading-[1.08] tracking-[-0.01em] text-ink-1">
                  {cap.title}
                </h3>
                <p className="text-base leading-relaxed text-ink-2 max-w-[68ch]">
                  {cap.body}
                </p>
                <ul className="flex flex-col gap-1.5 mt-2">
                  {cap.bullets.map((b) => (
                    <li
                      key={b}
                      className="flex items-start gap-2.5 text-sm text-ink-3 leading-relaxed"
                    >
                      <span
                        aria-hidden="true"
                        className="mt-1.5 inline-block w-1 h-1 rounded-full bg-accent shrink-0"
                      />
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      </section>

      <GoldRule className="mx-8 md:mx-32 max-w-[1400px] xl:mx-auto" />

      {/* ── Decision Quality ───────────────────────────────────────── */}
      <section className="px-8 md:px-32 py-32 max-w-[1400px] mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12">
          <div className="md:col-span-5 flex flex-col gap-6">
            <Eyebrow>04 · The differentiator</Eyebrow>
            <h2 className="font-serif font-light text-[40px] md:text-[48px] leading-[1.05] tracking-[-0.015em]">
              We measure the <GoldItalic>decision</GoldItalic>, not the outcome.
            </h2>
          </div>
          <div className="md:col-span-7 flex flex-col gap-5">
            <p className="text-base leading-relaxed text-ink-2 max-w-[64ch]">
              Every thesis you write is logged with the data you saw, the
              counterarguments you weighed, and the conviction you assigned.
              When the market resolves, the system attributes outcome to
              <GoldItalic> calibration</GoldItalic>, not to luck.
            </p>
            <p className="text-base leading-relaxed text-ink-2 max-w-[64ch]">
              Over time the calibration record builds a personal reliability
              diagram.{" "}
              <span className="text-ink-1">
                Your 70% theses resolved at 64%.
              </span>{" "}
              That gap is the most actionable signal an analyst can have — and
              nobody else is measuring it.
            </p>

            <div className="grid grid-cols-3 gap-6 mt-6 border-t border-line-1 pt-6">
              <Stat value="3" label="Loop stages: pre-decision, mid, post" />
              <Stat value="N" label="Conviction buckets, scored on hit-rate" />
              <Stat
                value="LLM"
                label="DQ Coach surfaces patterns across runs"
              />
            </div>
          </div>
        </div>
      </section>

      <GoldRule className="mx-8 md:mx-32 max-w-[1400px] xl:mx-auto" />

      {/* ── Architecture badge row ─────────────────────────────────── */}
      <section className="px-8 md:px-32 py-24 max-w-[1400px] mx-auto">
        <div className="flex flex-col gap-6">
          <Eyebrow>05 · Built to last</Eyebrow>
          <h3 className="font-serif text-[28px] md:text-[32px] leading-[1.08] tracking-[-0.01em] text-ink-1 max-w-3xl">
            Production-grade infrastructure with{" "}
            <GoldItalic>research-grade transparency</GoldItalic>.
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-6">
            {ARCHITECTURE.map((row) => (
              <div
                key={row.label}
                className="border border-line-1 bg-surface-1 p-5 flex flex-col gap-2 hover:bg-surface-2 transition-colors"
              >
                <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
                  {row.label}
                </span>
                <span className="font-mono text-sm text-ink-1">
                  {row.value}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-4 mt-auto">
                  {row.detail}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Ask / CTA ──────────────────────────────────────────────── */}
      <section className="relative px-8 md:px-32 py-40 max-w-[1400px] mx-auto">
        <div
          aria-hidden="true"
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse 700px 400px at 50% 50%, rgba(201,163,92,0.05), transparent)",
          }}
        />
        <div className="relative z-10 flex flex-col items-center text-center gap-8 max-w-4xl mx-auto">
          <Eyebrow>06 · The Ask</Eyebrow>
          <p
            className="font-serif font-light text-[40px] md:text-[64px] leading-[1.05] tracking-[-0.02em]"
            style={{ fontVariationSettings: '"opsz" 144, "SOFT" 40' }}
          >
            Goldeneye is building the{" "}
            <GoldItalic>decision infrastructure</GoldItalic>
            <br />
            for the probabilistic era.
          </p>
          <p className="text-base text-ink-3 max-w-2xl leading-relaxed">
            The demo is live. The architecture is shipped. The next move is
            yours.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 mt-4">
            <PrimaryCta href="/dashboard">Enter Terminal →</PrimaryCta>
            <GhostCta href="mailto:bo@goldeneye.intel">
              Talk to founders
            </GhostCta>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      <footer className="border-t border-line-1 px-8 md:px-32 py-8 max-w-[1400px] mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4 font-mono text-[10px] uppercase tracking-eyebrow text-ink-4">
          <span>© 2026 Goldeneye Capital · Chicago, IL</span>
          <span>
            Research and decision-support terminal — not financial advice
          </span>
        </div>
      </footer>
    </main>
  );
}

// ── Content ──────────────────────────────────────────────────────────────

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span
        className="font-serif text-[36px] leading-none text-accent-bright tracking-[-0.02em]"
        style={{ fontVariationSettings: '"opsz" 72' }}
      >
        {value}
      </span>
      <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-ink-3 leading-relaxed">
        {label}
      </span>
    </div>
  );
}

const PROBLEM_FORCES = [
  {
    tag: "Volume",
    name: "More data than the day will allow",
    detail: "Headlines · Reports · Curves",
  },
  {
    tag: "Latency",
    name: "Signals decay before the analyst integrates them",
    detail: "Seconds to relevance",
  },
  {
    tag: "Opacity",
    name: "Models that won't show their work",
    detail: "Black-box forecasts",
  },
  {
    tag: "Anchoring",
    name: "Yesterday's thesis colors today's read",
    detail: "Bias compounds silently",
  },
  {
    tag: "Crowding",
    name: "Positioning data lags conviction",
    detail: "By the time it's clear, it's late",
  },
  {
    tag: "Calibration",
    name: "Confidence doesn't track edge",
    detail: "Few analysts measure their own hit-rate",
  },
];

const PROBLEM_STATS = [
  {
    value: "~12×",
    label: "Data sources a commodity analyst is expected to track in real-time",
  },
  {
    value: "3.2s",
    label: "Median attention span on any single chart before context-switch",
  },
  {
    value: "<7%",
    label: "Of analysts measure their own conviction calibration formally",
  },
];

const CAPABILITIES = [
  {
    tag: "Working Thesis",
    title:
      "A first-class object for what you believe — and what would change your mind.",
    body: "Every screen revolves around the analyst's current view. Evidence pulled from forecasts and scenarios auto-populates the supporting / contradicting columns. A conviction slider anchors the thesis to a number. Goldeneye's LLM critiques it: missed risks, blind spots, questions to answer.",
    bullets: [
      "Persistent dashboard panel — never two clicks away",
      "Auto-populated from latest ensemble forecast and scenario run",
      "Critique drawer surfaces what the analyst may be missing",
    ],
  },
  {
    tag: "Explainable Forecasts",
    title:
      "Four models, weighted reasoning steps, an honest hit-rate against history.",
    body: "The ensemble reads weather, storage, positioning, and price-only signals. Each model's directional call carries its supporting + contradicting factors with weights. A backtest engine replays the same models against real history under strict look-ahead controls — the hit rates are honest.",
    bullets: [
      "Moving Average · Volatility Regime · Prophet · Factor Composite",
      "Look-ahead-safe replay with cheating-model property tests",
      "Per-model hit rates displayed inline with the live signal",
    ],
  },
  {
    tag: "Scenario Lab",
    title: "Counterfactuals as a workflow — not a spreadsheet exercise.",
    body: "Apply primitive shocks (weather, LNG export, production, storage) to a baseline and watch the forecast shift. Goldeneye's narrator explains the directional pressure, the strongest counterargument, and the data that would validate or invalidate each scenario in the next 1-2 weeks. Exportable as a PDF for the desk's morning meeting.",
    bullets: [
      "Six pre-built templates, plus custom shock builder",
      "LLM-narrated outputs with safety envelope",
      "Executive PDF export with brand chrome",
    ],
  },
  {
    tag: "Decision Quality",
    title: "A reliability diagram for your own convictions.",
    body: "The Calibration page buckets every resolved journal entry by claimed conviction and reports actual hit rate. The DQ Coach panel synthesizes per-bucket coaching — what patterns appear in your wins, what patterns appear in your misses, and one actionable suggestion per band.",
    bullets: [
      "Resolved entries → reliability diagram with sample-size guardrails",
      "Auto-generated headline copy when calibration drifts ≥ 5 pp",
      "LLM coaching with explicit pattern-not-position framing",
    ],
  },
];

const ARCHITECTURE = [
  {
    label: "Frontend",
    value: "Next.js 14",
    detail: "App Router · RSC · TypeScript",
  },
  {
    label: "Backend",
    value: "FastAPI",
    detail: "Async SQLAlchemy · Pydantic v2",
  },
  { label: "Database", value: "Postgres", detail: "TimescaleDB hypertables" },
  { label: "Intelligence", value: "Claude", detail: "Anthropic Sonnet + Opus" },
];
