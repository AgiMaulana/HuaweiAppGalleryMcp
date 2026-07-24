"""Tests for upload_file tool and fileDestUlr typo fix (Issue #3)"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huawei_appgallery_mcp.api.file_upload import (
    CHUNK_SIZE,
    MAX_CHUNK_RETRIES,
    upload_file,
    upload_file_in_chunks,
    _extract_dest_url,
)
from huawei_appgallery_mcp.errors import APIError, NetworkError
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
    config.api_base_url = "https://connect-api.cloud.huawei.com"
    config.dry_run = False
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
    with patch("huawei_appgallery_mcp.api.file_upload.get_upload_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_upload_response())
        mock_get_client.return_value = mock_client

        dest_url = await upload_file(
            upload_url="https://example.com/upload",
            auth_code="test_auth_code",
            file_path=sample_file,
        )

        assert dest_url == "https://example.com/destination/file.aab"
        # Verify the upload was called
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_handles_api_error():
    """Test that upload_file properly handles API errors."""
    with (
        patch("huawei_appgallery_mcp.api.file_upload.get_upload_client") as mock_get_client,
        pytest.raises(APIError, match="AppGallery API error"),
    ):
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_upload_response(
            code=204144641,
            msg="The files url is empty"
        ))
        mock_get_client.return_value = mock_client

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
    with patch("huawei_appgallery_mcp.api.file_upload.get_upload_client") as mock_get_client:
        # Response with correct spelling
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_upload_response(
            include_typo=False
        ))
        mock_get_client.return_value = mock_client

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


# ---------------------------------------------------------------------------
# Chunked upload tests (Stage 4.7)
# ---------------------------------------------------------------------------


def _chunk_response(dest_url=""):
    """Build a mock httpx.Response for a successful chunk upload."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "ret": {"code": 0, "msg": "success"},
        "result": {
            "UploadFileRsp": {
                "fileDestUlr": dest_url or "https://example.com/dest/file.aab"
            }
        },
    }
    resp.elapsed = MagicMock()
    resp.elapsed.total_seconds.return_value = 0.1
    resp.request = MagicMock()
    resp.request.method = "POST"
    resp.request.url = "https://chunk-upload.example.com"
    resp.status_code = 200
    return resp


@pytest.mark.asyncio
async def test_upload_file_in_chunks_success():
    """Two chunks, both succeed, dest_url returned."""
    file_content = b"a" * 1000  # 1000 bytes

    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".aab") as f:
        f.write(file_content)
        f.flush()
        file_path = Path(f.name)

    with (
        patch("huawei_appgallery_mcp.api.file_upload.CHUNK_SIZE", 500),
        patch(
            "huawei_appgallery_mcp.api.file_upload.get_upload_client"
        ) as mock_get_client,
    ):
        mock_client = MagicMock()
        # Two chunks: chunk 1 (no dest_url), chunk 2 (last, returns dest_url)
        mock_client.post = AsyncMock(
            side_effect=[
                _chunk_response(),
                _chunk_response(dest_url="https://example.com/final.aab"),
            ]
        )
        mock_get_client.return_value = mock_client

        dest_url = await upload_file_in_chunks(
            "https://chunk-upload.example.com",
            "auth123",
            file_path,
        )

        assert dest_url == "https://example.com/final.aab"
        assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_upload_file_in_chunks_chunk_failure_retry():
    """Chunk 1 fails once with NetworkError, succeeds on retry."""
    file_content = b"b" * 1000

    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".aab") as f:
        f.write(file_content)
        f.flush()
        file_path = Path(f.name)

    with (
        patch("huawei_appgallery_mcp.api.file_upload.CHUNK_SIZE", 500),
        patch(
            "huawei_appgallery_mcp.api.file_upload.get_upload_client"
        ) as mock_get_client,
    ):
        mock_client = MagicMock()
        # Chunk 1: attempt 1 fails (NetworkError), attempt 2 succeeds
        # Chunk 2 (last): succeeds with dest_url
        mock_client.post = AsyncMock(
            side_effect=[
                NetworkError("transient error"),
                _chunk_response(),
                _chunk_response(dest_url="https://example.com/retry_ok.aab"),
            ]
        )
        mock_get_client.return_value = mock_client

        dest_url = await upload_file_in_chunks(
            "https://chunk-upload.example.com",
            "auth123",
            file_path,
        )

        assert dest_url == "https://example.com/retry_ok.aab"
        # 3 calls: 1 failed + 1 retry for chunk 1, + 1 for chunk 2
        assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_upload_file_in_chunks_chunk_failure_exhausted():
    """Chunk fails all MAX_CHUNK_RETRIES attempts, NetworkError raised."""
    file_content = b"c" * 1000

    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".aab") as f:
        f.write(file_content)
        f.flush()
        file_path = Path(f.name)

    with (
        patch("huawei_appgallery_mcp.api.file_upload.CHUNK_SIZE", 500),
        patch(
            "huawei_appgallery_mcp.api.file_upload.get_upload_client"
        ) as mock_get_client,
    ):
        mock_client = MagicMock()
        # All attempts fail
        mock_client.post = AsyncMock(
            side_effect=NetworkError("persistent error")
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(NetworkError, match="persistent error"):
            await upload_file_in_chunks(
                "https://chunk-upload.example.com",
                "auth123",
                file_path,
            )

        # Should have tried MAX_CHUNK_RETRIES times
        assert mock_client.post.call_count == MAX_CHUNK_RETRIES


@pytest.mark.asyncio
async def test_upload_file_in_chunks_calls_progress():
    """on_progress callback receives correct bytes after each chunk."""
    file_content = b"d" * 1000  # 1000 bytes, 2 chunks of 500

    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".aab") as f:
        f.write(file_content)
        f.flush()
        file_path = Path(f.name)

    with (
        patch("huawei_appgallery_mcp.api.file_upload.CHUNK_SIZE", 500),
        patch(
            "huawei_appgallery_mcp.api.file_upload.get_upload_client"
        ) as mock_get_client,
    ):
        mock_client = MagicMock()
        mock_client.post = AsyncMock(
            side_effect=[
                _chunk_response(),
                _chunk_response(dest_url="https://example.com/progress.aab"),
            ]
        )
        mock_get_client.return_value = mock_client

        progress_calls = []

        def on_progress(uploaded, total):
            progress_calls.append((uploaded, total))

        await upload_file_in_chunks(
            "https://chunk-upload.example.com",
            "auth123",
            file_path,
            on_progress=on_progress,
        )

        # 2 chunks: after chunk 1 (500 bytes), after chunk 2 (1000 bytes)
        assert len(progress_calls) == 2
        assert progress_calls[0] == (500, 1000)
        assert progress_calls[1] == (1000, 1000)
