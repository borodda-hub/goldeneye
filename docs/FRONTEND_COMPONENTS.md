# docs/FRONTEND_COMPONENTS.md — Frontend Spec

Next.js 14 App Router, TypeScript, Tailwind, Recharts (general charts), Lightweight Charts (candles), TanStack Query.

## §design_principles

- **Institutional, dense, calm.** This is a Bloomberg-adjacent terminal, not a consumer app. Information density is a feature; whitespace serves grouping, not decoration.
- **Numbers are first-class.** Tabular figures, monospace digits, right-aligned, consistent decimal precision per metric.
- **Color is signal, not decoration.** Up = green band, down = red band, neutral = slate. No color used for "primary action" branding; CTA contrast comes from contrast and weight, not hue.
- **Charts are the hero.** Charts get the most pixels on every screen that has one.
- **Disclaimers are visible but not loud.** A persistent footer carries the standard disclaimer string.

## §tokens

Tailwind config in `apps/web/tailwind.config.ts`. Treat these as the only colors — no ad-hoc hex.

**Surface scale (dark, default)**
- `bg-surface-0`   `#0a0d12`   page background
- `bg-surface-1`   `#0f1319`   card background
- `bg-surface-2`   `#161b24`   elevated panel
- `bg-surface-3`   `#1d2330`   hovered / focused
- `border-line-1`  `#2a313e`   hairline borders
- `border-line-2`  `#3a4150`   strong borders

**Text**
- `text-ink-1`     `#e6ebf2`   primary
- `text-ink-2`     `#a7b0bf`   secondary
- `text-ink-3`     `#6b7589`   tertiary / labels
- `text-ink-4`     `#4a5364`   disabled

**Signal colors** (for price up/down, direction)
- `text-up`        `#34d399`   bullish
- `text-down`      `#f87171`   bearish
- `text-flat`      `#94a3b8`   neutral
- `bg-up-soft`     `#0d2820`   bullish band fill
- `bg-down-soft`   `#2c1416`   bearish band fill

**Accent (rarely used; for selected state, key callouts)**
- `text-accent`    `#7dd3fc`
- `bg-accent-soft` `#0c2230`

**Confidence bands**
- `text-conf-low`     `#f59e0b`
- `text-conf-medium`  `#fbbf24`
- `text-conf-high`    `#34d399`

**Type**
- Body: Inter, 14px / 1.5
- Numbers: JetBrains Mono, tabular-nums, 14px / 1.4
- Headers: Inter SemiBold, 16/20/24/32 step
- All number elements use `font-mono tabular-nums` Tailwind classes.

**Spacing**
- 4 / 8 / 12 / 16 / 24 / 32 / 48 — no other values.
- Gutter between cards: 16. Inside cards: 12.

**Radii**
- Cards: `rounded-md` (6px)
- Inputs/buttons: `rounded` (4px)
- No fully rounded pills except for status chips.

## §layout_shell

```
AppShell
├── TopBar               instrument selector, search, alert bell, account
├── SideNav              icon rail: Dashboard / Chart / Signal / Scenario / Journal / Paper / Admin
├── PageContent          per-screen
└── Footer               disclaimer string + connection status
```

`AppShell` is a server component that wraps the route group `(app)/`. Pages are server components that compose client components for interactive parts.

## §screens

### Dashboard `/dashboard`
```
DashboardPage
├── HeaderRow            instrument + last price + change + vol regime chip
├── DirectionalBiasCard  direction + confidence + 1-line LLM summary
├── PriceMiniChart       last 30d daily, sparkline-style with vol shading
├── FuturesCurveCard     curve plot (Recharts)
├── RecentEventsList     last 5 events with category icon and impact bar
└── DashboardLiveBar     live tick indicator + WS connection status
```

### Chart View `/chart`
```
ChartPage
├── ChartToolbar         resolution toggle, overlays toggle, range picker, contract picker
├── PriceChart           Lightweight Charts candles + volume pane + overlays + event markers
├── EventDrawer          collapsible right panel listing events in current view
└── ChartFooter          contract metadata, data source, "as of"
```

### Signal Lab `/signals`
```
SignalLabPage
├── EnsembleHeader       direction, confidence, vol regime, expected range
├── ModelGrid            one card per model: name, horizon, direction, confidence, top supporting/contradicting
├── ExplanationPanel     LLM explanation + caveats
├── HistoryTable         recent forecasts with actual outcome (after-the-fact)
└── DisclaimerFooter     standard disclaimer
```

### Scenario Lab `/scenarios`
```
ScenarioLabPage
├── TemplateGallery      preset shock packages (cold snap, LNG outage, etc.)
├── ShockBuilder         add/remove shocks (weather / lng_export / production / demand / geopolitical)
├── RunButton            POST /v1/scenarios/run
├── ResultPanel          directional pressure + confidence + range + assumptions + counterargs + data needed + narrative
├── ScenarioHistoryList  recent runs, replayable
└── DisclaimerFooter
```

### Decision Journal `/journal`
```
JournalPage
├── EntryList            cards with confidence bar
├── NewEntryForm         hypothesis, evidence rows, confidence slider, planned action, risks, invalidation
├── EntryDetailDrawer    full entry + LLM review (assumption-finding bullets) + linked paper trade if any
└── DisclaimerFooter
```

### Paper Trading `/paper`
```
PaperTradingPage
├── OpenPositionsTable   contract, side, size, entry, mark, stop, take, unrealized PnL
├── ClosedTradesTable    realized PnL summary, with row-level reflection
├── NewTradeForm         contract picker, side, size, entry (mid by default), stop, take, rationale, link-journal
├── EquityCurveChart     simulated equity over time
└── DisclaimerFooter
```

### Admin `/admin`
```
AdminPage
├── DataHealthGrid       per-adapter status / last success / lag
├── ModelHealthGrid      per-model last forecast / sample count
├── AlertsList           unread alerts with ack button
└── EnvironmentBlock     git sha, build time, env vars status (no secrets)
```

## §shared_components

Located in `apps/web/components/`:

- `<NumberCell value={n} unit?={u} delta?={d} />` — formatted with tabular-nums and color band; takes precision from the unit.
- `<DirectionChip dir />` — bullish/bearish/neutral pill.
- `<ConfidenceBar conf />` — three-segment bar with low/medium/high coloring.
- `<EventMarker event />` — used in the Chart View pane and the Recent Events list.
- `<DisclaimerFooter />` — sticky bottom bar carrying `services.safety.DISCLAIMER`.
- `<SafetyEnvelopeNote env />` — small print displaying `as_of`, confidence, and caveats from any envelope.
- `<LiveDot connected />` — small pulsing dot for WS status.

All shared components have a Storybook story in `apps/web/stories/` and a Vitest test in `apps/web/components/__tests__/`.

## §data_layer

- `apps/web/lib/api.ts` — typed REST client, generated against `packages/contracts/`.
- `apps/web/lib/realtime.ts` — single multiplexed WebSocket; exposes `useChannel('price.NG.front')` hook returning the latest message and a connection-status.
- `apps/web/lib/queries.ts` — TanStack Query keys and helpers, one per endpoint family.
- Server components pre-fetch via `fetch` and hydrate; client components subscribe to live updates afterward.

## §accessibility_and_responsiveness

- Color is never the only signal; up/down also use `▲` / `▼` glyphs. Direction chips have a text label.
- Focus states use a 2px outline in `text-accent`.
- Min target dimension for the demo: 1280×800. Mobile is roadmap, not MVP. Pages should not visually break below 1024 but interactive density is not promised.
