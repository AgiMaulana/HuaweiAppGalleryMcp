"""
Publishing / Release APIs

Submit app:                  POST /publish/v2/app-submit
Submit with file URL:        POST /publish/v2/app-submit-with-file
Change phased release state: PUT  /publish/v2/phased-release/state
Update phased release:       PUT  /publish/v2/phased-release
Update release time:         PUT  /publish/v2/on-shelf-time
Set GMS dependency:          PUT  /publish/v2/properties/gms

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-submit-0000001158245061
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-submit-with-file-0000001111845092
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-phased-release-state-0000001158365051
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-phased-release-0000001111685204
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-update-releasetime-0000001158365053
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-gms-0000001111845094
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
    channel_id: int | None = None,
) -> dict[str, Any]:
    """
    Submit the app for review and release on Huawei AppGallery.

    All app info and file info must already be saved before calling this.
    channel_id: optional channel (e.g. 2 = open testing).
    """
    token = await get_access_token(config)

    params: dict[str, Any] = {"appId": app_id}
    if channel_id is not None:
        params["channelId"] = channel_id

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
            params=params,
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


async def change_phased_release_state(
    config: AuthConfig,
    app_id: str,
    *,
    state: str,
    phased_release_start_time: str | None = None,
    phased_release_end_time: str | None = None,
    phased_release_percent: str | None = None,
) -> dict[str, Any]:
    """
    Change the release status of an app released by phase.

    state: "RELEASE" to proceed, "ROLLBACK" to roll back, "GRAY_TERMINATED" to stop.
    """
    token = await get_access_token(config)
    payload: dict[str, Any] = {"state": state}
    if phased_release_start_time is not None:
        payload["phasedReleaseStartTime"] = phased_release_start_time
    if phased_release_end_time is not None:
        payload["phasedReleaseEndTime"] = phased_release_end_time
    if phased_release_percent is not None:
        payload["phasedReleasePercent"] = phased_release_percent
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}/phased-release/state",
            params={"appId": app_id},
            headers=build_auth_headers(token, config.client_id),
            json=payload,
        )
    return _handle(response)


async def update_phased_release(
    config: AuthConfig,
    app_id: str,
    *,
    state: str,
    phased_release_start_time: str | None = None,
    phased_release_end_time: str | None = None,
    phased_release_percent: str | None = None,
    release_type: Literal[1, 3] = 3,
) -> dict[str, Any]:
    """
    Change phased release to full release, or update the phased release configuration.
    """
    token = await get_access_token(config)
    payload: dict[str, Any] = {"state": state}
    if phased_release_start_time is not None:
        payload["phasedReleaseStartTime"] = phased_release_start_time
    if phased_release_end_time is not None:
        payload["phasedReleaseEndTime"] = phased_release_end_time
    if phased_release_percent is not None:
        payload["phasedReleasePercent"] = phased_release_percent
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}/phased-release",
            params={"appId": app_id, "releaseType": release_type},
            headers=build_auth_headers(token, config.client_id),
            json=payload,
        )
    return _handle(response)


async def update_release_time(
    config: AuthConfig,
    app_id: str,
    *,
    change_type: int,
    release_time: str | None = None,
    release_type: Literal[1, 3] = 1,
) -> dict[str, Any]:
    """
    Update the release time of a version (only callable when app is in Releasing state).

    change_type: 1=release immediately, 2=release as scheduled, 3=update scheduled release time.
    release_time: UTC datetime string, e.g. "2026-04-01T10:00:00+0800".
    """
    token = await get_access_token(config)
    payload: dict[str, Any] = {"changeType": change_type, "releaseType": release_type}
    if release_time is not None:
        payload["releaseTime"] = release_time
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}/on-shelf-time",
            params={"appId": app_id},
            headers=build_auth_headers(token, config.client_id),
            json=payload,
        )
    return _handle(response)


async def set_gms_dependency(
    config: AuthConfig,
    app_id: str,
    *,
    need_gms: int,
) -> dict[str, Any]:
    """
    Report whether the app depends on GMS to AppGallery Connect.

    need_gms: 0 = does not depend on GMS, 1 = depends on GMS.
    """
    token = await get_access_token(config)
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}/properties/gms",
            params={"appId": app_id},
            headers=build_auth_headers(token, config.client_id),
            json={"needGms": need_gms},
        )
    return _handle(response)


def _handle(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    if data.get("ret", {}).get("code", 0) != 0:
        ret = data["ret"]
        raise RuntimeError(f"AppGallery API error {ret['code']}: {ret.get('msg', '')}")
    return data
