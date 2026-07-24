"""
App Info APIs

Query : GET /publish/v2/app-info
Update: PUT /publish/v2/app-info

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-info-query-0000001158365045
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-info-update-0000001111685198
"""

import logging
from typing import Any, Literal

import httpx

from huawei_appgallery_mcp.api._helpers import handle_api_response
from huawei_appgallery_mcp.auth import AuthConfig, build_auth_headers, get_access_token
from huawei_appgallery_mcp.http_client import get_client

logger = logging.getLogger(__name__)


async def query_app_info(
    config: AuthConfig,
    app_id: str,
    release_type: Literal[1, 3] = 1,
    channel_id: int | None = None,
) -> dict[str, Any]:
    """Query the current metadata of an app."""
    token = await get_access_token(config)
    params: dict[str, Any] = {"appId": app_id, "releaseType": release_type}
    if channel_id is not None:
        params["channelId"] = channel_id
    client = get_client()
    response = await client.get(
        f"{config.api_base_url}/api/publish/v2/app-info",
        params=params,
        headers=build_auth_headers(token, config.client_id),
    )
    return handle_api_response(response)


async def update_app_info(
    config: AuthConfig,
    app_id: str,
    *,
    default_lang: str | None = None,
    app_name: str | None = None,
    app_desc: str | None = None,
    brief_desc: str | None = None,
    privacy_policy: str | None = None,
    category_id: str | None = None,
    sub_category_id: str | None = None,
    cs_email: str | None = None,
    cs_phone: str | None = None,
    cs_url: str | None = None,
    content_rating: int | None = None,
    age_rating: int | None = None,
) -> dict[str, Any]:
    """Update app metadata in the AppGallery Connect draft."""
    token = await get_access_token(config)

    # Build payload with only provided fields (None = omit)
    payload: dict[str, Any] = {}
    if default_lang is not None:
        payload["defaultLang"] = default_lang
    if app_name is not None:
        payload["appName"] = app_name
    if app_desc is not None:
        payload["appDesc"] = app_desc
    if brief_desc is not None:
        payload["briefDesc"] = brief_desc
    if privacy_policy is not None:
        payload["privacyPolicy"] = privacy_policy
    if category_id is not None:
        payload["categoryId"] = category_id
    if sub_category_id is not None:
        payload["subCategoryId"] = sub_category_id
    if cs_email is not None:
        payload["csEmail"] = cs_email
    if cs_phone is not None:
        payload["csPhone"] = cs_phone
    if cs_url is not None:
        payload["csUrl"] = cs_url
    if content_rating is not None:
        payload["contentRating"] = content_rating
    if age_rating is not None:
        payload["ageRating"] = age_rating

    client = get_client()
    response = await client.put(
        f"{config.api_base_url}/api/publish/v2/app-info",
        params={"appId": app_id},
        headers=build_auth_headers(token, config.client_id),
        json=payload,
    )
    return handle_api_response(response)
