"""
Publishing / Release APIs

Submit app:           POST /publish/v2/app-submit
Submit with file URL: POST /publish/v2/app-submit-with-file

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-submit-0000001158245061
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-submit-with-file-0000001111845092
"""

from typing import Any, Literal

import httpx

from huawei_appgallery_mcp.auth import AuthConfig, build_auth_headers, get_access_token

BASE_URL = "https://connect-api.cloud.huawei.com/api/publish/v2"


async def submit_app(
    config: AuthConfig,
    app_id: str,
    *,
    release_type: Literal[1, 3] = 1,
    release_percent: int | None = None,
    release_time: int | None = None,
    remark: str | None = None,
) -> dict[str, Any]:
    """
    Submit the app for review and release on Huawei AppGallery.

    All app info and file info must already be saved before calling this.
    """
    token = await get_access_token(config)

    payload: dict[str, Any] = {"releaseType": release_type}
    if release_percent is not None:
        payload["releasePercent"] = release_percent
    if release_time is not None:
        payload["releaseTime"] = release_time
    if remark is not None:
        payload["remark"] = remark

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/app-submit",
            params={"appId": app_id},
            headers=build_auth_headers(token, config.client_id),
            json=payload,
        )
    return _handle(response)


async def submit_app_with_file(
    config: AuthConfig,
    app_id: str,
    file_type: Literal[1, 2, 5],
    files: list[dict[str, str]],
    *,
    release_type: Literal[1, 3] = 1,
    release_percent: int | None = None,
    release_time: int | None = None,
    remark: str | None = None,
) -> dict[str, Any]:
    """
    Submit the app when the APK/AAB is hosted on your own server.

    Huawei will download the file from the provided HTTPS URL during review.

    files: list of {"fileName": ..., "fileUrl": ..., "sha256": ...}
    """
    token = await get_access_token(config)

    payload: dict[str, Any] = {
        "fileType": file_type,
        "files": files,
        "releaseType": release_type,
    }
    if release_percent is not None:
        payload["releasePercent"] = release_percent
    if release_time is not None:
        payload["releaseTime"] = release_time
    if remark is not None:
        payload["remark"] = remark

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/app-submit-with-file",
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
