"""Tests for language_info API module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huawei_appgallery_mcp.api.language_info import (
    delete_language_info,
    update_language_info,
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


class TestUpdateLanguageInfo:
    @pytest.mark.asyncio
    async def test_update_language_info_success(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.language_info.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.language_info.get_client"
            ) as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.put = AsyncMock(
                return_value=_mock_response({"result": "ok"})
            )
            mock_get_client.return_value = mock_client

            result = await update_language_info(
                mock_auth_config,
                "app123",
                "en-US",
                app_name="My App",
                app_desc="Description",
            )
            assert result == {"result": "ok"}
            mock_client.put.assert_called_once()
            call_kwargs = mock_client.put.call_args.kwargs
            assert call_kwargs["params"]["appId"] == "app123"
            assert call_kwargs["json"]["lang"] == "en-US"
            assert call_kwargs["json"]["appName"] == "My App"
            assert call_kwargs["json"]["appDesc"] == "Description"


class TestDeleteLanguageInfo:
    @pytest.mark.asyncio
    async def test_delete_language_info_success(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.language_info.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.language_info.get_client"
            ) as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.delete = AsyncMock(
                return_value=_mock_response({"result": "ok"})
            )
            mock_get_client.return_value = mock_client

            result = await delete_language_info(
                mock_auth_config, "app123", "fr-FR"
            )
            assert result == {"result": "ok"}
            mock_client.delete.assert_called_once()
            call_kwargs = mock_client.delete.call_args.kwargs
            assert call_kwargs["params"]["appId"] == "app123"
            assert call_kwargs["params"]["lang"] == "fr-FR"


class TestLanguageApiError:
    @pytest.mark.asyncio
    async def test_language_api_error(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.language_info.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.language_info.get_client"
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
            await update_language_info(
                mock_auth_config, "app123", "en-US", app_name="Fail"
            )
