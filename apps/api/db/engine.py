import ssl
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


def _ssl_arg(sslmode: str | None) -> bool | ssl.SSLContext:
    """SSL connect arg matching libpq's ``sslmode`` semantics for asyncpg.

    asyncpg's ``ssl=True`` does *full* verification (CERT_REQUIRED +
    check_hostname), which is stricter than libpq's ``require`` ("encrypt but
    don't verify"). Managed providers (Timescale Cloud, …) often serve a cert
    chain that isn't in the local trust store, so verifying ``require`` fails
    with CERTIFICATE_VERIFY_FAILED. So: ``verify-ca`` / ``verify-full`` verify
    (``ssl=True``); ``require`` and the bare ``DATABASE_SSL`` flag encrypt
    without verifying.
    """
    if sslmode in ("verify-ca", "verify-full"):
        return True
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


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
    # Tolerate values pasted into a hosting dashboard with stray whitespace or
    # surrounding quotes — otherwise SQLAlchemy can't parse the URL at all.
    url = url.strip()
    if len(url) >= 2 and url[0] == url[-1] and url[0] in ("'", '"'):
        url = url[1:-1].strip()

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
    connect_args: dict[str, object] = {}
    if want_ssl:
        connect_args["ssl"] = _ssl_arg(sslmode)
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
