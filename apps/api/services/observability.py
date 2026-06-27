"""Phase B4 — minimal observability wiring.

Smallest genuinely-useful layer for a multi-tenant app: structured request
logging with a request-id (the lightweight "span" substitute), request metrics,
and recording safety violations to the (previously dormant) Alert table so they
surface in the admin view. NOT a full APM/OTel buildout.
"""
from __future__ import annotations

import logging
import logging.config
import time
import uuid
from typing import Any, Awaitable, Callable

from fastapi import Request, Response

from apps.api.services.metrics import HTTP_DURATION, HTTP_REQUESTS, SAFETY_VIOLATIONS

logger = logging.getLogger("goldeneye.request")
_safety_logger = logging.getLogger("goldeneye.safety")


def configure_logging(level: str = "INFO") -> None:
    """Install a simple structured-ish logging config (idempotent)."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": (
                        "%(asctime)s %(levelname)s %(name)s %(message)s"
                    ),
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {"handlers": ["console"], "level": level.upper()},
        }
    )


def _route_label(request: Request) -> str:
    """The matched route *template* (low cardinality), not the raw path."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or "<unmatched>"


async def request_metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign a request-id, time the request, record metrics, emit one
    structured log line, and echo the id back in `X-Request-ID`."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start
        route = _route_label(request)
        method = request.method
        HTTP_REQUESTS.labels(
            method=method, route=route, status=str(status)
        ).inc()
        HTTP_DURATION.labels(method=method, route=route).observe(duration)
        logger.info(
            "request method=%s route=%s status=%s duration_ms=%.1f request_id=%s",
            method,
            route,
            status,
            duration * 1000.0,
            request_id,
        )
        # `response` exists on the success path; set the header there.
        try:
            response.headers["X-Request-ID"] = request_id  # type: ignore[name-defined]
        except Exception:  # noqa: BLE001 — error path already raised
            pass


async def _resolve_user_id(request: Request) -> uuid.UUID | None:
    """Best-effort user attribution for an alert — never raises."""
    try:
        from apps.api.auth.clerk import verify_token
        from apps.api.db.session import get_session_factory
        from apps.api.repos import users as users_repo

        authz = request.headers.get("Authorization")
        if not authz:
            return None
        parts = authz.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        claims = verify_token(parts[1].strip())
        sub = claims.get("sub") if claims else None
        if not sub:
            return None
        async with get_session_factory()() as session:
            user = await users_repo.upsert(session, clerk_user_id=sub)
            await session.commit()
            return user.id
    except Exception:  # noqa: BLE001
        return None


async def record_safety_violation(request: Request, message: str) -> None:
    """Persist a blocked safety violation to the Alert table + bump the counter.

    Multi-tenant aware (`user_id` best-effort). Centralized at the single choke
    point (the SafetyViolation handler) so every violation, from any LLM call, is
    recorded. Best-effort — alerting must never mask the original 500.
    """
    SAFETY_VIOLATIONS.inc()
    payload: dict[str, Any] = {
        "message": message,
        "path": request.url.path,
        "method": request.method,
        "request_id": getattr(request.state, "request_id", None),
    }
    try:
        from apps.api.db.session import get_session_factory
        from apps.api.models.orm.alerts import Alert

        user_id = await _resolve_user_id(request)
        async with get_session_factory()() as session:
            session.add(
                Alert(
                    user_id=user_id,
                    kind="safety_violation",
                    severity="error",
                    payload=payload,
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001
        _safety_logger.exception("failed to record safety-violation alert")
