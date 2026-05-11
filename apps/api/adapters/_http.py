"""
Shared HTTP client for real adapters.
Mock adapters don't use this — they call generators directly.
Writes adapter_runs rows on each call.
"""
import time
from collections.abc import Callable

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

class AdapterHTTPClient:
    """
    Wraps httpx.AsyncClient with:
    - exponential backoff + jitter (max 5 retries, only on 5xx and connection errors, not 4xx)
    - per-host concurrency via httpx limits
    - adapter_runs row writing (passed in as callback to avoid circular imports)

    Usage:
        client = AdapterHTTPClient(adapter_name="eia.storage")
        response = await client.get("https://api.eia.gov/v2/...", params={...})
    """
    def __init__(self, adapter_name: str, on_run: Callable | None = None):
        self.adapter_name = adapter_name
        self.on_run = on_run  # async callable(adapter_name, status, rows, error)
        self._client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def get(self, url: str, **kwargs) -> httpx.Response:
        started = time.time()
        try:
            response = await self._get_with_retry(url, **kwargs)
            response.raise_for_status()
            if self.on_run:
                await self.on_run(self.adapter_name, "ok", 0, None)
            return response
        except Exception as e:
            if self.on_run:
                await self.on_run(self.adapter_name, "down", 0, str(e))
            raise

    @retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=1, max=30))
    async def _get_with_retry(self, url: str, **kwargs) -> httpx.Response:
        response = await self._client.get(url, **kwargs)
        if response.status_code >= 500:
            response.raise_for_status()
        return response

    async def close(self):
        await self._client.aclose()
