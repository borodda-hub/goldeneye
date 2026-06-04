"""Pattern-recognition services.

Phase 21: candlestick patterns. Detectors are deterministic geometric rules on
OHLC bars — descriptive observations of recent price action, NOT trade signals.
Output is framed as research (safety envelope + desk-analyst voice).
"""
from apps.api.services.patterns.candlestick import detect_patterns
from apps.api.services.patterns.chart_patterns import detect_auto_ta

__all__ = ["detect_auto_ta", "detect_patterns"]
