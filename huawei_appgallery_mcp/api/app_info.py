"""
App Info APIs

Query : GET /publish/v2/app-info
Update: PUT /publish/v2/app-info

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-info-query-0000001158365045
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-info-update-0000001111685198
"""

from typing import Any, Literal

import httpx

from huawei_appgallery_mcp.auth import AuthConfig, build_auth_headers, get_access_token

BASE_URL = "https://connect-api.cloud.huawei.com/api/publish/v2"


async def query_app_info(
    config: AuthConfig,
    app_id: str,
    release_type: Literal[1, 3] = 1,
) -> dict[str, Any]:
    """Query the current metadata of an app."""
    token = await get_access_token(config)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/app-info",
            params={"appId": app_id, "releaseType": release_type},
            headers=build_auth_headers(token, config.client_id),
        )
    return _handle(response)


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

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}/app-info",
            params={"appId": app_id},
            headers=build_auth_headers(token, config.client_id),
            json=payload,
        )
    return _handle(response)


def _handle(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    if data.get("ret", {}).get("code", 0) != 0:
        ret = data["ret"]
        raise RuntimeError(f"AppGallery API error {ret['code']}: {ret.get('msg', '')}")
    return data
