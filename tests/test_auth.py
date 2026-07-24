"""Tests for auth module — AuthConfig.from_env, resolve_app_id, get_access_token, build_auth_headers."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huawei_appgallery_mcp.auth import AuthConfig, build_auth_headers, get_access_token
from huawei_appgallery_mcp.errors import AuthError, ValidationError


# The mock_env_vars autouse fixture (conftest.py) sets:
#   HUAWEI_CLIENT_ID=test_client_id
#   HUAWEI_CLIENT_SECRET=test_client_secret
#   HUAWEI_APP_ID=test_app_id
# Tests that need different/missing values override via monkeypatch.


class TestAuthConfigFromEnv:
    def test_config_from_env_valid(self, monkeypatch):
        monkeypatch.setenv("HUAWEI_CLIENT_ID", "cid")
        monkeypatch.setenv("HUAWEI_CLIENT_SECRET", "csecret")
        monkeypatch.delenv("HUAWEI_APP_ID", raising=False)
        monkeypatch.delenv("HUAWEI_API_BASE_URL", raising=False)
        monkeypatch.delenv("HUAWEI_DRY_RUN", raising=False)

        config = AuthConfig.from_env()
        assert config.client_id == "cid"
        assert config.client_secret == "csecret"
        assert config.default_app_id is None
        assert config.api_base_url == "https://connect-api.cloud.huawei.com"
        assert config.dry_run is False

    def test_config_from_env_missing_id(self, monkeypatch):
        monkeypatch.delenv("HUAWEI_CLIENT_ID", raising=False)
        monkeypatch.setenv("HUAWEI_CLIENT_SECRET", "secret")
        with pytest.raises(AuthError, match="HUAWEI_CLIENT_ID"):
            AuthConfig.from_env()

    def test_config_from_env_missing_secret(self, monkeypatch):
        monkeypatch.setenv("HUAWEI_CLIENT_ID", "id")
        monkeypatch.delenv("HUAWEI_CLIENT_SECRET", raising=False)
        with pytest.raises(AuthError, match="HUAWEI_CLIENT_ID"):
            AuthConfig.from_env()

    def test_config_from_env_with_app_id(self, monkeypatch):
        monkeypatch.setenv("HUAWEI_CLIENT_ID", "cid")
        monkeypatch.setenv("HUAWEI_CLIENT_SECRET", "csecret")
        monkeypatch.setenv("HUAWEI_APP_ID", "my_app")
        config = AuthConfig.from_env()
        assert config.default_app_id == "my_app"

    def test_config_from_env_without_app_id(self, monkeypatch):
        monkeypatch.setenv("HUAWEI_CLIENT_ID", "cid")
        monkeypatch.setenv("HUAWEI_CLIENT_SECRET", "csecret")
        monkeypatch.delenv("HUAWEI_APP_ID", raising=False)
        config = AuthConfig.from_env()
        assert config.default_app_id is None


class TestResolveAppId:
    def test_resolve_app_id_explicit(self):
        config = AuthConfig(
            client_id="cid",
            client_secret="csecret",
            default_app_id="default_app",
        )
        assert config.resolve_app_id("explicit_app") == "explicit_app"

    def test_resolve_app_id_fallback(self):
        config = AuthConfig(
            client_id="cid",
            client_secret="csecret",
            default_app_id="default_app",
        )
        assert config.resolve_app_id(None) == "default_app"

    def test_resolve_app_id_missing(self):
        config = AuthConfig(
            client_id="cid",
            client_secret="csecret",
            default_app_id=None,
        )
        with pytest.raises(ValidationError, match="app_id is required"):
            config.resolve_app_id(None)


class TestGetAccessToken:
    @pytest.mark.asyncio
    async def test_get_access_token_cached_valid(self, monkeypatch):
        monkeypatch.setattr(
            "huawei_appgallery_mcp.auth._cached_token", "cached_token_value"
        )
        monkeypatch.setattr(
            "huawei_appgallery_mcp.auth._token_expires_at", time.time() + 3600
        )

        with patch("huawei_appgallery_mcp.auth.get_client") as mock_get_client:
            config = AuthConfig(client_id="cid", client_secret="csecret")
            token = await get_access_token(config)
            assert token == "cached_token_value"
            mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_access_token_expired_refreshes(self, monkeypatch):
        monkeypatch.setattr(
            "huawei_appgallery_mcp.auth._cached_token", "old_token"
        )
        monkeypatch.setattr(
            "huawei_appgallery_mcp.auth._token_expires_at", time.time() - 1
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_in": 3600,
        }
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("huawei_appgallery_mcp.auth.get_client", return_value=mock_client):
            config = AuthConfig(client_id="cid", client_secret="csecret")
            token = await get_access_token(config)
            assert token == "new_token"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_access_token_api_error(self, monkeypatch):
        monkeypatch.setattr("huawei_appgallery_mcp.auth._cached_token", None)
        monkeypatch.setattr("huawei_appgallery_mcp.auth._token_expires_at", 0.0)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "ret": {"code": 1, "msg": "invalid client"},
        }
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("huawei_appgallery_mcp.auth.get_client", return_value=mock_client):
            config = AuthConfig(client_id="cid", client_secret="csecret")
            with pytest.raises(AuthError, match="Failed to obtain token"):
                await get_access_token(config)

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, monkeypatch):
        monkeypatch.setattr("huawei_appgallery_mcp.auth._cached_token", None)
        monkeypatch.setattr("huawei_appgallery_mcp.auth._token_expires_at", 0.0)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "my_access_token",
            "expires_in": 3600,
        }
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("huawei_appgallery_mcp.auth.get_client", return_value=mock_client):
            config = AuthConfig(client_id="cid", client_secret="csecret")
            token = await get_access_token(config)
            assert token == "my_access_token"
            # Token should be cached in module-level globals
            import huawei_appgallery_mcp.auth as auth_mod
            assert auth_mod._cached_token == "my_access_token"


class TestBuildAuthHeaders:
    def test_build_auth_headers(self):
        headers = build_auth_headers("mytoken", "my_client_id")
        assert headers == {
            "Authorization": "Bearer mytoken",
            "client_id": "my_client_id",
            "Content-Type": "application/json",
        }
