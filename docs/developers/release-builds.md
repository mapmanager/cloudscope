# Release builds

CloudScope release builds are part of the project's reproducibility strategy. Official releases are tied to git tags so the source code, desktop application artifacts, and deployed web application state can be associated with a specific version.

Using published versions gives scientific users a stable reference point while allowing development to continue with new analysis methods, file-format support, and GUI features.

## Versioned release workflow

A typical release workflow is:

1. Update and test the source tree.
2. Create a git tag for the release version.
3. Push the tag to GitHub.
4. Build release artifacts for supported platforms.
5. Archive the source code and desktop app artifacts on the GitHub Releases page.
6. Deploy or record the matching web application version.

## Desktop builds

CloudScope desktop builds are created with NiceGUI Pack / PyInstaller.

## macOS security pipeline

The macOS release process includes:

1. Build the app bundle.
2. Locally code sign the app.
3. Zip the app bundle.
4. Upload the zip to Apple notarization.
5. Wait for notarization approval.
6. On approval, sign/staple the notarized artifact.
7. Distribute the final desktop app.

## Windows builds

Windows release details should be documented here once the release artifact workflow is finalized.
