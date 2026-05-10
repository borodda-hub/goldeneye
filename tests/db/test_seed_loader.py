"""Verifies that fixture JSON loads without error on a fresh migrated DB."""
import pytest
import sys
import os


@pytest.mark.asyncio
async def test_load_fixtures_runs_clean(migrated_url, tmp_path):
    os.environ["DATABASE_URL"] = migrated_url
    sys.path.insert(0, ".")
    from apps.api.seeds.load_fixtures import load_all
    await load_all()
