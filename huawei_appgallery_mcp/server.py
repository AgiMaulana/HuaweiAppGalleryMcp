"""
Huawei AppGallery Connect MCP Server

Manages the full app publishing lifecycle:
  1. Query / update app info
  2. Manage language / localization info
  3. Upload APK / AAB files (single or chunked)
  4. Submit app for release

Configuration via environment variables (set in .env or MCP config env block):
  HUAWEI_CLIENT_ID      – Connect API client ID from AGC Console → Users & Permissions → API key (required)
  HUAWEI_CLIENT_SECRET  – Connect API client secret (required)
  HUAWEI_APP_ID         – Default app ID; all tools fall back to this when app_id is not passed (optional)
"""

import json
from pathlib import Path
from typing import Any

# Load .env from the working directory (or any parent) if present.
# This lets users set credentials in a .env file without exporting them in the shell.
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
    query_compile_status,
    update_app_file_info,
    upload_file,
    upload_file_in_chunks,
)
from huawei_appgallery_mcp.api.publish import (
    change_phased_release_state,
    set_gms_dependency,
    submit_app,
    submit_app_with_file,
    update_phased_release,
    update_release_time,
)
from huawei_appgallery_mcp.api.report import (
    get_download_report_url,
    get_install_failure_report_url,
)

app = Server("huawei-appgallery-mcp")

# Shared app_id property injected into every tool schema
_APP_ID_PROP = {
    "type": "string",
    "description": (
        "AppGallery Connect app ID. "
        "Optional if HUAWEI_APP_ID is set in the environment."
    ),
}

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
                "app_id": _APP_ID_PROP,
                "release_type": {
                    "type": "integer",
                    "enum": [1, 3],
                    "description": "1 = formal release (default), 3 = phased/grey release.",
                },
            },
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
                "app_id": _APP_ID_PROP,
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
                "app_id": _APP_ID_PROP,
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
            "required": ["lang"],
        },
    ),
    Tool(
        name="delete_language_info",
        description="Remove a localized store listing for a specific language from the app draft.",
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
                "lang": {"type": "string", "description": 'Language tag to delete, e.g. "fr-FR".'},
            },
            "required": ["lang"],
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
                "app_id": _APP_ID_PROP,
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
            "required": ["suffix"],
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
                "app_id": _APP_ID_PROP,
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
            "required": ["file_path", "file_type"],
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
                "app_id": _APP_ID_PROP,
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
            "required": ["file_type", "files"],
        },
    ),

    # ── Publishing ─────────────────────────────────────────────────────────────
    Tool(
        name="submit_app",
        description=(
            "Submit the app for review and release on Huawei AppGallery. "
            "All app info and file info must be saved before calling this. "
            "Supports full release, phased (grey) release, scheduled release, and channel-specific release (e.g. open testing via channel_id=2)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
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
                "channel_id": {
                    "type": "integer",
                    "description": "Optional channel ID. Use 2 for open testing.",
                },
            },
        },
    ),
    Tool(
        name="change_phased_release_state",
        description="Change the release status of an app in phased (grey) release — proceed, roll back, or stop.",
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
                "state": {
                    "type": "string",
                    "description": "RELEASE = proceed, ROLLBACK = roll back, GRAY_TERMINATED = stop phased release.",
                },
                "phased_release_start_time": {"type": "string", "description": "UTC datetime, e.g. 2026-05-01T00:00:00+0800."},
                "phased_release_end_time": {"type": "string", "description": "UTC datetime, e.g. 2026-05-15T00:00:00+0800."},
                "phased_release_percent": {"type": "string", "description": "Rollout percentage, e.g. \"50.00\"."},
            },
            "required": ["state"],
        },
    ),
    Tool(
        name="update_phased_release",
        description="Change a phased release to full release, or update the phased release schedule/percentage.",
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
                "state": {"type": "string", "description": "Release state, e.g. RELEASE."},
                "phased_release_start_time": {"type": "string", "description": "UTC datetime, e.g. 2026-05-01T00:00:00+0800."},
                "phased_release_end_time": {"type": "string", "description": "UTC datetime, e.g. 2026-05-15T00:00:00+0800."},
                "phased_release_percent": {"type": "string", "description": "Rollout percentage, e.g. \"50.00\"."},
                "release_type": {
                    "type": "integer",
                    "enum": [1, 3],
                    "description": "1 = convert to full release, 3 = keep as phased (default).",
                },
            },
            "required": ["state"],
        },
    ),
    Tool(
        name="update_release_time",
        description=(
            "Update the scheduled release time of a version. "
            "Only callable when the app is in Releasing state."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
                "change_type": {
                    "type": "integer",
                    "enum": [1, 2, 3],
                    "description": "1 = release immediately, 2 = release as scheduled, 3 = update scheduled time.",
                },
                "release_time": {
                    "type": "string",
                    "description": "UTC datetime string, e.g. 2026-04-01T10:00:00+0800. Required for change_type 2 or 3.",
                },
                "release_type": {
                    "type": "integer",
                    "enum": [1, 3],
                    "description": "1 = full release (default), 3 = phased.",
                },
            },
            "required": ["change_type"],
        },
    ),
    Tool(
        name="set_gms_dependency",
        description="Report whether the app depends on GMS (Google Mobile Services) to AppGallery Connect.",
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
                "need_gms": {
                    "type": "integer",
                    "enum": [0, 1],
                    "description": "0 = does not depend on GMS, 1 = depends on GMS.",
                },
            },
            "required": ["need_gms"],
        },
    ),
    Tool(
        name="query_compile_status",
        description="Query the AAB compilation status for one or more app package IDs returned after uploading.",
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
                "pkg_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of app package IDs to query.",
                },
            },
            "required": ["pkg_ids"],
        },
    ),
    Tool(
        name="get_download_report_url",
        description=(
            "Obtain the download URL of the app download and installation report (CSV or Excel). "
            "Max date range: 180 days."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
                "language": {
                    "type": "string",
                    "enum": ["zh-CN", "en-US", "ru-RU"],
                    "description": "Language for report column headers.",
                },
                "start_time": {"type": "string", "description": "Start date in YYYYMMDD format (UTC)."},
                "end_time": {"type": "string", "description": "End date in YYYYMMDD format (UTC)."},
                "group_by": {
                    "type": "string",
                    "description": "Grouping dimension: date (default), countryId, businessType, or appVersion.",
                },
                "export_type": {
                    "type": "string",
                    "enum": ["CSV", "EXCEL"],
                    "description": "Export format. Default: CSV.",
                },
            },
            "required": ["language", "start_time", "end_time"],
        },
    ),
    Tool(
        name="get_install_failure_report_url",
        description=(
            "Obtain the download URL of the app installation failure data report (CSV or Excel). "
            "Max date range: 180 days."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_id": _APP_ID_PROP,
                "language": {
                    "type": "string",
                    "enum": ["zh-CN", "en-US", "ru-RU"],
                    "description": "Language for report column headers.",
                },
                "start_time": {"type": "string", "description": "Start date in YYYYMMDD format (UTC)."},
                "end_time": {"type": "string", "description": "End date in YYYYMMDD format (UTC)."},
                "group_by": {
                    "type": "string",
                    "description": "Grouping dimension: date (default), deviceName, downloadType, appVersion, or countryId.",
                },
                "export_type": {
                    "type": "string",
                    "enum": ["CSV", "EXCEL"],
                    "description": "Export format. Default: CSV.",
                },
            },
            "required": ["language", "start_time", "end_time"],
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
                "app_id": _APP_ID_PROP,
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
            "required": ["file_type", "files"],
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
                config.resolve_app_id(args.get("app_id")),
                release_type=args.get("release_type", 1),
            )

        case "update_app_info":
            return await update_app_info(
                config,
                config.resolve_app_id(args.get("app_id")),
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
                config.resolve_app_id(args.get("app_id")),
                args["lang"],
                app_name=args.get("app_name"),
                app_desc=args.get("app_desc"),
                brief_desc=args.get("brief_desc"),
                new_features=args.get("new_features"),
            )

        case "delete_language_info":
            return await delete_language_info(
                config,
                config.resolve_app_id(args.get("app_id")),
                args["lang"],
            )

        # ── File Upload ───────────────────────────────────────────────────────
        case "get_upload_url":
            suffix = args["suffix"]
            file_name = args.get("file_name")
            if not suffix and file_name:
                suffix = file_name.rsplit(".", 1)[-1].lower()
            return await get_upload_url(
                config,
                config.resolve_app_id(args.get("app_id")),
                suffix,
                file_name or "",
                release_type=args.get("release_type", 1),
            )

        case "upload_app_file":
            file_path = Path(args["file_path"])
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            app_id = config.resolve_app_id(args.get("app_id"))
            suffix = file_path.suffix.lstrip(".").lower()
            file_name = file_path.name
            file_size = file_path.stat().st_size

            # Step 1 – get upload URL
            url_data = await get_upload_url(config, app_id, suffix, file_name)
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
                app_id,
                args["file_type"],
                [{"fileName": file_name, "fileDestUrl": dest_url}],
            )
            result["_uploadedFileUrl"] = dest_url
            return result

        case "update_app_file_info":
            api_files = [
                {
                    "fileName": f["file_name"],
                    "fileDestUrl": f["file_dest_url"],
                    **({"sha256": f["sha256"]} if "sha256" in f else {}),
                }
                for f in args["files"]
            ]
            return await update_app_file_info(
                config,
                config.resolve_app_id(args.get("app_id")),
                args["file_type"],
                api_files,
            )

        # ── Publishing ────────────────────────────────────────────────────────
        case "submit_app":
            return await submit_app(
                config,
                config.resolve_app_id(args.get("app_id")),
                release_type=args.get("release_type", 1),
                release_percent=args.get("release_percent"),
                release_time=args.get("release_time"),
                remark=args.get("remark"),
                channel_id=args.get("channel_id"),
            )

        case "change_phased_release_state":
            return await change_phased_release_state(
                config,
                config.resolve_app_id(args.get("app_id")),
                state=args["state"],
                phased_release_start_time=args.get("phased_release_start_time"),
                phased_release_end_time=args.get("phased_release_end_time"),
                phased_release_percent=args.get("phased_release_percent"),
            )

        case "update_phased_release":
            return await update_phased_release(
                config,
                config.resolve_app_id(args.get("app_id")),
                state=args["state"],
                phased_release_start_time=args.get("phased_release_start_time"),
                phased_release_end_time=args.get("phased_release_end_time"),
                phased_release_percent=args.get("phased_release_percent"),
                release_type=args.get("release_type", 3),
            )

        case "update_release_time":
            return await update_release_time(
                config,
                config.resolve_app_id(args.get("app_id")),
                change_type=args["change_type"],
                release_time=args.get("release_time"),
                release_type=args.get("release_type", 1),
            )

        case "set_gms_dependency":
            return await set_gms_dependency(
                config,
                config.resolve_app_id(args.get("app_id")),
                need_gms=args["need_gms"],
            )

        case "query_compile_status":
            return await query_compile_status(
                config,
                config.resolve_app_id(args.get("app_id")),
                args["pkg_ids"],
            )

        case "get_download_report_url":
            return await get_download_report_url(
                config,
                config.resolve_app_id(args.get("app_id")),
                language=args["language"],
                start_time=args["start_time"],
                end_time=args["end_time"],
                group_by=args.get("group_by"),
                export_type=args.get("export_type"),
            )

        case "get_install_failure_report_url":
            return await get_install_failure_report_url(
                config,
                config.resolve_app_id(args.get("app_id")),
                language=args["language"],
                start_time=args["start_time"],
                end_time=args["end_time"],
                group_by=args.get("group_by"),
                export_type=args.get("export_type"),
            )

        case "submit_app_with_file":
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
                config.resolve_app_id(args.get("app_id")),
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
