import Link from "next/link";
import { GoldItalic } from "../../components/typography/GoldItalic";

export const metadata = {
  title: "Goldeneye — Methodology, Architecture & Value",
  description:
    "The Goldeneye white paper: how the terminal forecasts, how it validates, what it refuses to claim, and how the system is built.",
};

/**
 * The white paper. Where the landing pitches and /validation proves, this page
 * EXPLAINS — methodology, architecture, and value in long-form depth.
 *
 * Truth discipline: every number here traces to docs/MODEL_DILIGENCE.md and is
 * dated in §10; live drift-locked numbers live on /validation. Design language
 * is the landing's (serif display + mono eyebrows + token colors only).
 */

// ── primitives (mirrors the landing's inline idiom) ──────────────────────

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2.5 font-mono text-[11px] uppercase tracking-eyebrow text-accent">
      <span
        aria-hidden="true"
        className="inline-block w-[18px] h-px bg-accent"
      />
      {children}
    </span>
  );
}

function GoldRule() {
  return (
    <hr className="border-0 border-t border-accent-deep mx-8 md:mx-32 max-w-[1400px] xl:mx-auto" />
  );
}

function Section({
  id,
  eyebrow,
  title,
  children,
}: {
  id: string;
  eyebrow: string;
  title: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="px-8 md:px-32 py-20 max-w-[1400px] mx-auto scroll-mt-16"
    >
      <div className="flex flex-col gap-4 mb-10 max-w-3xl">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h2 className="font-serif font-light text-[32px] md:text-[44px] leading-[1.05] tracking-[-0.015em]">
          {title}
        </h2>
      </div>
      <div className="flex flex-col gap-5 max-w-[72ch] text-base leading-relaxed text-ink-2">
        {children}
      </div>
    </section>
  );
}

function Doctrine({
  n,
  title,
  body,
  mechanism,
}: {
  n: string;
  title: string;
  body: string;
  mechanism: string;
}) {
  return (
    <article className="border-l-2 border-accent-deep pl-5 py-1 flex flex-col gap-2">
      <h3 className="font-serif text-[22px] leading-tight text-ink-1">
        <span className="font-mono text-[11px] uppercase tracking-eyebrow text-accent mr-3 align-middle">
          {n}
        </span>
        {title}
      </h3>
      <p className="text-base leading-relaxed text-ink-2">{body}</p>
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-4">
        Enforced by ·{" "}
        <span className="text-ink-3 normal-case">{mechanism}</span>
      </p>
    </article>
  );
}

function Term({ children }: { children: React.ReactNode }) {
  return <span className="text-ink-1">{children}</span>;
}

// ── page ─────────────────────────────────────────────────────────────────

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-bg text-ink-1">
      {/* ── Chrome bar ──────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-8 py-4 font-mono text-[11px] uppercase tracking-eyebrow text-ink-3">
        <Link href="/" className="hover:text-accent transition-colors">
          ← Goldeneye
        </Link>
        <div className="flex items-center gap-6">
          <Link
            href="/validation"
            className="hover:text-accent transition-colors"
          >
            Validation ledger
          </Link>
          <Link
            href="/dashboard"
            className="hover:text-accent transition-colors"
          >
            Enter Terminal →
          </Link>
        </div>
      </div>

      {/* ── Title + abstract ────────────────────────────────────────── */}
      <header className="px-8 md:px-32 pt-20 pb-16 max-w-[1400px] mx-auto">
        <div className="flex flex-col gap-6 max-w-4xl">
          <Eyebrow>White paper · 2026</Eyebrow>
          <h1
            className="font-serif font-light text-[44px] md:text-[72px] leading-[1.0] tracking-[-0.025em]"
            style={{ fontVariationSettings: '"opsz" 144, "SOFT" 40' }}
          >
            Methodology, architecture, and the case for measuring{" "}
            <GoldItalic>calibration</GoldItalic> instead of selling{" "}
            <GoldItalic>prediction</GoldItalic>.
          </h1>

          <div className="border border-line-1 bg-surface-1 p-6 md:p-8 mt-4 flex flex-col gap-4">
            <span className="font-mono text-[11px] uppercase tracking-eyebrow text-accent">
              Abstract
            </span>
            <p className="font-serif italic text-lg md:text-xl leading-relaxed text-ink-2 max-w-[72ch]">
              Goldeneye is a research and paper-trading terminal for commodity
              markets. It runs a transparent forecast engine over real market,
              storage, positioning, weather, and news data — and then does the
              thing forecast products don&rsquo;t: it tests every one of its own
              claims out-of-sample on real data, publishes the failures at full
              weight, and scores its users&rsquo; judgment with the same
              machinery. One claim has earned an edge — the price-range bands
              are calibrated. Directional prediction was tested the same way and
              has not earned one, so the terminal frames direction as labeled
              views, never probabilities. The product is not a crystal ball. It
              is decision infrastructure: an instrument for finding out, with
              evidence, how good your judgment actually is.
            </p>
          </div>

          {/* Contents */}
          <nav
            aria-label="Contents"
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-2 mt-6 border-t border-line-1 pt-6"
          >
            {TOC.map((t) => (
              <a
                key={t.id}
                href={`#${t.id}`}
                className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-3 hover:text-accent transition-colors py-1"
              >
                <span className="text-accent-deep mr-2">{t.n}</span>
                {t.label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <GoldRule />

      {/* ── 01 Positioning ──────────────────────────────────────────── */}
      <Section
        id="positioning"
        eyebrow="01 · Positioning"
        title={
          <>
            What Goldeneye is — and what it deliberately{" "}
            <GoldItalic>is not</GoldItalic>.
          </>
        }
      >
        <p>
          Goldeneye is a <Term>research and decision-support terminal</Term>. It
          synthesizes market data into explainable forecasts, runs
          counterfactual scenarios, simulates paper trades, and keeps a scored
          record of every analytical decision its users log. It was built
          commodity-first — natural gas is the showcase desk, with crude,
          products, and metals alongside — because commodity markets supply the
          richest public fundamental data (EIA storage, CFTC positioning,
          weather) against which honest validation is possible.
        </p>
        <p>
          Three boundaries are architectural, not legal fine print. Goldeneye{" "}
          <Term>never connects to a broker or real-money venue</Term> — the
          paper-trading engine is a self-contained simulator and no such
          integration exists in the codebase. It{" "}
          <Term>never gives personalized financial advice</Term> — every AI
          output passes through a safety layer that rejects advice-shaped
          language before it can reach a screen (§08). And it{" "}
          <Term>never claims certainty</Term> — every forecast ships inside an
          uncertainty envelope with a confidence band, caveats, and its data
          provenance.
        </p>
      </Section>

      <GoldRule />

      {/* ── 02 The problem ──────────────────────────────────────────── */}
      <Section
        id="problem"
        eyebrow="02 · The problem"
        title={
          <>
            Markets grade outcomes. Nobody grades the{" "}
            <GoldItalic>decision</GoldItalic>.
          </>
        }
      >
        <p>
          An analyst who calls a rally at 85% conviction and gets stopped out
          learns almost nothing from the loss alone: good decisions lose all the
          time, and bad ones get paid. The professionally useful signal is not
          the outcome but the <Term>calibration gap</Term> — across all of your
          85% calls, how many actually resolved your way? That number is
          knowable, actionable, and almost never measured, because measuring it
          requires infrastructure: decisions logged before resolution with
          stated conviction, resolved mechanically against real prices with no
          retroactive editing, and bucketed into a reliability curve with honest
          sample-size guardrails.
        </p>
        <p>
          Goldeneye is that infrastructure. The same discipline is applied
          symmetrically: the platform&rsquo;s own models are scored by the same
          machinery as its users&rsquo; judgments, and the results are published
          either way. A tool that grades your judgment is only credible if it
          grades its own first.
        </p>
      </Section>

      <GoldRule />

      {/* ── 03 Doctrine ─────────────────────────────────────────────── */}
      <Section
        id="doctrine"
        eyebrow="03 · Methodology doctrine"
        title={
          <>
            Five commitments, each with an{" "}
            <GoldItalic>enforcement mechanism</GoldItalic> — not a policy
            document.
          </>
        }
      >
        <p>
          Research honesty fails quietly: a synthetic-data property becomes a
          product claim, a failed probe never gets written up, a doc drifts from
          the code it describes. Goldeneye&rsquo;s answer is to make each
          commitment mechanical — something a test can fail.
        </p>
        <div className="flex flex-col gap-8 mt-4">
          <Doctrine
            n="D1"
            title="No claim without provenance."
            body="Every predictive or calibration claim — in code, docs, UI, or a pitch — must state its data provenance: synthetic (measured on seeded data), real-OOS (walk-forward on real market data the model never fit), or real-in-sample (weak, and labeled as such). Synthetic results are demo furniture, never evidence: the seed injects volatility clustering by construction and generates features causally independent of price, so there, `vol is predictable' and `direction is not' are both foregone conclusions before any model runs."
            mechanism="the provenance ledger (docs/MODEL_DILIGENCE.md) — the single source of truth every claim cites"
          />
          <Doctrine
            n="D2"
            title="Gates are pre-registered."
            body="Before any validation probe runs, its acceptance criteria — thresholds, sample-size floors, and how each outcome will be interpreted — are committed to the repository. The probe then runs once against those frozen gates. This removes the researcher's oldest exit: deciding what would have counted as success after seeing the result."
            mechanism="gate documents committed to git before the run; verdicts recorded PASS / FAIL / INSUFFICIENT-N either way"
          />
          <Doctrine
            n="D3"
            title="Walk-forward everything; look-ahead is a bug class."
            body="Every backtest and validation harness reconstructs, for each historical decision date, exactly the information that existed on that date: features flow through symbol-scoped as-of chokepoints keyed to release dates, models refit on trailing windows only, and evaluation windows never overlap with fitting windows. The property is proven, not assumed — a deliberately cheating model that peeks one day ahead must be caught by the test suite, permanently."
            mechanism="the cheating-model proof in CI (tests/test_backtest_lookahead.py) + symbol-scoped context tests against real SQL"
          />
          <Doctrine
            n="D4"
            title="Failures are published at full weight."
            body="A failed probe is a result, not an embarrassment. The validation ledger renders FAIL and INSUFFICIENT-N rows with the same typographic weight as the one edge that passed — because a ledger that only shows wins is marketing, and because the failures are what make the surviving claim believable."
            mechanism="the /validation page renders the full ledger; failed rows are structurally identical to passing rows"
          />
          <Doctrine
            n="D5"
            title="Code and published claims cannot drift apart."
            body="The validation page's ledger rows are anchored to specific markers in the diligence document, and a CI test fails the build if either side changes without the other. The same pattern binds validation harnesses to the live surfaces they validate: the vol-premium probe and the live endpoint call the same function, so the number a test blessed is the number a user sees."
            mechanism="drift-lock tests (code↔doc anchors, shared computation paths) that run in every CI lane"
          />
        </div>
      </Section>

      <GoldRule />

      {/* ── 04 Forecast engine ──────────────────────────────────────── */}
      <Section
        id="forecast-engine"
        eyebrow="04 · The forecast engine"
        title={
          <>
            Four transparent voters, one ensemble — and direction framed as{" "}
            <GoldItalic>views</GoldItalic>, because that is what the evidence
            supports.
          </>
        }
      >
        <p>
          Directional signals come from an ensemble of four deliberately simple,
          fully inspectable models: a <Term>moving-average directional</Term>{" "}
          read, a <Term>Holt trend</Term> model (pure-numpy exponential trend),
          a <Term>factor composite</Term> (a transparent rules-based blend of
          storage surprise, positioning, and momentum with hand-set weights),
          and a <Term>walk-forward logistic regression</Term> — the one
          genuinely trained voter, refit on each call from only past closes so
          it is look-ahead-safe by construction. Each voter reports direction
          plus its supporting and contradicting factors; the ensemble vote
          derives a coarse confidence band from agreement, down-modulated by
          predicted range width, and each model&rsquo;s weight is scaled by its
          own persisted calibration record — chronically overconfident models
          are automatically down-weighted. A volatility-regime classifier stamps
          context (calm / normal / elevated / crisis) on every row but does not
          vote. Per-asset-class configuration parameterizes thresholds and bands
          so the same engine runs natural gas, crude, metals, an equity index,
          and rates without commodity constants leaking across classes.
        </p>
        <p>
          The honest frame, and the part that distinguishes this engine from
          most forecast products:{" "}
          <Term>
            every directional model in the lineup has been tested walk-forward
            on roughly a decade of real prices, and none earned an edge
          </Term>
          . Price-only models scored below a drift-aware naive baseline across
          all tested horizon-commodity cells; feeding fourteen years of real
          CFTC positioning and EIA storage into the factor model made it
          measurably worse, not better; and no model produced a usable
          confidence gradient. Rather than tuning until something flattered, the
          terminal encodes the finding: direction surfaces are labeled views
          with attributed reasoning — useful as structured argument, never sold
          as probability.
        </p>
      </Section>

      <GoldRule />

      {/* ── 05 Vol engine ───────────────────────────────────────────── */}
      <Section
        id="vol-engine"
        eyebrow="05 · The volatility &amp; range engine"
        title={
          <>
            The one validated edge: <GoldItalic>calibrated ranges</GoldItalic>,
            measured the hard way.
          </>
        }
      >
        <p>
          Volatility clusters; tomorrow&rsquo;s turbulence is forecastable from
          today&rsquo;s in a way tomorrow&rsquo;s direction is not. Goldeneye
          turns that one durable regularity into its core quantitative product:
          a forward <Term>price-range band</Term> at stated coverage. The
          estimator stack is an EWMA baseline and a <Term>log-space HAR</Term>{" "}
          model (heterogeneous autoregression over daily, weekly, and monthly
          realized-vol components, fit in logs so vol explosions cannot
          over-extrapolate) — log-HAR won the pre-registered walk-forward
          comparison and is the default, with EWMA selectable. Band quantiles
          are <Term>empirical</Term>, learned walk-forward from each
          series&rsquo; own scaled-return distribution rather than assumed
          normal, which is what makes the fat-tailed 95% band honest.
        </p>
        <p>
          The claim is measured as coverage: on ~10 years of real daily prices
          across six commodities, walk-forward with no tuning on the evaluation
          data, the 80% band covers 78–81% of realized outcomes and the 95% band
          93–95%; the vol forecast correlates 0.44–0.59 with subsequent realized
          volatility at the one-week horizon. Two things are true at once and
          the platform says both: these numbers are{" "}
          <Term>real, replicated, and out-of-sample</Term> — and vol
          autocorrelation is <Term>table stakes</Term>, a known market fact
          rather than proprietary alpha. The differentiation is not a secret
          signal; it is that the stated coverage is actually true, continuously
          re-measurable, and presented with its provenance.
        </p>
      </Section>

      <GoldRule />

      {/* ── 06 Data layer ───────────────────────────────────────────── */}
      <Section
        id="data-layer"
        eyebrow="06 · The data layer"
        title={
          <>
            Adapters, as-of context, and archives that{" "}
            <GoldItalic>accumulate toward</GoldItalic> future claims.
          </>
        }
      >
        <p>
          All external data flows through protocol-based adapters — market
          prices (delayed), EIA storage, CFTC Commitments of Traders, NWS
          weather, and RSS news — each with a mock twin that returns realistic
          fixtures, so the full system runs with zero keys and real sources drop
          in behind the same interface via environment config. Provenance is{" "}
          <Term>observed, not configured</Term>: the platform inspects what the
          database actually holds (real rows, fresh within release cadence)
          rather than trusting its own settings, after a live incident in which
          an upstream vendor silently renamed a field and a &ldquo;real&rdquo;
          adapter fell back to mock without saying so. Feature queries are{" "}
          <Term>symbol-scoped and as-of dated</Term>: a backtest for crude can
          only ever see crude&rsquo;s positioning as it stood on the decision
          date — a correctness class the test suite guards with red-proof tests.
        </p>
        <p>
          Where a claim cannot be tested yet, the platform builds the evidence
          base instead of guessing: immutable, insert-only{" "}
          <Term>vintage archives</Term> snapshot the weather forecast and the
          futures curve daily, source-labeled, because forecast features can
          only be validated against what was forecast at the time — an archive
          you cannot reconstruct later. Each archive carries a pre-registered
          re-entry gate and a visible clock in the terminal&rsquo;s admin view.
        </p>
      </Section>

      <GoldRule />

      {/* ── 07 Decision intelligence ────────────────────────────────── */}
      <Section
        id="decision-intelligence"
        eyebrow="07 · Decision intelligence"
        title={
          <>
            The instrument turned on the <GoldItalic>analyst</GoldItalic>: a
            scored, tamper-evident record of judgment.
          </>
        }
      >
        <p>
          The decision journal is the product&rsquo;s center of gravity. A
          logged thesis captures hypothesis, evidence, stated conviction,
          planned action, risk factors, and invalidation criteria; an
          auto-resolution loop scores it against real prices at its horizon with
          no retroactive editing. Resolved entries feed a{" "}
          <Term>reliability diagram</Term> — claimed conviction bucketed against
          realized hit rate — which is the calibration mirror most analysts have
          never seen. A parallel <Term>append-only decision ledger</Term>{" "}
          shadows every journal row with a SHA-256 hash chain and
          database-trigger immutability: the compliance-grade answer to
          &ldquo;at the moment of decision, what exactly did you know?&rdquo;
        </p>
        <p>
          On top of the scored record sit deliberately conservative judgments.
          The <Term>skill-vs-luck verdict</Term> asks whether a desk&rsquo;s
          hit-rate confidence interval clears a coin flip and refuses to crown
          streaks — blind momentum and random desks read &ldquo;luck&rdquo; by
          design, which is the test working. An LLM{" "}
          <Term>decision-quality coach</Term> mines resolved entries for the
          patterns in wins versus misses, and a devil&rsquo;s-advocate reviewer
          steelmans the opposite of any thesis — both constrained to critique
          process, never to endorse trades. The public demo runs a fictional,
          clearly labeled sample analyst whose banner figure is derived from the
          same live calibration endpoint the page renders, so even the marketing
          copy cannot drift from the data.
        </p>
      </Section>

      <GoldRule />

      {/* ── 08 AI layer ─────────────────────────────────────────────── */}
      <Section
        id="ai-layer"
        eyebrow="08 · The AI layer"
        title={
          <>
            Language models with a <GoldItalic>containment system</GoldItalic>.
          </>
        }
      >
        <p>
          LLMs do what they are good at — summarizing market state, explaining
          signal reasoning, narrating scenarios, critiquing theses, coaching
          decision quality, extracting structure from news — and are
          architecturally prevented from doing what they must not. Every call
          flows through a single explainer module (one choke point, cacheable,
          swappable). Prompts carry a persona contract with a hard-banned phrase
          list — every promissory and advice-shaped construction the behavior
          contract enumerates — require inference to be marked as inference,
          require at least one contradicting consideration with any directional
          view, and name the instrument explicitly so a model can never guess
          the commodity from a price level. Every output then passes a{" "}
          <Term>safety envelope</Term> that attaches confidence, caveats,
          timestamp, and disclaimer — and runs a forbidden-phrase scan that
          rejects the text outright rather than let advice-shaped language reach
          a screen. Rejections are counted, alerted, and surfaced in the admin
          view.
        </p>
      </Section>

      <GoldRule />

      {/* ── 09 Architecture ─────────────────────────────────────────── */}
      <Section
        id="architecture"
        eyebrow="09 · Architecture"
        title={
          <>
            A four-tier system built for <GoldItalic>inspectability</GoldItalic>
            .
          </>
        }
      >
        <p>
          A Next.js 14 frontend (App Router, server components by default) talks
          REST and WebSocket to a FastAPI backend; Postgres with TimescaleDB
          stores time-series in hypertables alongside relational state; Redis
          provides hot-read caching and WebSocket fan-out. The backend enforces
          a strict layering — routers validate and delegate, services own logic,
          repositories own SQL, adapters own the outside world — and every model
          or LLM output crosses the safety wrapper before serialization. Shared
          API types are{" "}
          <Term>generated from the backend&rsquo;s OpenAPI schema</Term>, with a
          CI lane that fails on contract drift, so the frontend cannot quietly
          disagree with the API about shapes.
        </p>
        {/* 4-up only ≥lg — at md the prose container is ~512px (the U-trap). */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 my-4">
          {STACK.map((row) => (
            <div
              key={row.label}
              className="border border-line-1 bg-surface-1 p-4 flex flex-col gap-1.5"
            >
              <span className="font-mono text-[11px] uppercase tracking-eyebrow text-accent">
                {row.label}
              </span>
              <span className="font-mono text-sm text-ink-1">{row.value}</span>
              <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-4">
                {row.detail}
              </span>
            </div>
          ))}
        </div>
        <p>
          Verification is layered the same way: ~1,000 backend tests and ~430
          frontend tests behind a single health gate (lint, typecheck, and tests
          across both stacks); a database-integration CI lane that runs
          migrations and isolation tests against a real TimescaleDB container;
          the contract-drift lane; the drift-lock tests of §03; and a{" "}
          <Term>UI audit harness</Term> that renders every page at seven
          viewport widths and fails on overlap, spill, or clipped content — the
          definition of done for any UI change. Migrations go through Alembic
          only; observability is a request-ID structured log line, a Prometheus
          metrics endpoint, and safety-violation alerting.
        </p>
      </Section>

      <GoldRule />

      {/* ── 10 Results ──────────────────────────────────────────────── */}
      <Section
        id="results"
        eyebrow="10 · Results"
        title={
          <>
            The verdict table, condensed — failures{" "}
            <GoldItalic>included</GoldItalic>.
          </>
        }
      >
        <p>
          Every row below is a pre-registered, walk-forward test on real market
          data, summarized as of July 2026. The terminal&rsquo;s{" "}
          <Link
            href="/validation"
            className="text-accent hover:text-accent-bright"
          >
            validation page
          </Link>{" "}
          renders the full drift-locked ledger with live numbers and the exact
          command that reproduces each verdict.
        </p>
        <div className="flex flex-col border-t border-line-1 mt-2">
          {RESULTS.map((row) => (
            <div
              key={row.claim}
              className="flex flex-col gap-1 border-b border-line-1 py-4 sm:flex-row sm:items-baseline sm:gap-4"
            >
              <span
                className={`inline-block w-fit whitespace-nowrap rounded-sm border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ${row.cls}`}
              >
                {row.badge}
              </span>
              <div className="min-w-0">
                <p className="text-sm text-ink-1">{row.claim}</p>
                <p className="mt-0.5 text-[12px] leading-relaxed text-ink-3">
                  {row.result}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <GoldRule />

      {/* ── 11 Limitations ──────────────────────────────────────────── */}
      <Section
        id="limitations"
        eyebrow="11 · Limitations &amp; roadmap"
        title={
          <>
            What this system <GoldItalic>cannot</GoldItalic> do, in its own
            words.
          </>
        }
      >
        <p>
          Goldeneye has no directional edge and does not pretend otherwise —
          that finding is now backed by real-data testing of every model in the
          lineup, including with real positioning and storage features. Its
          validated edge, calibrated ranges, rests on a market regularity every
          quantitative desk knows; the platform&rsquo;s differentiation is
          honesty infrastructure, not secret alpha. The cross-asset
          configurations for the equity-index and rates classes are hand-set
          plausible scales proving engine portability, not validated
          calibrations — and they are labeled as such. LLM narratives, however
          constrained, remain generative text and carry their envelopes for a
          reason.
        </p>
        <p>
          The forward path is deliberately evidence-gated rather than
          feature-gated. The weather vintage archive unlocks a degree-day
          forecast probe once it spans a winter (~January 2027). The vol-premium
          timing result — promising on two of three asset pairs, not crowned —
          earns a re-run against its original gate on a year of new data (~July
          2027). The curve archive matures into a cross-sectional carry test at
          roughly two years (~mid-2028). Each gate is pre-registered now, while
          the outcome is unknown — which is the only time a gate is worth
          anything.
        </p>
      </Section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-line-1 px-8 md:px-32 py-10 max-w-[1400px] mx-auto flex flex-col gap-6">
        <p className="max-w-[80ch] text-[13px] leading-relaxed text-ink-3">
          Goldeneye is a research and decision-support terminal. It does not
          provide personalized financial advice, does not execute trades against
          real brokers, and does not guarantee any forecast or scenario. Paper
          trading is simulated. For research, education, and decision-quality
          practice only.
        </p>
        <div className="flex flex-wrap items-center justify-between gap-4 font-mono text-[11px] uppercase tracking-eyebrow text-ink-4">
          <span>© 2026 Goldeneye Capital · Chicago, IL</span>
          <div className="flex items-center gap-6">
            <Link
              href="/validation"
              className="hover:text-accent transition-colors"
            >
              Validation ledger
            </Link>
            <Link
              href="/dashboard"
              className="hover:text-accent transition-colors"
            >
              Enter Terminal →
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}

// ── content data ─────────────────────────────────────────────────────────

const TOC = [
  { n: "01", id: "positioning", label: "Positioning" },
  { n: "02", id: "problem", label: "The problem" },
  { n: "03", id: "doctrine", label: "Doctrine" },
  { n: "04", id: "forecast-engine", label: "Forecast engine" },
  { n: "05", id: "vol-engine", label: "Vol & range engine" },
  { n: "06", id: "data-layer", label: "Data layer" },
  { n: "07", id: "decision-intelligence", label: "Decision intelligence" },
  { n: "08", id: "ai-layer", label: "AI layer" },
  { n: "09", id: "architecture", label: "Architecture" },
  { n: "10", id: "results", label: "Results" },
  { n: "11", id: "limitations", label: "Limitations" },
];

const STACK = [
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
  {
    label: "Cache / WS",
    value: "Redis",
    detail: "Hot reads · pub/sub fan-out",
  },
  {
    label: "Contracts",
    value: "OpenAPI",
    detail: "Generated TS types · drift CI",
  },
  {
    label: "Migrations",
    value: "Alembic",
    detail: "One source of DDL truth",
  },
  {
    label: "Intelligence",
    value: "Claude",
    detail: "Single choke point + safety",
  },
  {
    label: "Verification",
    value: "CI × 4 lanes",
    detail: "Health · DB · contracts · UI audit",
  },
];

// Condensed from docs/MODEL_DILIGENCE.md, dated 2026-07. The /validation page
// is the live, drift-locked source; badge classes mirror VerdictTag.tsx.
const RESULTS = [
  {
    badge: "edge · real-oos",
    cls: "border-up/40 bg-up/10 text-up",
    claim: "80% / 95% price-range bands are calibrated",
    result:
      "Walk-forward coverage 78–81% and 93–95% across six commodities, ~10 years of real daily prices; forward-vol correlation 0.44–0.59 at 1w.",
  },
  {
    badge: "edge · real-oos",
    cls: "border-up/40 bg-up/10 text-up",
    claim: "log-HAR beats the EWMA incumbent as vol estimator",
    result:
      "≈ +0.05 R² out-of-sample (5/6 commodities at 1w) on the pre-registered gate — promoted to default. Its raw-variance sibling failed the same gate and is benched.",
  },
  {
    badge: "no edge · tested",
    cls: "border-down/40 bg-down/10 text-down",
    claim: "Directional prediction (all four voters + ensemble)",
    result:
      "Below a drift-aware naive baseline across all tested cells on ~10y real data; real COT + storage features made the factor model measurably worse (~6 SE). Direction ships as labeled views.",
  },
  {
    badge: "no edge · tested",
    cls: "border-down/40 bg-down/10 text-down",
    claim: "Curve carry as a timing signal; storage-surprise event edge",
    result:
      "Carry: adequately powered and failed. Storage-day: premise absent — the seasonal-norm surprise doesn't move price even on release day. Both verdicts published.",
  },
  {
    badge: "promising",
    cls: "border-conf-medium/40 bg-conf-medium/10 text-conf-medium",
    claim: "Vol-premium timing (forecast-RV vs implied-vol spread)",
    result:
      "Passes its gate on 2 of 3 asset pairs (crude, equities; gold fails). Surfaced descriptively behind a live ship-gate — not crowned until the pre-registered re-run.",
  },
  {
    badge: "collecting",
    cls: "border-cyan/40 bg-cyan/10 text-cyan",
    claim: "Weather & futures-curve feature archives",
    result:
      "Untestable claims say so. Immutable daily vintages accumulate toward dated, pre-registered validation gates (~2027–2028).",
  },
];
