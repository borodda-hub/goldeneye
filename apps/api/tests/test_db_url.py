"""Unit tests for the asyncpg URL normalizer used at deploy time."""

import ssl

import pytest

from apps.api.db import engine
from apps.api.db.engine import prepare_async_url


def _assert_encrypt_no_verify(connect_args: dict[str, object]) -> None:
    """`require` semantics: TLS on, but no cert/hostname verification."""
    ctx = connect_args["ssl"]
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_NONE


def test_local_url_passes_through_without_ssl() -> None:
    url, connect_args = prepare_async_url(
        "postgresql+asyncpg://ngti:ngti@localhost:5432/ngti"
    )
    assert url == "postgresql+asyncpg://ngti:ngti@localhost:5432/ngti"
    assert connect_args == {}


def test_timescale_cloud_url_is_normalized() -> None:
    # The shape Timescale Cloud / Neon hand out: bare `postgres` scheme +
    # `sslmode=require`. asyncpg understands neither.
    raw = "postgres://tsdbadmin:pw@abc.tsdb.cloud.timescale.com:34567/tsdb?sslmode=require"
    url, connect_args = prepare_async_url(raw)
    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url
    # `require` → encrypt but do NOT verify (managed cert chains aren't in the
    # local trust store; asyncpg ssl=True would over-verify and fail).
    _assert_encrypt_no_verify(connect_args)


def test_channel_binding_and_other_libpq_params_are_stripped() -> None:
    raw = (
        "postgresql://u:p@host:5432/db"
        "?sslmode=require&channel_binding=require&sslrootcert=/x"
    )
    url, connect_args = prepare_async_url(raw)
    for bad in ("sslmode", "channel_binding", "sslrootcert"):
        assert bad not in url
    _assert_encrypt_no_verify(connect_args)


def test_database_ssl_flag_forces_tls_without_sslmode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine.settings, "database_ssl", True)
    url, connect_args = prepare_async_url(
        "postgresql+asyncpg://u:p@some.managed.host:5432/db"
    )
    _assert_encrypt_no_verify(connect_args)
    assert url == "postgresql+asyncpg://u:p@some.managed.host:5432/db"


def test_verify_full_uses_strict_verification() -> None:
    url, connect_args = prepare_async_url(
        "postgresql+asyncpg://u:p@host:5432/db?sslmode=verify-full"
    )
    assert connect_args == {"ssl": True}
    assert "sslmode" not in url


def test_sslmode_disable_does_not_force_tls() -> None:
    url, connect_args = prepare_async_url(
        "postgresql+asyncpg://u:p@host:5432/db?sslmode=disable"
    )
    assert connect_args == {}
    assert "sslmode" not in url
