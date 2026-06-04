"""Pattern-recognition services.

Phase 21: candlestick patterns. Detectors are deterministic geometric rules on
OHLC bars — descriptive observations of recent price action, NOT trade signals.
Output is framed as research (safety envelope + desk-analyst voice).
"""
from apps.api.services.patterns.candlestick import detect_patterns

__all__ = ["detect_patterns"]
