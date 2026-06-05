from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from apps.api.src.settings import settings

_engine: AsyncEngine | None = None

# libpq-style query params that asyncpg does not understand and must be
# stripped from the URL (TLS is requested via connect_args instead).
_LIBPQ_ONLY_PARAMS = (
    "sslmode",
    "ssl",
    "channel_binding",
    "sslrootcert",
    "sslcert",
    "sslkey",
    "gssencmode",
)


def prepare_async_url(url: str) -> tuple[str, dict[str, object]]:
    """Normalize a Postgres URL for SQLAlchemy's asyncpg driver.

    Managed Postgres (Timescale Cloud, Neon, …) hands out libpq-style URLs like
    ``postgres://user:pass@host:port/db?sslmode=require``. asyncpg uses a
    different scheme name and does not understand ``sslmode`` /
    ``channel_binding`` query params, so we:

    * rewrite a bare ``postgres`` / ``postgresql`` scheme to
      ``postgresql+asyncpg``,
    * strip libpq-only query params, and
    * enable TLS via ``connect_args={"ssl": True}`` when the URL asked for it
      (``sslmode=require`` / ``verify-*``) or ``DATABASE_SSL`` is set.

    Returns the cleaned URL and the connect_args for ``create_async_engine``.
    Local / compose URLs (no ``sslmode``, ``database_ssl=False``) pass through
    with empty connect_args, so dev behaviour is unchanged.
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    query = dict(parse_qsl(parts.query))
    sslmode = query.get("sslmode")
    for key in _LIBPQ_ONLY_PARAMS:
        query.pop(key, None)

    want_ssl = settings.database_ssl or (
        sslmode in ("require", "verify-ca", "verify-full")
    )

    clean = urlunsplit(
        (scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    connect_args: dict[str, object] = {"ssl": True} if want_ssl else {}
    return clean, connect_args


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url, connect_args = prepare_async_url(settings.database_url)
        _engine = create_async_engine(
            url,
            echo=settings.debug,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _engine
