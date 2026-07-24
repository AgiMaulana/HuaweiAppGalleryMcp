"""Shared HTTP client with connection pooling and retry.

Provides singleton httpx.AsyncClient instances so every API call
reuses the same TCP connection pool instead of opening a new
connection per call. Includes automatic retry on 5xx and
network errors with exponential backoff.

Usage:
    from huawei_appgallery_mcp.http_client import get_client, get_upload_client, close_clients

    client = get_client()
    response = await client.get(...)

    # On shutdown:
    await close_clients()
"""

import logging

import httpx

logger = logging.getLogger(__name__)

# Retry 3 times on 5xx / network errors with exponential backoff
_transport = httpx.AsyncHTTPTransport(retries=3)

# Standard timeout: 10 s connect, 30 s read, 30 s write, 60 s pool
_default_timeout = httpx.Timeout(10.0, read=30.0, write=30.0, pool=60.0)

# Upload timeout: up to 10 minutes for large files
_upload_timeout = httpx.Timeout(600.0)

_client: httpx.AsyncClient | None = None
_upload_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Return the shared httpx.AsyncClient for standard API calls."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(transport=_transport, timeout=_default_timeout)
        logger.debug("Created shared HTTP client (timeout=%s)", _default_timeout)
    return _client


def get_upload_client() -> httpx.AsyncClient:
    """Return a dedicated httpx.AsyncClient for file uploads (longer timeout)."""
    global _upload_client
    if _upload_client is None:
        _upload_client = httpx.AsyncClient(transport=_transport, timeout=_upload_timeout)
        logger.debug("Created upload HTTP client (timeout=%s)", _upload_timeout)
    return _upload_client


async def close_clients() -> None:
    """Close all shared HTTP clients. Call on server shutdown."""
    global _client, _upload_client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.debug("Closed shared HTTP client")
    if _upload_client is not None:
        await _upload_client.aclose()
        _upload_client = None
        logger.debug("Closed upload HTTP client")
