"""Shared helpers for AppGallery Connect API calls."""

import logging
import time
from typing import Any

import httpx

from huawei_appgallery_mcp.errors import APIError

logger = logging.getLogger(__name__)


def handle_api_response(response: httpx.Response) -> dict[str, Any]:
    """Validate an HTTP response and extract the JSON body.

    Raises:
        httpx.HTTPStatusError: on HTTP 4xx/5xx (from raise_for_status).
        APIError: on Huawei business error (ret.code != 0).
    """
    elapsed = response.elapsed.total_seconds()
    logger.info(
        "%s %s → %d (%.2fs)",
        response.request.method,
        response.request.url,
        response.status_code,
        elapsed,
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    if data.get("ret", {}).get("code", 0) != 0:
        ret = data["ret"]
        raise APIError(ret["code"], ret.get("msg", ""))
    return data
