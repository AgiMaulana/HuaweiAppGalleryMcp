"""Tests for publish API module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huawei_appgallery_mcp.api.publish import (
    change_phased_release_state,
    set_gms_dependency,
    submit_app,
    submit_app_with_file,
    update_phased_release,
    update_release_time,
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
    resp.request.method = "POST"
    resp.request.url = "https://example.com/api"
    resp.status_code = 200
    return resp


def _setup_mocks():
    """Return a triple of (token_patch, get_client_patch, mock_client)."""
    mock_client = MagicMock()
    mock_client.post = AsyncMock(
        return_value=_mock_response({"result": "ok"})
    )
    mock_client.put = AsyncMock(
        return_value=_mock_response({"result": "ok"})
    )
    token_patch = patch(
        "huawei_appgallery_mcp.api.publish.get_access_token",
        AsyncMock(return_value="token"),
    )
    client_patch = patch(
        "huawei_appgallery_mcp.api.publish.get_client",
        return_value=mock_client,
    )
    return token_patch, client_patch, mock_client


class TestSubmitApp:
    @pytest.mark.asyncio
    async def test_submit_app_success(self, mock_auth_config):
        token_patch, client_patch, mock_client = _setup_mocks()
        with token_patch, client_patch:
            result = await submit_app(mock_auth_config, "app123")
            assert result == {"result": "ok"}
            mock_client.post.assert_called_once()
            url = mock_client.post.call_args[0][0]
            assert "/api/publish/v2/app-submit" in url
            json_body = mock_client.post.call_args.kwargs["json"]
            assert json_body["releaseType"] == 1

    @pytest.mark.asyncio
    async def test_submit_app_with_optional_params(self, mock_auth_config):
        token_patch, client_patch, mock_client = _setup_mocks()
        with token_patch, client_patch:
            await submit_app(
                mock_auth_config,
                "app123",
                release_percent=50,
                release_time=1700000000000,
                remark="test release",
                channel_id=2,
            )
            json_body = mock_client.post.call_args.kwargs["json"]
            assert json_body["releasePercent"] == 50
            assert json_body["releaseTime"] == 1700000000000
            assert json_body["remark"] == "test release"
            params = mock_client.post.call_args.kwargs["params"]
            assert params["channelId"] == 2

    @pytest.mark.asyncio
    async def test_submit_app_with_open_testing(self, mock_auth_config):
        token_patch, client_patch, mock_client = _setup_mocks()
        with token_patch, client_patch:
            await submit_app(
                mock_auth_config,
                "app123",
                use_testing_version=True,
                test_start_time=1700000000000,
                test_end_time=1710000000000,
                feedback_email="test@example.com",
            )
            json_body = mock_client.post.call_args.kwargs["json"]
            assert json_body["useTestingVersion"] is True
            assert json_body["testStartTime"] == 1700000000000
            assert json_body["testEndTime"] == 1710000000000
            assert json_body["feedbackEmail"] == "test@example.com"


class TestSubmitAppWithFile:
    @pytest.mark.asyncio
    async def test_submit_app_with_file_success(self, mock_auth_config):
        token_patch, client_patch, mock_client = _setup_mocks()
        with token_patch, client_patch:
            files = [
                {"fileName": "app.aab", "fileUrl": "https://cdn.example.com/app.aab"}
            ]
            result = await submit_app_with_file(
                mock_auth_config, "app123", 5, files
            )
            assert result == {"result": "ok"}
            mock_client.post.assert_called_once()
            url = mock_client.post.call_args[0][0]
            assert "/api/publish/v2/app-submit-with-file" in url
            json_body = mock_client.post.call_args.kwargs["json"]
            assert json_body["fileType"] == 5
            assert json_body["files"] == files
            assert json_body["releaseType"] == 1


class TestChangePhasedReleaseState:
    @pytest.mark.asyncio
    async def test_change_phased_release_state(self, mock_auth_config):
        token_patch, client_patch, mock_client = _setup_mocks()
        with token_patch, client_patch:
            result = await change_phased_release_state(
                mock_auth_config,
                "app123",
                state="RELEASE",
                phased_release_start_time="2026-05-01T00:00:00+0800",
                phased_release_end_time="2026-05-15T00:00:00+0800",
                phased_release_percent="50.00",
            )
            assert result == {"result": "ok"}
            # Verify PUT verb was used
            mock_client.put.assert_called_once()
            url = mock_client.put.call_args[0][0]
            assert "/api/publish/v2/phased-release/state" in url
            json_body = mock_client.put.call_args.kwargs["json"]
            assert json_body["state"] == "RELEASE"
            assert json_body["phasedReleaseStartTime"] == "2026-05-01T00:00:00+0800"
            assert json_body["phasedReleaseEndTime"] == "2026-05-15T00:00:00+0800"
            assert json_body["phasedReleasePercent"] == "50.00"


class TestUpdatePhasedRelease:
    @pytest.mark.asyncio
    async def test_update_phased_release(self, mock_auth_config):
        token_patch, client_patch, mock_client = _setup_mocks()
        with token_patch, client_patch:
            result = await update_phased_release(
                mock_auth_config,
                "app123",
                state="RELEASE",
            )
            assert result == {"result": "ok"}
            mock_client.put.assert_called_once()
            url = mock_client.put.call_args[0][0]
            assert "/api/publish/v2/phased-release" in url
            params = mock_client.put.call_args.kwargs["params"]
            assert params["releaseType"] == 3  # default


class TestUpdateReleaseTime:
    @pytest.mark.asyncio
    async def test_update_release_time(self, mock_auth_config):
        token_patch, client_patch, mock_client = _setup_mocks()
        with token_patch, client_patch:
            result = await update_release_time(
                mock_auth_config,
                "app123",
                change_type=2,
                release_time="2026-04-01T10:00:00+0800",
            )
            assert result == {"result": "ok"}
            mock_client.put.assert_called_once()
            url = mock_client.put.call_args[0][0]
            assert "/api/publish/v2/on-shelf-time" in url
            json_body = mock_client.put.call_args.kwargs["json"]
            assert json_body["changeType"] == 2
            assert json_body["releaseType"] == 1  # default
            assert json_body["releaseTime"] == "2026-04-01T10:00:00+0800"


class TestSetGmsDependency:
    @pytest.mark.asyncio
    async def test_set_gms_dependency(self, mock_auth_config):
        token_patch, client_patch, mock_client = _setup_mocks()
        with token_patch, client_patch:
            result = await set_gms_dependency(
                mock_auth_config, "app123", need_gms=1
            )
            assert result == {"result": "ok"}
            mock_client.put.assert_called_once()
            url = mock_client.put.call_args[0][0]
            assert "/api/publish/v2/properties/gms" in url
            json_body = mock_client.put.call_args.kwargs["json"]
            assert json_body["needGms"] == 1


class TestSubmitApiError:
    @pytest.mark.asyncio
    async def test_submit_api_error(self, mock_auth_config):
        with (
            patch(
                "huawei_appgallery_mcp.api.publish.get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch(
                "huawei_appgallery_mcp.api.publish.get_client"
            ) as mock_get_client,
            pytest.raises(APIError, match="AppGallery API error"),
        ):
            mock_client = MagicMock()
            mock_client.post = AsyncMock(
                return_value=_mock_response(
                    code=204144641,
                    data={
                        "ret": {"code": 204144641, "msg": "service error"}
                    },
                )
            )
            mock_get_client.return_value = mock_client
            await submit_app(mock_auth_config, "app123")
