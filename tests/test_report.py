"""Tests for report API module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huawei_appgallery_mcp.api.report import (
    get_download_report_url,
    get_install_failure_report_url,
)
from huawei_appgallery_mcp.auth import AuthConfig
from huawei_appgallery_mcp.errors import APIError


@pytest.fixture
def mock_auth_config():
    return AuthConfig(
        client_id="test_cid",
        client_secret="test_csecret",
        default_app_id="test_app_id",
    )


def _mock_response(data=None, code=0):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = data or {"ret": {"code": code, "msg": "ok"}}
    resp.elapsed = MagicMock()
    resp.elapsed.total_seconds.return_value = 0.1
    resp.request = MagicMock()
    resp.request.method = "GET"
    resp.request.url = "https://example.com/api"
    resp.status_code = 200
    return resp


class TestDownloadReport:
    @pytest.mark.asyncio
    async def test_get_download_report_url_success(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.report.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.report.get_client"
            ) as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get = AsyncMock(
                return_value=_mock_response({"result": "ok"})
            )
            mock_get_client.return_value = mock_client

            result = await get_download_report_url(
                mock_auth_config,
                "app123",
                language="en-US",
                start_time="20260101",
                end_time="20260131",
            )
            assert result == {"result": "ok"}
            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "appDownloadExport/app123" in url
            assert call_args.kwargs["params"]["language"] == "en-US"

    @pytest.mark.asyncio
    async def test_get_download_report_url_with_optional(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.report.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.report.get_client"
            ) as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get = AsyncMock(
                return_value=_mock_response({"result": "ok"})
            )
            mock_get_client.return_value = mock_client

            await get_download_report_url(
                mock_auth_config,
                "app123",
                language="en-US",
                start_time="20260101",
                end_time="20260131",
                group_by="countryId",
                export_type="EXCEL",
            )
            params = mock_client.get.call_args.kwargs["params"]
            assert params["groupBy"] == "countryId"
            assert params["exportType"] == "EXCEL"

    @pytest.mark.asyncio
    async def test_get_install_failure_report_url_success(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.report.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.report.get_client"
            ) as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get = AsyncMock(
                return_value=_mock_response({"result": "ok"})
            )
            mock_get_client.return_value = mock_client

            result = await get_install_failure_report_url(
                mock_auth_config,
                "app123",
                language="en-US",
                start_time="20260101",
                end_time="20260131",
            )
            assert result == {"result": "ok"}
            url = mock_client.get.call_args[0][0]
            assert "appDownloadFailExport/app123" in url


class TestReportApiError:
    @pytest.mark.asyncio
    async def test_report_api_error(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.report.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.report.get_client"
            ) as mock_get_client,
            pytest.raises(APIError, match="AppGallery API error"),
        ):
            mock_client = MagicMock()
            mock_client.get = AsyncMock(
                return_value=_mock_response(
                    code=1, data={"ret": {"code": 1, "msg": "error"}}
                )
            )
            mock_get_client.return_value = mock_client
            await get_download_report_url(
                mock_auth_config,
                "app123",
                language="en-US",
                start_time="20260101",
                end_time="20260131",
            )
