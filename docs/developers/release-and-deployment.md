# Release and Deployment

CloudScope uses GitHub Actions, git tags, desktop build workflows, documentation deployment, and Docker deployment to support reproducible scientific software releases.

## Release workflow

CloudScope uses git tags to create official releases.

Example:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions then executes the release workflow and publishes release artifacts to the [CloudScope Releases](https://github.com/mapmanager/cloudscope/releases){target="_blank" rel="noopener"} page.

Official releases are intended to provide long-term reproducibility for scientific analysis.

## Desktop application builds

CloudScope is distributed as a native desktop application for macOS and Windows.

The desktop application and browser application use the same `acqstore` backend analysis engine.

### macOS

The macOS build process includes:

1. Build the application bundle.
2. Code sign the application.
3. ZIP the signed bundle.
4. Upload to Apple notarization.
5. Wait for notarization approval.
6. Staple the notarization ticket.
7. Publish the distributable artifact.

### Windows

The Windows build process generates a distributable ZIP archive containing the CloudScope executable and required runtime files.

## Documentation deployment

Documentation is built using MkDocs and Material for MkDocs.

GitHub Actions publishes documentation to GitHub Pages:

[CloudScope Documentation](https://mapmanager.github.io/cloudscope/){target="_blank" rel="noopener"}

## Docker deployment

CloudScope can be deployed as a containerized browser application.

Repository files:

- [Dockerfile](https://github.com/mapmanager/cloudscope/blob/main/Dockerfile){target="_blank" rel="noopener"}
- [docker-compose.yml](https://github.com/mapmanager/cloudscope/blob/main/docker-compose.yml){target="_blank" rel="noopener"}

The public deployment runs on Oracle Cloud infrastructure and is exposed through Cloudflare Tunnel:

[CloudScope Web Application](https://cloudscope.mapmanager.net){target="_blank" rel="noopener"}

## User data and uploads

The public deployment supports:

- sample data loading
- user file upload
- `.oir` files
- `.czi` files
- `.tif` files

Uploaded files remain separate from the CloudScope source repository.

## Versioned reproducibility

Scientific reproducibility is a primary project goal.

Every official release is associated with:

- git tag
- GitHub Release
- archived source code
- archived documentation
- archived desktop application artifacts

Users can reproduce analyses using the exact software version used to generate prior results.
