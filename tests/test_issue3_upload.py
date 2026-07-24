"""Tests for upload_file tool and fileDestUlr typo fix (Issue #3)"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huawei_appgallery_mcp.api.file_upload import (
    upload_file,
    _extract_dest_url,
)
from huawei_appgallery_mcp.errors import APIError
from huawei_appgallery_mcp.server import _dispatch


# Mock response helper
def mock_upload_response(code=0, msg="success", include_typo=True):
    """Create a mock upload API response with the fileDestUlr typo."""
    response = MagicMock()
    response.raise_for_status = MagicMock()  # Not async
    
    if include_typo:
        # Huawei's API has the typo: fileDestUlr (missing 'l')
        response.json.return_value = {
            "ret": {"code": code, "msg": msg},
            "result": {
                "UploadFileRsp": {
                    "fileDestUlr": "https://example.com/destination/file.aab"
                }
            },
        }
    else:
        # Some responses might use the correct spelling
        response.json.return_value = {
            "ret": {"code": code, "msg": msg},
            "result": {
                "UploadFileRsp": {
                    "fileDestUrl": "https://example.com/destination/file.aab"
                }
            },
        }
    return response


@pytest.fixture
def mock_config():
    """Create a mock AuthConfig."""
    from huawei_appgallery_mcp.auth import AuthConfig

    config = AsyncMock(spec=AuthConfig)
    config.client_id = "test_client_id"
    config.client_secret = "test_client_secret"
    config.default_app_id = "test_app_id"
    return config


@pytest.fixture
def mock_token():
    """Mock access token."""
    return "mock_access_token"


@pytest.fixture
def sample_file():
    """Create a temporary sample file for upload testing."""
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.aab') as f:
        f.write(b'\x00' * 1024)  # 1 KB file
        f.flush()
        return Path(f.name)


def test_extract_dest_url_with_typo():
    """Test that _extract_dest_url handles Huawei's fileDestUlr typo (Issue #3)."""
    # Test with typo (fileDestUlr - missing 'l')
    data_with_typo = {
        "result": {
            "UploadFileRsp": {
                "fileDestUlr": "https://example.com/typo_url.aab"
            }
        }
    }
    url = _extract_dest_url(data_with_typo)
    assert url == "https://example.com/typo_url.aab", "Should extract URL from fileDestUlr (typo)"


def test_extract_dest_url_correct_spelling():
    """Test that _extract_dest_url also handles correct spelling."""
    # Test with correct spelling (fileDestUrl)
    data_correct = {
        "result": {
            "UploadFileRsp": {
                "fileDestUrl": "https://example.com/correct_url.aab"
            }
        }
    }
    url = _extract_dest_url(data_correct)
    assert url == "https://example.com/correct_url.aab", "Should extract URL from fileDestUrl (correct)"


def test_extract_dest_url_prefers_typo_over_correct():
    """Test that fileDestUlr (typo) is checked first."""
    # If both exist, typo version should be checked first (as per implementation)
    data_both = {
        "result": {
            "UploadFileRsp": {
                "fileDestUlr": "https://example.com/typo.aab",
                "fileDestUrl": "https://example.com/correct.aab"
            }
        }
    }
    url = _extract_dest_url(data_both)
    # The implementation checks fileDestUlr first with `or`, so if it exists, it's used
    assert url == "https://example.com/typo.aab"


def test_extract_dest_url_empty():
    """Test _extract_dest_url returns empty string when URL not found."""
    data_empty = {
        "result": {
            "UploadFileRsp": {}
        }
    }
    url = _extract_dest_url(data_empty)
    assert url == "", "Should return empty string when no URL found"


def test_extract_dest_url_flat_structure():
    """Test _extract_dest_url with flat structure (not nested)."""
    data_flat = {
        "fileDestUlr": "https://example.com/flat_url.aab"
    }
    url = _extract_dest_url(data_flat)
    assert url == "https://example.com/flat_url.aab"


@pytest.mark.asyncio
async def test_upload_file_returns_dest_url(sample_file):
    """Test that upload_file properly extracts and returns fileDestUrl."""
    with patch("huawei_appgallery_mcp.api.file_upload.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_upload_response()

        dest_url = await upload_file(
            upload_url="https://example.com/upload",
            auth_code="test_auth_code",
            file_path=sample_file,
        )

        assert dest_url == "https://example.com/destination/file.aab"
        # Verify the upload was called
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_handles_api_error():
    """Test that upload_file properly handles API errors."""
    with (
        patch("huawei_appgallery_mcp.api.file_upload.httpx.AsyncClient") as mock_client,
        pytest.raises(APIError, match="AppGallery API error"),
    ):
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_upload_response(
            code=204144641,
            msg="The files url is empty"
        )

        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.aab') as f:
            f.write(b'\x00' * 1024)
            f.flush()
            await upload_file(
                upload_url="https://example.com/upload",
                auth_code="test_auth_code",
                file_path=Path(f.name),
            )


@pytest.mark.asyncio
async def test_upload_file_with_correct_spelling(sample_file):
    """Test upload_file when API returns correct spelling (fileDestUrl)."""
    with patch("huawei_appgallery_mcp.api.file_upload.httpx.AsyncClient") as mock_client:
        # Response with correct spelling
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_upload_response(
            include_typo=False
        )

        dest_url = await upload_file(
            upload_url="https://example.com/upload",
            auth_code="test_auth_code",
            file_path=sample_file,
        )

        assert dest_url == "https://example.com/destination/file.aab"


@pytest.mark.asyncio
async def test_upload_file_mcp_tool(mock_config):
    """Test the upload_file MCP tool dispatch (Issue #3)."""
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.aab') as f:
        f.write(b'\x00' * 1024)
        f.flush()
        test_file_path = f.name

    with (
        patch("huawei_appgallery_mcp.server.upload_file") as mock_upload,
    ):
        mock_upload.return_value = "https://example.com/dest/file.aab"

        result = await _dispatch(
            "upload_file",
            {
                "file_path": test_file_path,
                "upload_url": "https://example.com/upload",
                "auth_code": "test_auth_code",
            },
            mock_config,
        )

        assert result["fileDestUrl"] == "https://example.com/dest/file.aab"
        assert result["fileName"] == Path(test_file_path).name
        mock_upload.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_mcp_tool_file_not_found(mock_config):
    """Test upload_file MCP tool with non-existent file."""
    with pytest.raises(FileNotFoundError, match="File not found"):
        await _dispatch(
            "upload_file",
            {
                "file_path": "/nonexistent/file.aab",
                "upload_url": "https://example.com/upload",
                "auth_code": "test_auth_code",
            },
            mock_config,
        )


@pytest.mark.asyncio
async def test_upload_file_mcp_tool_large_file(mock_config):
    """Test upload_file MCP tool rejects files > 4GB."""
    # Create a mock file that appears large
    with (
        patch("pathlib.Path.stat") as mock_stat,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Mock file size to be 5 GB
        mock_stat.return_value.st_size = 5 * 1024 * 1024 * 1024

        with pytest.raises(ValueError, match="exceeds 4 GB limit"):
            await _dispatch(
                "upload_file",
                {
                    "file_path": "/tmp/large_file.aab",
                    "upload_url": "https://example.com/upload",
                    "auth_code": "test_auth_code",
                },
                mock_config,
            )

