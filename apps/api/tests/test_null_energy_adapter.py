"""Phase 17 — NullEnergyAdapter + registry energy routing.

Non-energy instruments (metals, grains, …) must get an empty energy adapter
so their signal path never picks up bogus gas-storage alt-data and never 500s.
"""
from __future__ import annotations

import pytest

from apps.api.adapters.energy.null_energy import NullEnergyAdapter
from apps.api.adapters.registry import get_energy


async def test_null_adapter_returns_empty():
    adapter = NullEnergyAdapter()
    assert await adapter.get_latest_storage() is None
    assert await adapter.get_storage_reports() == []


@pytest.mark.parametrize("symbol", ["GC", "SI", "HG", "ZC", "ES", "ZZZ"])
def test_non_energy_symbols_route_to_null(symbol):
    """Metals/grains/index/unknown → NullEnergyAdapter regardless of mode."""
    assert isinstance(get_energy(symbol), NullEnergyAdapter)


def test_energy_symbols_do_not_route_to_null():
    """NG and the petroleum products must NOT get the null adapter."""
    for symbol in ("NG", "CL", "HO", "RB"):
        assert not isinstance(get_energy(symbol), NullEnergyAdapter)
