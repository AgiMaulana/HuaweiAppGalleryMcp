"""
Huawei AppGallery Connect MCP Server

Manages the full app publishing lifecycle:
  1. Query / update app info
  2. Manage language / localization info
  3. Upload APK / AAB files (single or chunked)
  4. Submit app for release

Configuration via environment variables:
  HUAWEI_CLIENT_ID      – AppGallery Connect API client ID
  HUAWEI_CLIENT_SECRET  – AppGallery Connect API client secret
"""

import json
from pathlib import Path
from typing import Any

# Load .env from the working directory (or any parent) if present.
# This lets users set HUAWEI_CLIENT_ID / HUAWEI_CLIENT_SECRET in a .env file
# without needing to export them in the shell or MCP config.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can still be set directly

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from huawei_appgallery_mcp.auth import AuthConfig
from huawei_appgallery_mcp.api.app_info import query_app_info, update_app_info
from huawei_appgallery_mcp.api.language_info import (
    update_language_info,
    delete_language_info,
)
from huawei_appgallery_mcp.api.file_upload import (
    CHUNK_THRESHOLD,
    get_upload_url,
    update_app_file_info,
    upload_file,
    upload_file_in_chunks,
)
from huawei_appgallery_mcp.api.publish import submit_app, submit_app_with_file

app = Server("huawei-appgallery-mcp")

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    # ── App Info ──────────────────────────────────────────────────────────────
    Tool(
        name="query_app_info",
        description=(
            "Query the current metadata of an app (name, description, category, "
            "content rating, etc.) from Huawei AppGallery Connect."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "release_type": {
                    "type": "integer",
                    "enum": [1, 3],
                    "description": "1 = formal release (default), 3 = phased/grey release.",
                },
            },
            "required": ["app_id"],
        },
    ),
    Tool(
        name="update_app_info",
        description=(
            "Update app metadata (name, description, category, privacy policy, "
            "content rating, support contact, etc.) in the AppGallery Connect draft."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "default_lang": {"type": "string", "description": 'Default language tag, e.g. "en-US".'},
                "app_name": {"type": "string", "description": "App display name."},
                "app_desc": {"type": "string", "description": "Full app description (shown on store page)."},
                "brief_desc": {"type": "string", "description": "Short tagline / brief description."},
                "privacy_policy": {"type": "string", "description": "URL of the app's privacy policy."},
                "category_id": {"type": "string", "description": "Primary category ID from AppGallery taxonomy."},
                "sub_category_id": {"type": "string", "description": "Sub-category ID from AppGallery taxonomy."},
                "cs_email": {"type": "string", "description": "Customer support email address."},
                "cs_phone": {"type": "string", "description": "Customer support phone number."},
                "cs_url": {"type": "string", "description": "Customer support URL."},
                "content_rating": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4],
                    "description": "1=Everyone, 2=Pre-teen, 3=Teen, 4=Mature.",
                },
                "age_rating": {"type": "integer", "description": "Age rating (e.g. 7, 12, 16, 18)."},
            },
            "required": ["app_id"],
        },
    ),

    # ── Language Info ──────────────────────────────────────────────────────────
    Tool(
        name="update_language_info",
        description=(
            "Add or update localized store listing content (app name, description, "
            "release notes) for a specific language."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "lang": {
                    "type": "string",
                    "description": 'BCP-47 language tag, e.g. "en-US", "zh-CN", "id".',
                },
                "app_name": {"type": "string", "description": "App name in this language."},
                "app_desc": {"type": "string", "description": "App description in this language."},
                "brief_desc": {"type": "string", "description": "Brief introduction in this language."},
                "new_features": {
                    "type": "string",
                    "description": "\"What's new\" release notes in this language.",
                },
            },
            "required": ["app_id", "lang"],
        },
    ),
    Tool(
        name="delete_language_info",
        description="Remove a localized store listing for a specific language from the app draft.",
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "lang": {"type": "string", "description": 'Language tag to delete, e.g. "fr-FR".'},
            },
            "required": ["app_id", "lang"],
        },
    ),

    # ── File Upload ────────────────────────────────────────────────────────────
    Tool(
        name="get_upload_url",
        description=(
            "Obtain a pre-signed upload URL and auth code from Huawei before uploading "
            "an APK, AAB, or other file. Returns uploadUrl, chunkUploadUrl, and authCode."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "suffix": {
                    "type": "string",
                    "enum": ["apk", "aab", "rpk", "pdf", "jpg", "jpeg", "png"],
                    "description": "File extension of the file to upload.",
                },
                "file_name": {
                    "type": "string",
                    "description": "File name (used locally to determine suffix if suffix not provided).",
                },
                "release_type": {
                    "type": "integer",
                    "enum": [1, 3],
                    "description": "1 = formal release (default), 3 = phased release.",
                },
            },
            "required": ["app_id", "suffix"],
        },
    ),
    Tool(
        name="upload_app_file",
        description=(
            "Upload an APK or AAB file from the local filesystem to Huawei AppGallery. "
            "Handles the full flow: get upload URL → upload (chunked automatically for files >4 GB) "
            "→ attach file to app draft. Returns the API response."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the APK or AAB file on the local machine.",
                },
                "file_type": {
                    "type": "integer",
                    "enum": [1, 2, 5],
                    "description": "1=APK, 2=RPK, 5=AAB.",
                },
            },
            "required": ["app_id", "file_path", "file_type"],
        },
    ),
    Tool(
        name="update_app_file_info",
        description=(
            "Manually attach one or more already-uploaded files to the app draft. "
            "Use this after you ran get_upload_url and uploaded files yourself."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "file_type": {
                    "type": "integer",
                    "enum": [1, 2, 5],
                    "description": "1=APK, 2=RPK, 5=AAB.",
                },
                "files": {
                    "type": "array",
                    "description": "Array of uploaded file descriptors.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_name": {"type": "string"},
                            "file_dest_url": {
                                "type": "string",
                                "description": "Destination URL returned by the upload endpoint.",
                            },
                            "sha256": {"type": "string", "description": "SHA-256 hash of the file (recommended)."},
                        },
                        "required": ["file_name", "file_dest_url"],
                    },
                },
            },
            "required": ["app_id", "file_type", "files"],
        },
    ),

    # ── Publishing ─────────────────────────────────────────────────────────────
    Tool(
        name="submit_app",
        description=(
            "Submit the app for review and release on Huawei AppGallery. "
            "All app info and file info must be saved before calling this. "
            "Supports full release, phased (grey) release, and scheduled release."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "release_type": {
                    "type": "integer",
                    "enum": [1, 3],
                    "description": "1 = full release to all users (default), 3 = phased/grey release.",
                },
                "release_percent": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Percentage of users to receive the update. Only used when release_type=3.",
                },
                "release_time": {
                    "type": "integer",
                    "description": "Scheduled release timestamp in Unix milliseconds. Omit for immediate.",
                },
                "remark": {"type": "string", "description": "Internal release notes (not shown to users)."},
            },
            "required": ["app_id"],
        },
    ),
    Tool(
        name="submit_app_with_file",
        description=(
            "Submit the app for release when the APK/AAB is hosted on your own server. "
            "Huawei will download the file from the provided HTTPS URL during the review process."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The AppGallery Connect app ID."},
                "file_type": {
                    "type": "integer",
                    "enum": [1, 2, 5],
                    "description": "1=APK, 2=RPK, 5=AAB.",
                },
                "files": {
                    "type": "array",
                    "description": "Array of files hosted on your server.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_name": {"type": "string"},
                            "file_url": {
                                "type": "string",
                                "description": "HTTPS URL where Huawei can download the file.",
                            },
                            "sha256": {"type": "string"},
                        },
                        "required": ["file_name", "file_url"],
                    },
                },
                "release_type": {
                    "type": "integer",
                    "enum": [1, 3],
                    "description": "1 = full release (default), 3 = phased release.",
                },
                "release_percent": {"type": "integer", "minimum": 1, "maximum": 100},
                "release_time": {"type": "integer", "description": "Scheduled release timestamp in Unix ms."},
                "remark": {"type": "string"},
            },
            "required": ["app_id", "file_type", "files"],
        },
    ),
]

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        config = AuthConfig.from_env()
        result = await _dispatch(name, arguments, config)
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]


async def _dispatch(name: str, args: dict[str, Any], config: AuthConfig) -> Any:
    match name:
        # ── App Info ──────────────────────────────────────────────────────────
        case "query_app_info":
            return await query_app_info(
                config,
                args["app_id"],
                release_type=args.get("release_type", 1),
            )

        case "update_app_info":
            return await update_app_info(
                config,
                args["app_id"],
                default_lang=args.get("default_lang"),
                app_name=args.get("app_name"),
                app_desc=args.get("app_desc"),
                brief_desc=args.get("brief_desc"),
                privacy_policy=args.get("privacy_policy"),
                category_id=args.get("category_id"),
                sub_category_id=args.get("sub_category_id"),
                cs_email=args.get("cs_email"),
                cs_phone=args.get("cs_phone"),
                cs_url=args.get("cs_url"),
                content_rating=args.get("content_rating"),
                age_rating=args.get("age_rating"),
            )

        # ── Language Info ─────────────────────────────────────────────────────
        case "update_language_info":
            return await update_language_info(
                config,
                args["app_id"],
                args["lang"],
                app_name=args.get("app_name"),
                app_desc=args.get("app_desc"),
                brief_desc=args.get("brief_desc"),
                new_features=args.get("new_features"),
            )

        case "delete_language_info":
            return await delete_language_info(config, args["app_id"], args["lang"])

        # ── File Upload ───────────────────────────────────────────────────────
        case "get_upload_url":
            suffix = args["suffix"]
            file_name = args.get("file_name")
            if not suffix and file_name:
                suffix = file_name.rsplit(".", 1)[-1].lower()
            return await get_upload_url(
                config,
                args["app_id"],
                suffix,
                file_name or "",
                release_type=args.get("release_type", 1),
            )

        case "upload_app_file":
            file_path = Path(args["file_path"])
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            suffix = file_path.suffix.lstrip(".").lower()
            file_name = file_path.name
            file_size = file_path.stat().st_size

            # Step 1 – get upload URL
            url_data = await get_upload_url(config, args["app_id"], suffix, file_name)
            upload_url = url_data.get("uploadUrl") or url_data.get("info", {}).get("uploadUrl", "")
            chunk_url = url_data.get("chunkUploadUrl") or url_data.get("info", {}).get("chunkUploadUrl", "")
            auth_code = url_data.get("authCode") or url_data.get("info", {}).get("authCode", "")

            # Step 2 – upload
            if file_size > CHUNK_THRESHOLD:
                dest_url = await upload_file_in_chunks(chunk_url, auth_code, file_path)
            else:
                dest_url = await upload_file(upload_url, auth_code, file_path)

            # Step 3 – attach to draft
            result = await update_app_file_info(
                config,
                args["app_id"],
                args["file_type"],
                [{"fileName": file_name, "fileDestUlr": dest_url}],
            )
            result["_uploadedFileUrl"] = dest_url
            return result

        case "update_app_file_info":
            # Normalize snake_case → camelCase expected by the API
            api_files = [
                {
                    "fileName": f["file_name"],
                    "fileDestUlr": f["file_dest_url"],
                    **({"sha256": f["sha256"]} if "sha256" in f else {}),
                }
                for f in args["files"]
            ]
            return await update_app_file_info(
                config, args["app_id"], args["file_type"], api_files
            )

        # ── Publishing ────────────────────────────────────────────────────────
        case "submit_app":
            return await submit_app(
                config,
                args["app_id"],
                release_type=args.get("release_type", 1),
                release_percent=args.get("release_percent"),
                release_time=args.get("release_time"),
                remark=args.get("remark"),
            )

        case "submit_app_with_file":
            # Normalize snake_case → camelCase
            api_files = [
                {
                    "fileName": f["file_name"],
                    "fileUrl": f["file_url"],
                    **({"sha256": f["sha256"]} if "sha256" in f else {}),
                }
                for f in args["files"]
            ]
            return await submit_app_with_file(
                config,
                args["app_id"],
                args["file_type"],
                api_files,
                release_type=args.get("release_type", 1),
                release_percent=args.get("release_percent"),
                release_time=args.get("release_time"),
                remark=args.get("remark"),
            )

        case _:
            raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    import asyncio

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
