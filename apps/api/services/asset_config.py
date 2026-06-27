"""Phase B5 — per-asset-class engine configuration (single source of constants).

The forecast→decision→resolution loop was hard-tuned to natural-gas microstructure
with constants scattered across the voters, the ensemble, the deadband, and the
paper engine. B5 lifts them here, keyed by ``Instrument.asset_class``.

`commodity` holds **today's exact values, verbatim** — the byte-identical golden
lock (`tests/test_asset_config_golden.py`) proves the refactor changed no existing
behaviour. `metal` and any unknown class fall back to `commodity` via `config_for`.

`index` (equities) and `rates` (treasuries) are **hand-set, UNVALIDATED** scales —
plausible volatility/threshold magnitudes for those markets, not calibrated or
backtested. They are recorded as `unvalidated` in `docs/MODEL_DILIGENCE.md`. B5 is a
portability phase: it proves the loop *runs* cross-asset with no commodity hardcode
leaking — NOT that it predicts equities or rates.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VolRegimeBands:
    """Annualized-realized-vol cutoffs → compressed/normal/elevated/crisis."""

    compressed: float = 0.25
    normal: float = 0.45
    elevated: float = 0.70


@dataclass(frozen=True)
class MaConfig:
    cross_up: float = 1.002       # sma20 > sma50 * cross_up → bullish
    cross_down: float = 0.998     # sma20 < sma50 * cross_down → bearish
    spread_high: float = 0.01     # |spread| > spread_high → high confidence
    spread_medium: float = 0.005
    amplify: float = 2.0          # expected_pct = (sma20/sma50 - 1) * amplify
    range_normal: float = 0.02    # ± range half-width, normal/compressed regimes
    range_elevated: float = 0.04  # ± range half-width, elevated/crisis regimes


@dataclass(frozen=True)
class HoltConfig:
    min_closes: int = 30
    neutral_band: float = 0.001   # |expected_pct| <= neutral_band → neutral
    snr_high: float = 1.5
    snr_medium: float = 0.7


@dataclass(frozen=True)
class FactorConfig:
    storage_weight: float = 0.4
    cot_weight: float = 0.3
    momentum_weight: float = 0.3
    expected_pct: float = 0.005   # directional ± expected move
    range_pct: float = 0.02       # ± fixed range half-width


@dataclass(frozen=True)
class LogregConfig:
    direction_up: float = 0.55    # p_up >= direction_up → bullish
    direction_down: float = 0.45  # p_up <= direction_down → bearish
    edge_high: float = 0.15       # |p_up - 0.5| >= edge_high → high confidence
    edge_medium: float = 0.07
    lr: float = 0.3
    iters: int = 400
    min_train_rows: int = 24


@dataclass(frozen=True)
class EnsembleBand:
    """Band-width cutoffs for the LLM-envelope confidence down-modulation (A2).

    Golden-neutral (not part of compute_ensemble's output) but threaded per-class so
    an ES/ZN decision's narrative envelope isn't judged against NG-scale band widths.
    """

    wide: float = 0.10
    very_wide: float = 0.18


@dataclass(frozen=True)
class AssetClassConfig:
    vol_regime_bands: VolRegimeBands = field(default_factory=VolRegimeBands)
    ma: MaConfig = field(default_factory=MaConfig)
    holt: HoltConfig = field(default_factory=HoltConfig)
    factor: FactorConfig = field(default_factory=FactorConfig)
    logreg: LogregConfig = field(default_factory=LogregConfig)
    ensemble_band: EnsembleBand = field(default_factory=EnsembleBand)
    default_deadband: float = 0.003


# ── The class table ──────────────────────────────────────────────────────────
# commodity == today's exact NG-tuned values (all defaults). DO NOT change these
# without re-capturing the golden baseline — the lock will (correctly) go red.
_COMMODITY = AssetClassConfig()

# index (equities, e.g. ES) — HAND-SET, UNVALIDATED. Equity index vol runs lower and
# tighter than gas: ~12–18% annualized, sub-1% typical daily moves.
_INDEX = AssetClassConfig(
    vol_regime_bands=VolRegimeBands(compressed=0.10, normal=0.18, elevated=0.30),
    ma=MaConfig(
        cross_up=1.001, cross_down=0.999, spread_high=0.005, spread_medium=0.0025,
        amplify=2.0, range_normal=0.012, range_elevated=0.025,
    ),
    holt=HoltConfig(min_closes=30, neutral_band=0.0005, snr_high=1.5, snr_medium=0.7),
    factor=FactorConfig(
        storage_weight=0.4, cot_weight=0.3, momentum_weight=0.3,
        expected_pct=0.003, range_pct=0.012,
    ),
    logreg=LogregConfig(),
    ensemble_band=EnsembleBand(wide=0.06, very_wide=0.12),
    default_deadband=0.002,
)

# rates (treasuries, e.g. ZN) — HAND-SET, UNVALIDATED. Treasury futures vol is very
# low: ~4–8% annualized, tiny daily moves around par.
_RATES = AssetClassConfig(
    vol_regime_bands=VolRegimeBands(compressed=0.04, normal=0.08, elevated=0.14),
    ma=MaConfig(
        cross_up=1.0005, cross_down=0.9995, spread_high=0.003, spread_medium=0.0015,
        amplify=2.0, range_normal=0.006, range_elevated=0.012,
    ),
    holt=HoltConfig(min_closes=30, neutral_band=0.0003, snr_high=1.5, snr_medium=0.7),
    factor=FactorConfig(
        storage_weight=0.4, cot_weight=0.3, momentum_weight=0.3,
        expected_pct=0.0015, range_pct=0.006,
    ),
    logreg=LogregConfig(),
    ensemble_band=EnsembleBand(wide=0.03, very_wide=0.06),
    default_deadband=0.001,
)

CONFIGS: dict[str, AssetClassConfig] = {
    "commodity": _COMMODITY,
    "index": _INDEX,
    "rates": _RATES,
}

# The default everything falls back to — commodity == today's behaviour.
DEFAULT = _COMMODITY


def config_for(asset_class: str | None) -> AssetClassConfig:
    """Resolve an asset_class to its config; unknown / None / metal → commodity."""
    if not asset_class:
        return DEFAULT
    return CONFIGS.get(asset_class, DEFAULT)
