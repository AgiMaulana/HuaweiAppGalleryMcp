# Release Guide

PyPI publishing is triggered by [`.github/workflows/publish-pypi.yml`](/Users/agi.maulana/Documents/Workspace/HuaweiAppGalleryMcp/.github/workflows/publish-pypi.yml) when a GitHub Release is published.

This repository uses a release-branch flow for package publishing:

1. Cut a branch named `release/x.y.z` from the commit you want to publish.
2. Bump [`pyproject.toml`](/Users/agi.maulana/Documents/Workspace/HuaweiAppGalleryMcp/pyproject.toml) to `x.y.z` on that release branch.
3. Validate the build from the release branch.
4. Create a Git tag `vx.y.z` from that release branch commit.
5. Publish the GitHub Release for `vx.y.z`.

## Workflow checks

The publish workflow validates two things before publishing to PyPI:

- The release target must be a `release/*` branch.
- The GitHub Release tag must match the package version in `pyproject.toml`.

## Example

```bash
git checkout -b release/1.1.2
# edit pyproject.toml -> version = "1.1.2"
git commit -am "chore: bump version to 1.1.2"
git tag v1.1.2
git push origin release/1.1.2
git push origin v1.1.2
```

Then publish the GitHub Release for `v1.1.2`, making sure its target branch is `release/1.1.2`.
