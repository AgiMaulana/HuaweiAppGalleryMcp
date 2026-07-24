"""
File Upload APIs

1. Get upload URL      : GET  /publish/v2/upload-url
2. Upload file         : POST {uploadUrl}          (single, ≤4 GB)
3. Upload chunks       : POST {chunkUploadUrl}     (multi-part, >4 GB)
4. Attach files        : PUT  /publish/v2/app-file-info
5. Query compile status: GET  /publish/v2/package/compile/status

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-upload-url-new-0000001111685200
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-upload-file-new-0000001111845090
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-obbfile-upload-0000001158245067
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-file-info-0000001111685202
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-query-aabfile-0000001111685206
"""

import asyncio
import logging
import math
from pathlib import Path
from typing import Any, Callable, Literal

import httpx

from huawei_appgallery_mcp.api._helpers import handle_api_response
from huawei_appgallery_mcp.auth import AuthConfig, build_auth_headers, get_access_token
from huawei_appgallery_mcp.errors import NetworkError
from huawei_appgallery_mcp.http_client import get_client, get_upload_client

logger = logging.getLogger(__name__)

BASE_URL = "https://connect-api.cloud.huawei.com/api/publish/v2"

# Chunk size for large-file uploads: 5 MB
CHUNK_SIZE = 5 * 1024 * 1024

# Files larger than this are uploaded in chunks
CHUNK_THRESHOLD = 4 * 1024 * 1024 * 1024  # 4 GB

FileSuffix = Literal["apk", "aab", "rpk", "pdf", "jpg", "jpeg", "png"]


async def get_upload_url(
    config: AuthConfig,
    app_id: str,
    suffix: FileSuffix,
    file_name: str,
    release_type: int = 1,
) -> dict[str, Any]:
    """Obtain a pre-signed upload URL and auth code from Huawei."""
    token = await get_access_token(config)
    client = get_client()
    response = await client.get(
        f"{BASE_URL}/upload-url",
        params={"appId": app_id, "suffix": suffix, "releaseType": release_type},
        headers=build_auth_headers(token, config.client_id),
    )
    return handle_api_response(response)


async def upload_file(
    upload_url: str,
    auth_code: str,
    file_path: Path,
) -> str:
    """
    Upload a single file (≤4 GB).

    Streams the file in 5 MB chunks so memory usage stays constant
    regardless of file size. Returns the fileDestUrl reported by Huawei.
    """
    file_name = file_path.name

    async def file_stream():
        with file_path.open("rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    client = get_upload_client()
    response = await client.post(
        upload_url,
        data={"authCode": auth_code, "fileCount": "1"},
        files={"file": (file_name, file_stream())},
    )
    data = handle_api_response(response)
    return _extract_dest_url(data)


# Max retries per chunk for resilient large-file upload
MAX_CHUNK_RETRIES = 3


async def upload_file_in_chunks(
    chunk_upload_url: str,
    auth_code: str,
    file_path: Path,
    on_progress: Callable[[int, int], None] | None = None,
) -> str:
    """
    Upload a large file (>4 GB) in 5 MB chunks with per-chunk retry.

    Each chunk is retried up to MAX_CHUNK_RETRIES times on network errors
    with exponential backoff, so a transient failure at chunk 1023 doesn't
    restart the entire upload from chunk 1.

    Returns the fileDestUrl after all chunks are uploaded.
    """
    file_name = file_path.name
    file_size = file_path.stat().st_size
    total_chunks = math.ceil(file_size / CHUNK_SIZE)
    dest_url = ""

    client = get_upload_client()

    with file_path.open("rb") as fh:
        for chunk_num in range(1, total_chunks + 1):
            chunk_data = fh.read(CHUNK_SIZE)
            is_last = chunk_num == total_chunks

            for attempt in range(1, MAX_CHUNK_RETRIES + 1):
                try:
                    response = await client.post(
                        chunk_upload_url,
                        data={
                            "authCode": auth_code,
                            "fileCount": str(total_chunks),
                            "chunkNum": str(chunk_num),
                            "isLastChunk": "1" if is_last else "0",
                        },
                        files={"file": (file_name, chunk_data)},
                    )
                    data = handle_api_response(response)
                    if is_last:
                        dest_url = _extract_dest_url(data)
                    break
                except NetworkError:
                    if attempt == MAX_CHUNK_RETRIES:
                        raise
                    logger.warning(
                        "Chunk %d/%d failed (attempt %d), retrying...",
                        chunk_num, total_chunks, attempt,
                    )
                    await asyncio.sleep(2 ** attempt)

            if on_progress:
                uploaded = min(chunk_num * CHUNK_SIZE, file_size)
                on_progress(uploaded, file_size)

    return dest_url


async def update_app_file_info(
    config: AuthConfig,
    app_id: str,
    file_type: Literal[1, 2, 5],
    files: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Attach uploaded files to the app draft.

    file_type: 1=APK, 2=RPK, 5=AAB
    files: list of {"fileName": ..., "fileDestUrl": ..., "sha256": ...}
    """
    token = await get_access_token(config)
    client = get_client()
    response = await client.put(
        f"{BASE_URL}/app-file-info",
        params={"appId": app_id},
        headers=build_auth_headers(token, config.client_id),
        json={"fileType": file_type, "files": files},
    )
    return handle_api_response(response)


async def query_compile_status(
    config: AuthConfig,
    app_id: str,
    pkg_ids: list[str],
) -> dict[str, Any]:
    """
    Query the compilation status of one or more AAB packages.

    pkg_ids: list of app package IDs returned when the file was attached.
    """
    token = await get_access_token(config)
    client = get_client()
    response = await client.get(
        f"{BASE_URL}/package/compile/status",
        params={"appId": app_id, "pkgIds": ",".join(pkg_ids)},
        headers=build_auth_headers(token, config.client_id),
    )
    return handle_api_response(response)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_dest_url(data: dict[str, Any]) -> str:
    """Navigate the nested response to find the file destination URL.

    Huawei's API has a known typo: the field is 'fileDestUlr' (missing 'l')
    in some versions and 'fileDestUrl' in others. We check both.
    """
    try:
        rsp = data["result"]["UploadFileRsp"]
        return rsp.get("fileDestUlr") or rsp.get("fileDestUrl", "")
    except (KeyError, TypeError):
        pass
    return data.get("fileDestUlr") or data.get("fileDestUrl", "")
