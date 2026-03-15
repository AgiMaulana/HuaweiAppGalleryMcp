"""
Distribution / Operation Quality Report APIs

Download & installation report URL : GET /report/distribution-operation-quality/v1/appDownloadExport/{appId}
Installation failure report URL     : GET /report/distribution-operation-quality/v1/appDownloadFailExport/{appId}

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-download-report
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-install-fail-report
"""

from typing import Any

import httpx

from huawei_appgallery_mcp.auth import AuthConfig, build_auth_headers, get_access_token

BASE_URL = "https://connect-api.cloud.huawei.com/api/report/distribution-operation-quality/v1"


async def get_download_report_url(
    config: AuthConfig,
    app_id: str,
    *,
    language: str,
    start_time: str,
    end_time: str,
    group_by: str | None = None,
    export_type: str | None = None,
) -> dict[str, Any]:
    """
    Obtain the download URL for the app download and installation report (CSV or Excel).

    language   : "zh-CN", "en-US", or "ru-RU"
    start_time : YYYYMMDD (UTC)
    end_time   : YYYYMMDD (UTC) — max 180-day range
    group_by   : date (default), countryId, businessType, or appVersion
    export_type: CSV (default) or EXCEL
    """
    token = await get_access_token(config)
    params: dict[str, Any] = {
        "language": language,
        "startTime": start_time,
        "endTime": end_time,
    }
    if group_by is not None:
        params["groupBy"] = group_by
    if export_type is not None:
        params["exportType"] = export_type
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/appDownloadExport/{app_id}",
            params=params,
            headers=build_auth_headers(token, config.client_id),
        )
    return _handle(response)


async def get_install_failure_report_url(
    config: AuthConfig,
    app_id: str,
    *,
    language: str,
    start_time: str,
    end_time: str,
    group_by: str | None = None,
    export_type: str | None = None,
) -> dict[str, Any]:
    """
    Obtain the download URL for the app installation failure data report (CSV or Excel).

    language   : "zh-CN", "en-US", or "ru-RU"
    start_time : YYYYMMDD (UTC)
    end_time   : YYYYMMDD (UTC) — max 180-day range
    group_by   : date (default), deviceName, downloadType, appVersion, or countryId
    export_type: CSV (default) or EXCEL
    """
    token = await get_access_token(config)
    params: dict[str, Any] = {
        "language": language,
        "startTime": start_time,
        "endTime": end_time,
    }
    if group_by is not None:
        params["groupBy"] = group_by
    if export_type is not None:
        params["exportType"] = export_type
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/appDownloadFailExport/{app_id}",
            params=params,
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
