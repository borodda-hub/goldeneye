"""Verifies that fixture JSON loads without error on a fresh migrated DB."""
import os
import sys

import pytest


@pytest.mark.asyncio
async def test_load_fixtures_runs_clean(migrated_url, tmp_path):
    os.environ["DATABASE_URL"] = migrated_url
    sys.path.insert(0, ".")

    # Point the app's engine at the migrated testcontainer. `settings` is a
    # module singleton whose database_url is cached at import (default localhost),
    # and get_engine()/get_session_factory() memoize on first use — so without
    # this, load_all() connects to localhost:5432 and fails wherever that isn't a
    # live DB (e.g. CI). Override the cached URL and reset the memoized engine +
    # factory so get_engine() rebuilds against migrated_url.
    import apps.api.db.engine as db_engine
    import apps.api.db.session as db_session
    from apps.api.src.settings import settings as app_settings

    app_settings.database_url = migrated_url
    db_engine._engine = None
    db_session._session_factory = None

    from apps.api.seeds.load_fixtures import load_all
    await load_all()
