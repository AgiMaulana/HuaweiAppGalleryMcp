"""Tests for app_info API module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huawei_appgallery_mcp.api.app_info import query_app_info, update_app_info
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
    """Build a mock httpx.Response compatible with handle_api_response."""
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


class TestQueryAppInfo:
    @pytest.mark.asyncio
    async def test_query_app_info_success(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.app_info.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.app_info.get_client"
            ) as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get = AsyncMock(
                return_value=_mock_response({"result": "ok"})
            )
            mock_get_client.return_value = mock_client

            result = await query_app_info(mock_auth_config, "app123")
            assert result == {"result": "ok"}
            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args.kwargs
            assert call_kwargs["params"]["appId"] == "app123"
            assert call_kwargs["params"]["releaseType"] == 1

    @pytest.mark.asyncio
    async def test_query_app_info_with_channel(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.app_info.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.app_info.get_client"
            ) as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get = AsyncMock(
                return_value=_mock_response({"result": "ok"})
            )
            mock_get_client.return_value = mock_client

            await query_app_info(mock_auth_config, "app123", channel_id=2)
            call_kwargs = mock_client.get.call_args.kwargs
            assert call_kwargs["params"]["channelId"] == 2

    @pytest.mark.asyncio
    async def test_query_app_info_api_error(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.app_info.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.app_info.get_client"
            ) as mock_get_client,
            pytest.raises(APIError, match="AppGallery API error"),
        ):
            mock_client = MagicMock()
            mock_client.get = AsyncMock(
                return_value=_mock_response(
                    code=204144641,
                    data={"ret": {"code": 204144641, "msg": "service error"}},
                )
            )
            mock_get_client.return_value = mock_client
            await query_app_info(mock_auth_config, "app123")


class TestUpdateAppInfo:
    @pytest.mark.asyncio
    async def test_update_app_info_success(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.app_info.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.app_info.get_client"
            ) as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.put = AsyncMock(
                return_value=_mock_response({"result": "updated"})
            )
            mock_get_client.return_value = mock_client

            result = await update_app_info(
                mock_auth_config, "app123", app_name="New Name"
            )
            assert result == {"result": "updated"}
            call_kwargs = mock_client.put.call_args.kwargs
            json_body = call_kwargs["json"]
            assert json_body["appName"] == "New Name"
            assert "appDesc" not in json_body

    @pytest.mark.asyncio
    async def test_update_app_info_api_error(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.app_info.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.app_info.get_client"
            ) as mock_get_client,
            pytest.raises(APIError, match="AppGallery API error"),
        ):
            mock_client = MagicMock()
            mock_client.put = AsyncMock(
                return_value=_mock_response(
                    code=1, data={"ret": {"code": 1, "msg": "error"}}
                )
            )
            mock_get_client.return_value = mock_client
            await update_app_info(mock_auth_config, "app123", app_name="Fail")
