# Phase B5 — Cross-asset portability

## Context

NGTI's forecast→decision→resolution→calibration loop (the product's moat) is hard-tuned to natural-gas microstructure: vol-regime bands, MA/Holt/factor/logreg thresholds, ensemble band-widths, the deadband default, and the paper-engine tick value are scattered NG constants across ~8 modules. MASTER_PLAN.md §B5 calls for lifting these into one per-asset-class config, with the commodity entry holding today's exact values so every existing asset stays byte-identical, then proving portability by running the full loop on two genuinely non-commodity classes: ES (E-mini S&P 500 future, asset_class:"index") and ZN (10y Treasury future, asset_class:"rates").

This is a portability/architecture phase, not a predictive-edge claim. The index/rates config values are hand-set, unvalidated defaults (recorded as such in MODEL_DILIGENCE.md, exactly like factor_composite). DoD = "the full loop runs cleanly on a non-commodity asset with no commodity hardcode leaking, and existing assets are unchanged" — not "we predict equities."

Branch: feat/phase-b5-cross-asset. Commit this plan as docs/PHASE_B5_PLAN.md before code.

## Verified against the code this session

- Instrument already has asset_class (default "commodity"), contract_size, tick_size, currency, metadata_ (models/orm/instruments.py). No migration. metal is already a live asset_class (GC/SI) — it must keep working via the commodity fallback (below).
- ES fully scaffolded already: instruments.json has ES (asset_class:"index", contract_size:50, metadata.yahoo_ticker:"ES=F"); contracts.json has front-month ESU26; Yahoo map has "ES": ".CME". No ES bars seeded. Real top-level yahoo_ticker is null for every instrument — the live ticker lives in metadata.yahoo_ticker.
- ZN not seeded: absent from instruments.json/contracts.json and from the Yahoo exchange-suffix map (yahoo_delayed.py). Needs a fixture instrument + front-month + one map row.
- NG hardcodes to lift: regime bands 0.25/0.45/0.70 (moving_average_directional.classify_vol_regime, re-exported by volatility_regime.classify); MA direction 1.002/0.998, confidence 0.01/0.005, amplify ×2.0, range 0.02/0.04 (moving_average_directional.predict); Holt _NEUTRAL_BAND=0.001, SNR 1.5/0.7 (holt_trend); factor weights .4/.3/.3 + expected ±0.005 + range ±0.02 (factor_composite); logreg thresholds .55/.45, edges .15/.07, _LR/_ITERS/_MIN_TRAIN (logreg_directional); ensemble band-widths 0.10/0.18 (ensemble._WIDE/_VERY_WIDE_BAND_PCT); deadband 0.003 (signal_scoring.score_forecast); tick value NG_TICK_VALUE_USD=10_000 (paper_engine).
- run_all(ctx) calls each voter as predict(ctx.closes, "1d") and classify_regime(ctx.closes) (model_registry.py). factor_composite already no-ops storage/COT when None → index/rates degrade to momentum-only (honest), no crash.
- vol_range.py is left alone: its bands are empirical walk-forward quantiles (proven to generalize across 6 commodities in the 30a/b diligence) — it self-adapts per series. Not parameterized.
- 8 ForecastContext(...) build sites: routers/{signals,dashboard,explain,signal_quality,scenarios}.py and services/ledger.py all have the instrument object loaded; services/backtest.py (the S3 proof path) and a test only have symbol.
- Paper engine uses the NG constant in 3 places beyond compute_pnl's default param: validate_open (notional), close_trade (PnL), equity_curve (open-MTM). repos/instruments.py already has get_by_id.
- Honest-degradation gaps: rss._make_default_config falls back to a generic Yahoo feed (acceptable, but should carry an explicit reason); web scenarioGeo.buildGlobeLayers and ShockBuilder.shockTypesFor fall back to NG for anything not BZ/NG → ES/ZN would render the Henry-Hub globe + NG shocks (the real honesty bug). Fundamentals/positioning already return empty for non-energy.

## Design — the config-injection flow

Instrument.asset_class → config_for(asset_class) → fallback → CONFIGS["commodity"] (metal, anything unknown) == today's exact constants. ForecastContext(asset_class="commodity") --post_init--> ctx.cfg : AssetClassConfig. run_all(ctx) passes cfg=ctx.cfg to each voter (ma/holt/factor/logreg/classify_regime) — voters read cfg.* instead of module constants, LOGIC UNCHANGED. compute_ensemble reads band-widths from cfg. signal_scoring.score_forecast uses cfg.default_deadband when caller passes none. paper_engine tick value = instrument.contract_size (NG 10000, ES 50, ZN 1000).

Default asset_class="commodity" is the safety mechanism: every un-updated caller (backtest S3 path, tests) resolves to CONFIGS["commodity"] and stays byte-identical. Only instrument-aware callers opt into a real class.

### 1. apps/api/services/asset_config.py (new) — single source of per-class constants
- @dataclass(frozen=True) AssetClassConfig bundling every lifted constant, grouped by model: vol_regime_bands (compressed/normal/elevated cutoffs), ma (cross/spread/amplify/range-widths), holt (neutral_band, snr_high, snr_med), factor (weights, expected_pct, range), logreg (thresholds, edges, lr, iters, min_train), ensemble_band (wide, very_wide), default_deadband.
- CONFIGS: dict[str, AssetClassConfig] = commodity (today's values, lifted verbatim), index, rates. config_for(asset_class: str) -> AssetClassConfig → CONFIGS.get(ac, CONFIGS["commodity"]).
- The old module-level constants in each model file are replaced by reads of the passed cfg, so there is exactly one source and no drift. commodity values are the only ones that must equal the originals (the golden lock proves it); index/rates are hand-set guesses.

### 2. Thread cfg through the engine (parameterize constants; no logic change)
- ForecastContext: add asset_class: str = "commodity"; add non-init cfg set in __post_init__ via config_for(self.asset_class).
- Each voter predict(...) gains a trailing cfg: AssetClassConfig | None = None, defaulting to CONFIGS["commodity"] when None (keeps them independently callable / test-friendly). Bodies read cfg.ma.*, cfg.holt.*, etc. classify_regime/classify_vol_regime take cfg (or its bands). run_all passes cfg=ctx.cfg to all five calls. No model arithmetic changes → S3 look-ahead invariant untouched.
- compute_ensemble: add cfg param (default commodity); read _WIDE/_VERY_WIDE_BAND_PCT from cfg.ensemble_band. Update the 6 instrument-aware callers to pass cfg=ctx.cfg.
- signal_scoring.score_forecast: keep the deadband arg; callers that today pass a per-decision threshold_pct are unchanged — only the default (when none is set) is sourced from config_for(asset_class).default_deadband at the call site.
- Update the 6 instrument-aware ForecastContext build sites to pass asset_class=instrument.asset_class: routers/{signals,dashboard,explain,signal_quality,scenarios}.py + services/ledger.py (captures the decision-time ensemble for journal entries; would otherwise stamp commodity bands on an ES decision). Leave services/backtest.py and the test on the default (commodity) → S3 path byte-identical.

### 3. Paper engine — tick value from contract_size (apps/api/services/paper_engine.py)
- Replace NG_TICK_VALUE_USD usage with the position instrument's contract_size (repos/instruments.get_by_id), at all three sites: open_trade → fetch contract_size by instrument_id, pass into validate_open for the notional; close_trade → fetch by trade.instrument_id, pass tick_value into compute_pnl; equity_curve → resolve contract_size per trade's instrument (cache by instrument_id, mirroring the existing front_month_cache), pass into the open-MTM compute_pnl.
- compute_pnl already takes tick_value; keep the signature, just stop defaulting callers to the NG constant. Keep STARTING_EQUITY_USD/LEVERAGE_CAP as-is.

### 4. Light up ES + ZN (seed/fixtures)
- ES: no scaffolding — just backfill real bars.
- ZN: add to instruments.json (symbol:"ZN", asset_class:"rates", contract_size:1000, tick_size:0.015625, currency:"USD", metadata.yahoo_ticker:"ZN=F", metadata.description:"CBOT 10-Year US Treasury Note Futures"); add front-month ZNU26 to contracts.json (is_front_month:true); add "ZN": ".CBT" to yahoo_delayed._EXCHANGE_SUFFIX_BY_PREFIX.
- Add ES and ZN to backfill_prices.DEFAULT_SYMBOLS (backfill already resolves the contract ticker from the Yahoo map by symbol; both accumulate real bars, no replace_mock).

### 5. Honest degradation for energy-only surfaces (gate, don't build)
- adapters/news/rss.py: keep the generic Yahoo per-symbol feed for unknown symbols but carry an explicit "no curated keyword taxonomy for this asset class" note in the config/source metadata so the feed never presents as NG-curated. (No NG keyword fallback — already the case; the fix is making the absence explicit.)
- Web lib/scenarioGeo.ts: buildGlobeLayers and benchmarkOf currently key on instrument === "BZ" vs gas-default. Introduce a known-taxonomy set {NG, BZ}; for anything else return empty layers and have callers render the unsupported state (no Henry-Hub globe).
- Web components/scenarios/ShockBuilder.tsx: shockTypesFor returns [] for instruments without a taxonomy; render an explicit "No scenario taxonomy for this asset class yet" panel instead of NG shock controls. Thread the same gate through app/(app)/scenarios/ScenariosShell.tsx / ScenarioGlobe.tsx so the page shows the unsupported state for ES/ZN.
- Fundamentals/positioning already return empty for non-energy — add a lock test (below), no code change.
- Equity/rates scenario taxonomy itself is out of scope (deferred phase).

## Tests (new + locks)

1. Golden / byte-identical lock (the critical honest test) — apps/api/tests/test_asset_config_golden.py: on a fixed deterministic synthetic close series, assert each voter's full ForecastResult, the ensemble dict, and the vol_range output for asset_class="commodity" equal expected literals captured from current main before the refactor (capture first, see green, then refactor). Include a metal case (GC-like) to prove the commodity fallback. This is what proves "no existing behavior changed."
2. Full-loop for new classes — parametrized over ES + ZN (test_cross_asset_loop.py): forecast → ensemble → vol/range → journal decision → auto-resolve → calibration runs with no crash, plus no-leak asserts: paper-engine tick value == contract_size (50 / 1000, not 10000); resolved regime band + deadband == the class config, not the NG constant.
3. Honest degradation — fundamentals + positioning return empty for index/rates; web test that shockTypesFor("ES") === [] and buildGlobeLayers([], …, "ES") returns no points/arcs (extend components/scenarios/__tests__/ShockBuilder.test.tsx).
4. S3 re-run — tests/test_backtest_lookahead.py stays green (only constants parameterized; no look-ahead path added). Re-run it explicitly since model files are touched.

## Docs (same-commit, per CLAUDE.md)
- ARCHITECTURE.md: add the per-asset-class config tier. MODEL_DILIGENCE.md: record index/rates configs as unvalidated, hand-set (no edge claimed). MASTER_PLAN.md + HANDOFF.md: B5 status. No SCHEMA.md change (no migration). API_CONTRACTS.md only if a response model changes (none expected — /v1/instruments already returns asset_class).

## Verification (end-to-end)
1. pnpm health green (lint + typecheck + tests, both stacks); run apps/api tests incl. the golden lock and the S3 look-ahead proof.
2. make migrate (no-op) → reseed fixtures (picks up ZN) → python -m apps.api.seeds.backfill_prices ES ZN (real bars via the proxy). For ES and ZN: hit /v1/forecast/range, /v1/signals, create a /v1/journal decision, run /v1/journal/auto-resolve, open /calibration — confirm the loop runs and the tick value / regime bands are the class config.
3. Confirm /v1/fundamentals?symbol=ES and the Scenario Lab show the explicit unsupported state (not NG content). pnpm contracts:check (regen only if a response model changed).

## Promotion
Two-lane work → develop (CI incl. db-tests + contracts) → owner sign-off → fast-forward master.

## Out of scope (defer, don't creep)
Equity/rates scenario taxonomy + 3D globe geography + lean logic; real equity/rates fundamentals and non-CFTC positioning; spot (non-futures) equities; tuning/validating the index/rates config values (they ship hand-set + labeled unvalidated). B5 only makes the existing Scenario Lab and energy surfaces degrade honestly for the new classes.
