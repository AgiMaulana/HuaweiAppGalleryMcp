# Huawei AppGallery MCP

<!-- mcp-name: io.github.AgiMaulana/HuaweiAppGalleryMcp -->

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for managing app publishing on **Huawei AppGallery Connect**. Integrates directly with Claude Desktop or any MCP-compatible client.

[![Huawei App Gallery MCP server](https://glama.ai/mcp/servers/AgiMaulana/HuaweiAppGalleryMcp/badges/card.svg)](https://glama.ai/mcp/servers/AgiMaulana/HuaweiAppGalleryMcp)

## Features

- Query and update app metadata (name, description, category, ratings, support contacts)
- Manage localized store listings per language
- Upload APK / AAB files with automatic chunked upload for large files (>4 GB)
- Submit apps for full release, phased (grey) release, scheduled release, or open testing (`channel_id=2`)
- Submit apps when the binary is hosted on your own server
- Manage phased release lifecycle (state changes, percentage updates)
- Query AAB compilation status
- Update scheduled release time
- Set GMS dependency flag
- Obtain download/installation and install-failure report URLs

## Installation

```bash
pip install huawei-app-gallery-mcp
```

Or with `uv`:

```bash
uv pip install huawei-app-gallery-mcp
```

## Configuration

### 1. Get API credentials

1. Go to [AppGallery Connect](https://developer.huawei.com/consumer/en/service/josp/agc/index.html)
2. Navigate to **Users & Permissions** → **API key** → **Connect API**
3. Click **Create** and select the **App manager** role
4. Copy the **Client ID** and **Client Secret**

> These are **Connect API** credentials — different from HMS Core app credentials.

### 2. Set environment variables

Create a `.env` file in your working directory (the server loads it automatically):

```bash
HUAWEI_CLIENT_ID=your_connect_api_client_id
HUAWEI_CLIENT_SECRET=your_connect_api_client_secret

# Optional: set a default app ID so you don't have to pass it to every tool call
HUAWEI_APP_ID=your_app_id
```

### 3. Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "huawei-appgallery": {
      "command": "huawei-app-gallery-mcp",
      "env": {
        "HUAWEI_CLIENT_ID": "your_client_id",
        "HUAWEI_CLIENT_SECRET": "your_client_secret",
        "HUAWEI_APP_ID": "your_app_id"
      }
    }
  }
}
```

### Connect to Claude Code (machine-level)

Create `/Library/Application Support/ClaudeCode/managed-mcp.json` (macOS) or `/etc/claude-code/managed-mcp.json` (Linux):

```json
{
  "mcpServers": {
    "huawei-appgallery": {
      "type": "stdio",
      "command": "huawei-app-gallery-mcp",
      "env": {
        "HUAWEI_CLIENT_ID": "your_client_id",
        "HUAWEI_CLIENT_SECRET": "your_client_secret",
        "HUAWEI_APP_ID": "your_app_id"
      }
    }
  }
}
```

## Tools

All tools accept an optional `app_id` argument. If omitted, `HUAWEI_APP_ID` from the environment is used as the default.

| Tool | Description |
|---|---|
| `query_app_info` | Query current app metadata (name, description, category, ratings, etc.) |
| `update_app_info` | Update app metadata in the AppGallery Connect draft |
| `update_language_info` | Add or update a localized store listing for a specific language |
| `delete_language_info` | Remove a localized store listing |
| `get_upload_url` | Obtain a pre-signed upload URL and auth code before uploading a file |
| `upload_app_file` | Upload an APK/AAB from local disk and attach it to the app draft (auto-chunked for >4 GB) |
| `update_app_file_info` | Manually attach already-uploaded files to the app draft |
| `query_compile_status` | Query AAB compilation status for one or more package IDs |
| `submit_app` | Submit the app for review and release (supports full, phased, scheduled, and open testing via `channel_id=2`) |
| `submit_app_with_file` | Submit when the binary is hosted on your own server |
| `change_phased_release_state` | Change phased release status: proceed, roll back, or stop |
| `update_phased_release` | Convert phased release to full release or update the rollout schedule/percentage |
| `update_release_time` | Update the scheduled release time (only when app is in Releasing state) |
| `set_gms_dependency` | Report whether the app depends on GMS |
| `get_download_report_url` | Get download URL for the app download & installation report (CSV/Excel, max 180 days) |
| `get_install_failure_report_url` | Get download URL for the installation failure report (CSV/Excel, max 180 days) |

## Usage Examples

**Upload and release a new version:**

> Upload `/path/to/app-release.aab` (AAB, file type 5) then submit it for a full release.

**Phased rollout:**

> Submit the app for a phased release to 20% of users.

**Open testing:**

> Submit the app for open testing (channel_id=2).

**Update release notes:**

> Update the English release notes to "Bug fixes and performance improvements".

**Scheduled release:**

> Submit the app for release on March 20, 2026 at 10:00 UTC.

**Download report:**

> Get the download and installation report URL for the last 30 days in English CSV format.

## Publishing Workflow

```
Update app info  →  Update language info  →  Upload APK/AAB  →  Submit app
```

1. Use `update_app_info` / `update_language_info` to set metadata and release notes
2. Use `upload_app_file` to upload the binary (handles chunking automatically)
3. Use `submit_app` to trigger review and release

## API Reference

This server wraps the [AppGallery Connect Publishing API](https://developer.huawei.com/consumer/en/doc/AppGallery-connect-Guides/agcapi-getstarted-0000001111845062).

## License

MIT