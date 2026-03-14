"""
File Upload APIs

1. Get upload URL : GET  /publish/v2/upload-url
2. Upload file    : POST {uploadUrl}          (single, ≤4 GB)
3. Upload chunks  : POST {chunkUploadUrl}     (multi-part, >4 GB)
4. Attach files   : PUT  /publish/v2/app-file-info

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-upload-url-new-0000001111685200
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-upload-file-new-0000001111845090
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-obbfile-upload-0000001158245067
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-file-info-0000001111685202
"""

import math
from pathlib import Path
from typing import Any, Callable, Literal

import httpx

from huawei_appgallery_mcp.auth import AuthConfig, build_auth_headers, get_access_token

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
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/upload-url",
            params={"appId": app_id, "suffix": suffix, "releaseType": release_type},
            headers=build_auth_headers(token, config.client_id),
        )
    return _handle(response)


async def upload_file(
    upload_url: str,
    auth_code: str,
    file_path: Path,
) -> str:
    """
    Upload a single file (≤4 GB).

    Returns the fileDestUlr (destination URL) reported by Huawei.
    """
    file_name = file_path.name
    file_bytes = file_path.read_bytes()

    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(
            upload_url,
            data={"authCode": auth_code, "fileCount": "1"},
            files={"file": (file_name, file_bytes)},
        )
    data = _handle(response)
    return _extract_dest_url(data)


async def upload_file_in_chunks(
    chunk_upload_url: str,
    auth_code: str,
    file_path: Path,
    on_progress: Callable[[int, int], None] | None = None,
) -> str:
    """
    Upload a large file (>4 GB) in 5 MB chunks.

    Returns the fileDestUlr after all chunks are uploaded.
    """
    file_name = file_path.name
    file_size = file_path.stat().st_size
    total_chunks = math.ceil(file_size / CHUNK_SIZE)
    dest_url = ""

    with file_path.open("rb") as fh:
        for chunk_num in range(1, total_chunks + 1):
            chunk_data = fh.read(CHUNK_SIZE)
            is_last = chunk_num == total_chunks

            async with httpx.AsyncClient(timeout=600) as client:
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
            data = _handle(response)
            if is_last:
                dest_url = _extract_dest_url(data)

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
    files: list of {"fileName": ..., "fileDestUlr": ..., "sha256": ...}
    """
    token = await get_access_token(config)
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}/app-file-info",
            params={"appId": app_id},
            headers=build_auth_headers(token, config.client_id),
            json={"fileType": file_type, "files": files},
        )
    return _handle(response)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _handle(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    if data.get("ret", {}).get("code", 0) != 0:
        ret = data["ret"]
        raise RuntimeError(f"AppGallery API error {ret['code']}: {ret.get('msg', '')}")
    return data


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
