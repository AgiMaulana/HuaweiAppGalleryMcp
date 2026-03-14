# Huawei AppGallery MCP

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for managing app publishing on **Huawei AppGallery Connect**. Integrates directly with Claude Desktop or any MCP-compatible client.

## Features

- Query and update app metadata (name, description, category, ratings, support contacts)
- Manage localized store listings per language
- Upload APK / AAB files with automatic chunked upload for large files (>4 GB)
- Submit apps for full release, phased (grey) release, or scheduled release
- Submit apps when the binary is hosted on your own server

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
3. Create a key and copy the **Client ID** and **Client Secret**

### 2. Set environment variables

```bash
export HUAWEI_CLIENT_ID=your_client_id
export HUAWEI_CLIENT_SECRET=your_client_secret
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
        "HUAWEI_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

If you installed into a virtual environment, use the full path to the executable instead:

```json
{
  "mcpServers": {
    "huawei-appgallery": {
      "command": "/path/to/.venv/bin/huawei-app-gallery-mcp",
      "env": {
        "HUAWEI_CLIENT_ID": "your_client_id",
        "HUAWEI_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

## Tools

| Tool | Description |
|---|---|
| `query_app_info` | Query current app metadata (name, description, category, ratings, etc.) |
| `update_app_info` | Update app metadata in the AppGallery Connect draft |
| `update_language_info` | Add or update a localized store listing for a specific language |
| `delete_language_info` | Remove a localized store listing |
| `get_upload_url` | Obtain a pre-signed upload URL and auth code before uploading a file |
| `upload_app_file` | Upload an APK/AAB from local disk and attach it to the app draft (auto-chunked for large files) |
| `update_app_file_info` | Manually attach already-uploaded files to the app draft |
| `submit_app` | Submit the app for review and release |
| `submit_app_with_file` | Submit when the binary is hosted on your own server |

## Usage Examples

**Upload and release a new version:**

> Upload `/path/to/app-release.aab` (AAB, file type 5) for app ID `123456789`, then submit it for a full release.

**Phased rollout:**

> Submit app `123456789` for a phased release to 20% of users.

**Update release notes:**

> Update the English release notes for app `123456789` to "Bug fixes and performance improvements".

**Scheduled release:**

> Submit app `123456789` for release on March 20, 2026 at 10:00 UTC.

## Publishing Workflow

```
Update app info  →  Update language info  →  Upload APK/AAB  →  Submit app
```

1. Use `update_app_info` / `update_language_info` to set metadata and release notes
2. Use `upload_app_file` to upload the binary (handles chunking automatically)
3. Use `submit_app` to trigger the review and release

## API Reference

This server wraps the [AppGallery Connect Publishing API](https://developer.huawei.com/consumer/en/doc/AppGallery-connect-Guides/agcapi-getstarted-0000001111845062).

## License

MIT
