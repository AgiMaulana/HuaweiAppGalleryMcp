# Repository Guidelines

## Project Structure & Module Organization
Core server code lives in `huawei_appgallery_mcp/`. Use `server.py` for MCP tool registration and request dispatch, `auth.py` for credential handling, and `api/` for AppGallery feature modules such as `app_info.py`, `file_upload.py`, `publish.py`, and `report.py`. Tests live in `tests/`; keep new test files alongside the behavior they cover, using names like `test_publish.py`. Release process notes are in `docs/RELEASE.md`. Root config files include `pyproject.toml`, `server.json`, and `glama.json`.

## Build, Test, and Development Commands
Create a local environment and install dev dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Run tests with `pytest`. Target a single file with `pytest tests/test_issue3_upload.py` when iterating on one area. Validate packaging with `pip install .` or `python -m pip install .` before cutting a release. The published CLI entry point is `huawei-app-gallery-mcp`.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, `snake_case` for functions and modules, `UPPER_SNAKE_CASE` for constants, and concise docstrings on public helpers. Prefer type hints where the module already uses them. Keep MCP tool names descriptive and action-oriented, matching the existing `query_app_info` / `update_release_time` pattern. No formatter or linter is configured in this repo, so keep changes PEP 8-aligned and consistent with surrounding code.

## Testing Guidelines
Use `pytest` with `pytest-asyncio` for async flows. Name tests `test_<behavior>` and mock external HTTP calls instead of hitting Huawei endpoints. Add focused regression tests for API quirks, dispatch behavior, and environment-driven configuration. Reuse `tests/conftest.py` for shared fixtures and env setup.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit style such as `feat(app-info): support channel_id queries` and `fix: add upload_file tool...`. Keep commit subjects short and scoped when useful. PRs should explain the AppGallery behavior changed, list tests run, and link the relevant issue. Include example payloads or command snippets when a new MCP tool or parameter is introduced.

## Release & Configuration Notes
Never commit real `HUAWEI_CLIENT_ID`, `HUAWEI_CLIENT_SECRET`, or app IDs. For package releases, follow the release-branch flow in `docs/RELEASE.md`: branch from `release/x.y.z`, bump `pyproject.toml`, tag `vx.y.z`, and publish the GitHub Release from that branch.
