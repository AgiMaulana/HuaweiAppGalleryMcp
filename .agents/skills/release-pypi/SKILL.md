---
name: release-pypi
description: Use when creating a new HuaweiAppGalleryMcp package release by cutting a release branch, bumping the Python package version in pyproject.toml, tagging the release, and publishing a GitHub Release that triggers PyPI publishing. This skill is specific to this repository's release-branch workflow and should be used for requests like "create a release", "publish to PyPI", "cut a release branch", "prepare the next version", or "bump the package version for release".
---

# Release PyPI

This repository publishes to PyPI from GitHub Releases. The workflow in `.github/workflows/publish-pypi.yml` only succeeds when:

- the GitHub Release target is a `release/*` branch
- the release tag matches `pyproject.toml` version exactly, as `v<version>`

## Use this workflow

1. Inspect the current package version in `pyproject.toml`, existing tags, GitHub releases, and PyPI state.
2. Choose the next version.
3. Cut `release/x.y.z` from the intended base commit, usually `main`.
4. Update `pyproject.toml` to `x.y.z` on that branch.
5. Commit the version bump.
6. Push the release branch.
7. Create tag `vx.y.z` from the release branch tip.
8. Push the tag.
9. Publish a GitHub Release for `vx.y.z` with `release/x.y.z` as the target.
10. Confirm the `publish-pypi.yml` workflow starts and watch for success or failure.

## Commands

Use non-interactive commands.

Check state:

```bash
git status --short --branch
git tag --sort=-version:refname | head
sed -n '1,120p' pyproject.toml
gh release list --limit 10
```

Cut branch and bump version:

```bash
git checkout -b release/1.1.2
```

Edit `pyproject.toml` so:

```toml
version = "1.1.2"
```

Commit and push:

```bash
git add pyproject.toml
git commit -m "chore: bump version to 1.1.2"
git push -u origin release/1.1.2
git tag v1.1.2
git push origin v1.1.2
```

Create the GitHub Release:

```bash
gh release create v1.1.2 \
  --target release/1.1.2 \
  --title v1.1.2 \
  --notes "Release v1.1.2"
```

Check workflow status:

```bash
gh run list --workflow publish-pypi.yml --limit 5 \
  --json databaseId,status,conclusion,headSha,displayTitle,event,createdAt,url
```

## Guardrails

- Do not publish from `main` directly unless the user explicitly changes the repository policy.
- Do not assume the Git tag drives the package version. The version is sourced from `pyproject.toml`.
- Do not reuse a version already present on PyPI.
- Before creating a release, verify whether that version already exists on PyPI, in GitHub tags, or as an existing GitHub Release.
- If a GitHub Release already exists for the version, do not recreate it without user confirmation.
- Prefer concise release notes unless the user asks for a detailed changelog.

## References

Read these files when needed:

- `.github/workflows/publish-pypi.yml`
- `docs/RELEASE.md`
- `pyproject.toml`
