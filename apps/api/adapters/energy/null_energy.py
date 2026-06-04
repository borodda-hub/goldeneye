"""Null energy adapter — honest "no fundamentals" for non-energy instruments.

Metals (GC, SI, …) and other asset classes have no EIA-style weekly inventory
report. Rather than fall back to natural-gas storage (which would inject a bogus
alt-data feature into their signal path), the registry routes them here. Both
methods return empty results, so consumers degrade to "no storage data" cleanly
without a 500 and without wrong-instrument data.
"""
from __future__ import annotations

from typing import Any


class NullEnergyAdapter:
    """Conforms to EnergyDataAdapter; always returns empty."""

    async def get_storage_reports(self, limit: int = 100) -> list[dict[str, Any]]:
        return []

    async def get_latest_storage(self) -> dict[str, Any] | None:
        return None
