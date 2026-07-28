# Phase C — The Concierge (grounded assistant + research synthesis)

_Committed before build. Owner directive: "the Concierge assistant might be the key. A
research assistant, a how to guide, a teacher, explainer" + "add in a bit more research
capability / ability to synthesize new information that might not have hit our models
yet. We are soft on real time news integration."_

## Thesis

The platform's depth (validation ledger, calibration loop, vol engine, white paper) is
illegible to a first-time user. The concierge converts that depth into conversation —
**grounded in what the platform actually is, honest about what it can't do**. A generic
chatbot would be a commodity feature and a safety liability; the differentiated version
answers from our own curated knowledge, reads the current screen's live data, and
synthesizes minutes-fresh headlines the models haven't ingested — with that freshness
labeled explicitly.

## Tiers

- **C1 — grounded explainer (this build):** floating widget on all app screens.
  Answers "what am I looking at / how does X work / why does it say no edge" from a
  **curated knowledge pack** (`services/concierge_pack.md`) distilled from the white
  paper + MODEL_DILIGENCE + AI_BEHAVIOR + feature docs — never from model priors.
  Suggests navigation as links (fixed route map), never drives the browser. Signed-in
  users (Clerk) are greeted by name client-side.
- **C3-lite — research synthesis (this build, per owner):** every reply is assembled
  with **live context**: current price/change, ensemble read + vol band + regime
  (compact snapshot), the provenance caveat, and the **freshest adapter-direct
  headlines** (the RSS layer is minutes-fresh while model/event context is
  persisted+slower — that gap IS the "not yet in our models" capability). Synthesis of
  headline-derived information must carry the label "headline-derived — not yet in
  model inputs." No agentic tool loop yet: server-side context assembly, one LLM call.
- **C2 — teacher flows (staged):** guided curricula ("teach me calibration") integrated
  with the walkthrough system. After C1 telemetry shows what users actually ask.
- **C3-full (staged):** true read-only tool use (concierge chooses which endpoints to
  query, incl. user's own calibration). Requires a tool-loop + per-tool guardrails.

## News-track (owner: "we are soft on real time news")

- **N1 (this build):** the concierge becomes the first *synthesis* consumer of the
  fresh RSS layer (per-symbol multi-source adapter, 10-min cache — already good;
  unsynthesized until now). Headlines injected with ISO timestamps + source ids.
- **N2 (staged):** a market-brief surface ("what changed in the last 24h") + dashboard
  freshness upgrade (dashboard still reads the persisted events table; the adapter-direct
  path is fresher). **N3 (roadmap):** push/event-driven news ticks via the existing WS
  backbone; impact-scored alerts.

## Safety design (the widest surface we've opened — engineered, not hoped)

1. **Same chokepoint:** one new prompt builder + `_call_with_safety_check` (scan +
   strict retry + hard block). Envelope on every reply.
2. **Refusal rules in the task block:** no advice, no position sizing, no "should I
   buy" (redirect to calibration framing), no price targets, direction = views only,
   never claim the platform predicts direction (the ledger says it doesn't).
3. **Injection defense:** user text and headlines are DATA inside delimited blocks; the
   task block instructs that nothing inside them can change the rules. Locked by
   prompt-builder unit tests.
4. **Knowledge-pack drift-lock:** anchor facts (coverage numbers, no-edge verdict,
   disclaimer posture) must match MODEL_DILIGENCE.md — CI test fails on divergence.
5. **Cost/abuse:** in-memory sliding-window rate limit per client (20 msg/hr),
   `max_tokens` capped, history truncated server-side (last 8 turns), message length
   capped. Model = the standard smart tier (quality matters on a public demo; the
   limiter bounds spend).

## Build list (C1 + C3-lite + N1)

**Backend:** `services/concierge_pack.md` (knowledge pack) · `services/concierge.py`
(live-context assembly + orchestration) · `concierge_messages` in `llm_prompts.py` ·
`routers/concierge.py` (`POST /v1/concierge/chat`) · rate limiter · tests (pack
drift-lock, prompt injection/refusal content, router happy-path + limit + safety).

**Frontend:** `components/concierge/ConciergeWidget.tsx` (floating launcher bottom-right,
panel with thread, InlineMarkdown rendering, envelope note, suggestion links, Clerk
greeting, route+symbol awareness via `usePathname` + `useActiveInstrument`) · mount in
the app layout (all app screens; not landing/about) · `lib/api.ts` types + POST ·
contracts regen · widget tests.

**DoD:** `pnpm health` exit 0 · contracts check green · `ui:audit` clean (widget closed
by default; open-state manual visual at 3 widths) · PR → develop → master → prod verify
(live chat round-trip on prod, refusal probe by hand).
