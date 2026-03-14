"""
Language / Localization Info APIs

Update: PUT    /publish/v2/app-language-info
Delete: DELETE /publish/v2/app-language-info

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-language-info-update-0000001158245057
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-language-info-delete-0000001111845088
"""

from typing import Any

import httpx

from huawei_appgallery_mcp.auth import AuthConfig, build_auth_headers, get_access_token

BASE_URL = "https://connect-api.cloud.huawei.com/api/publish/v2"


async def update_language_info(
    config: AuthConfig,
    app_id: str,
    lang: str,
    *,
    app_name: str | None = None,
    app_desc: str | None = None,
    brief_desc: str | None = None,
    new_features: str | None = None,
) -> dict[str, Any]:
    """Add or update localized store listing content for a specific language."""
    token = await get_access_token(config)

    payload: dict[str, Any] = {"lang": lang}
    if app_name is not None:
        payload["appName"] = app_name
    if app_desc is not None:
        payload["appDesc"] = app_desc
    if brief_desc is not None:
        payload["briefDesc"] = brief_desc
    if new_features is not None:
        payload["newFeatures"] = new_features

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}/app-language-info",
            params={"appId": app_id},
            headers=build_auth_headers(token, config.client_id),
            json=payload,
        )
    return _handle(response)


async def delete_language_info(
    config: AuthConfig,
    app_id: str,
    lang: str,
) -> dict[str, Any]:
    """Remove a localized store listing for a specific language."""
    token = await get_access_token(config)
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{BASE_URL}/app-language-info",
            params={"appId": app_id, "lang": lang},
            headers=build_auth_headers(token, config.client_id),
        )
    return _handle(response)


def _handle(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    if data.get("ret", {}).get("code", 0) != 0:
        ret = data["ret"]
        raise RuntimeError(f"AppGallery API error {ret['code']}: {ret.get('msg', '')}")
    return data
