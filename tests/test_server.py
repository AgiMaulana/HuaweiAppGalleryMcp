"""Tests for server _dispatch function covering all tool branches."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huawei_appgallery_mcp.auth import AuthConfig
from huawei_appgallery_mcp.errors import ValidationError
from huawei_appgallery_mcp.server import _dispatch


@pytest.fixture
def mock_config():
    return AuthConfig(
        client_id="test_cid",
        client_secret="test_csecret",
        default_app_id="test_app_id",
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mock_async_fn(return_value=None):
    """Create an AsyncMock that returns the given value."""
    return AsyncMock(return_value=return_value)


# ── App Info ─────────────────────────────────────────────────────────────────


class TestDispatchQueryAppInfo:
    @pytest.mark.asyncio
    async def test_dispatch_query_app_info(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.query_app_info",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "query_app_info",
                {"release_type": 1},
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            call_args = mock_fn.call_args
            assert call_args[0][1] == "test_app_id"


class TestDispatchUpdateAppInfo:
    @pytest.mark.asyncio
    async def test_dispatch_update_app_info(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.update_app_info",
            _mock_async_fn({"result": "updated"}),
        ) as mock_fn:
            result = await _dispatch(
                "update_app_info",
                {
                    "app_name": "New Name",
                    "brief_desc": "Tagline",
                },
                mock_config,
            )
            assert result == {"result": "updated"}
            mock_fn.assert_called_once()
            kwargs = mock_fn.call_args.kwargs
            assert kwargs["app_name"] == "New Name"
            assert kwargs["brief_desc"] == "Tagline"


# ── Language Info ────────────────────────────────────────────────────────────


class TestDispatchLanguageInfo:
    @pytest.mark.asyncio
    async def test_dispatch_update_language_info(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.update_language_info",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "update_language_info",
                {"lang": "en-US", "app_name": "My App"},
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            # lang is passed as positional arg (3rd after config, app_id)
            args = mock_fn.call_args[0]
            assert args[2] == "en-US"
            assert mock_fn.call_args.kwargs["app_name"] == "My App"

    @pytest.mark.asyncio
    async def test_dispatch_delete_language_info(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.delete_language_info",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "delete_language_info",
                {"lang": "fr-FR"},
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            # lang is passed as positional arg (3rd after config, app_id)
            args = mock_fn.call_args[0]
            assert args[2] == "fr-FR"


# ── File Upload ──────────────────────────────────────────────────────────────


class TestDispatchGetUploadUrl:
    @pytest.mark.asyncio
    async def test_dispatch_get_upload_url(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.get_upload_url",
            _mock_async_fn({"uploadUrl": "http://example.com", "authCode": "abc"}),
        ) as mock_fn:
            result = await _dispatch(
                "get_upload_url",
                {"suffix": "aab", "file_name": "app.aab"},
                mock_config,
            )
            assert result["uploadUrl"] == "http://example.com"
            mock_fn.assert_called_once()


class TestDispatchUploadFile:
    @pytest.mark.asyncio
    async def test_dispatch_upload_file_file_not_found(self, mock_config):
        with pytest.raises(FileNotFoundError, match="File not found"):
            await _dispatch(
                "upload_file",
                {
                    "file_path": "/nonexistent/file.aab",
                    "upload_url": "http://example.com",
                    "auth_code": "abc",
                },
                mock_config,
            )


class TestDispatchUploadAppFile:
    @pytest.mark.asyncio
    async def test_dispatch_upload_app_file(self, mock_config):
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, suffix=".aab"
        ) as f:
            f.write(b"\x00" * 100)
            f.flush()
            file_path = f.name

        with (
            patch(
                "huawei_appgallery_mcp.server.get_upload_url",
                _mock_async_fn({
                    "uploadUrl": "http://upload.example.com",
                    "authCode": "abc123",
                }),
            ) as mock_get_url,
            patch(
                "huawei_appgallery_mcp.server.upload_file",
                _mock_async_fn("http://dest.example.com/file.aab"),
            ) as mock_upload,
            patch(
                "huawei_appgallery_mcp.server.update_app_file_info",
                _mock_async_fn({"pkgIds": ["pkg1"]}),
            ) as mock_attach,
        ):
            result = await _dispatch(
                "upload_app_file",
                {"file_path": file_path, "file_type": 5},
                mock_config,
            )
            assert result["pkgIds"] == ["pkg1"]
            assert result["_uploadedFileUrl"] == "http://dest.example.com/file.aab"
            mock_get_url.assert_called_once()
            mock_upload.assert_called_once()
            mock_attach.assert_called_once()


# ── Publishing ───────────────────────────────────────────────────────────────


class TestDispatchSubmitApp:
    @pytest.mark.asyncio
    async def test_dispatch_submit_app(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.submit_app",
            _mock_async_fn({"result": "submitted"}),
        ) as mock_fn:
            result = await _dispatch(
                "submit_app",
                {
                    "confirm": True,
                    "release_type": 3,
                    "release_percent": 50,
                    "remark": "test",
                },
                mock_config,
            )
            assert result == {"result": "submitted"}
            mock_fn.assert_called_once()
            kwargs = mock_fn.call_args.kwargs
            assert kwargs["release_type"] == 3
            assert kwargs["release_percent"] == 50


class TestDispatchSubmitAppWithFile:
    @pytest.mark.asyncio
    async def test_dispatch_submit_app_with_file(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.submit_app_with_file",
            _mock_async_fn({"result": "submitted"}),
        ) as mock_fn:
            files = [
                {
                    "file_name": "app.aab",
                    "file_url": "https://cdn.example.com/app.aab",
                    "sha256": "abc123",
                },
            ]
            result = await _dispatch(
                "submit_app_with_file",
                {"confirm": True, "file_type": 5, "files": files},
                mock_config,
            )
            assert result == {"result": "submitted"}
            mock_fn.assert_called_once()
            # Verify file transformation: file_name → fileName, file_url → fileUrl
            api_files = mock_fn.call_args[0][3]
            assert api_files[0]["fileName"] == "app.aab"
            assert api_files[0]["fileUrl"] == "https://cdn.example.com/app.aab"
            assert api_files[0]["sha256"] == "abc123"


class TestDispatchPhasedRelease:
    @pytest.mark.asyncio
    async def test_dispatch_change_phased_release_state(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.change_phased_release_state",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "change_phased_release_state",
                {
                    "state": "RELEASE",
                    "phased_release_percent": "50.00",
                },
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            kwargs = mock_fn.call_args.kwargs
            assert kwargs["state"] == "RELEASE"

    @pytest.mark.asyncio
    async def test_dispatch_update_phased_release(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.update_phased_release",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "update_phased_release",
                {"state": "RELEASE"},
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            kwargs = mock_fn.call_args.kwargs
            assert kwargs["release_type"] == 3  # default


class TestDispatchReleaseTime:
    @pytest.mark.asyncio
    async def test_dispatch_update_release_time(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.update_release_time",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "update_release_time",
                {
                    "change_type": 2,
                    "release_time": "2026-04-01T10:00:00+0800",
                },
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            kwargs = mock_fn.call_args.kwargs
            assert kwargs["change_type"] == 2


class TestDispatchGms:
    @pytest.mark.asyncio
    async def test_dispatch_set_gms_dependency(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.set_gms_dependency",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "set_gms_dependency",
                {"need_gms": 1},
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            kwargs = mock_fn.call_args.kwargs
            assert kwargs["need_gms"] == 1


class TestDispatchCompileStatus:
    @pytest.mark.asyncio
    async def test_dispatch_query_compile_status(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.query_compile_status",
            _mock_async_fn({"result": "compiling"}),
        ) as mock_fn:
            result = await _dispatch(
                "query_compile_status",
                {"pkg_ids": ["pkg1", "pkg2"]},
                mock_config,
            )
            assert result == {"result": "compiling"}
            mock_fn.assert_called_once()
            # pkg_ids passed as-is (list)
            args = mock_fn.call_args[0]
            assert args[2] == ["pkg1", "pkg2"]


# ── Reports ──────────────────────────────────────────────────────────────────


class TestDispatchReports:
    @pytest.mark.asyncio
    async def test_dispatch_get_download_report_url(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.get_download_report_url",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "get_download_report_url",
                {
                    "language": "en-US",
                    "start_time": "20260101",
                    "end_time": "20260131",
                },
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            kwargs = mock_fn.call_args.kwargs
            assert kwargs["language"] == "en-US"

    @pytest.mark.asyncio
    async def test_dispatch_get_install_failure_report_url(self, mock_config):
        with patch(
            "huawei_appgallery_mcp.server.get_install_failure_report_url",
            _mock_async_fn({"result": "ok"}),
        ) as mock_fn:
            result = await _dispatch(
                "get_install_failure_report_url",
                {
                    "language": "en-US",
                    "start_time": "20260101",
                    "end_time": "20260131",
                },
                mock_config,
            )
            assert result == {"result": "ok"}
            mock_fn.assert_called_once()
            kwargs = mock_fn.call_args.kwargs
            assert kwargs["language"] == "en-US"


# ── Unknown Tool ─────────────────────────────────────────────────────────────


class TestDispatchUnknown:
    def test_dispatch_unknown_tool(self, mock_config):
        import asyncio

        with pytest.raises(ValueError, match="Unknown tool"):
            asyncio.run(_dispatch("nonexistent_tool", {}, mock_config))
