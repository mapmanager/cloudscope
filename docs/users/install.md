# Get the desktop app

!!! tip "Try CloudScope first"
    You can use the [web application](https://cloudscope.mapmanager.net){target="_blank" rel="noopener"}
    without installing anything.

Please [fill out this form](request-desktop-app.md) to request the desktop app for macOS or
Windows. We will email you a download link. After you receive the ZIP, use the platform steps
below to install and run it.

## Running the desktop app

=== "Windows"

    ### Unblock the ZIP

    !!! warning "Unblock before extracting"
        Windows marks files downloaded from the Internet with a security zone flag. If you skip
        this step, CloudScope may fail to start after extraction (see **Troubleshooting** below).

        1. Right-click the ZIP file.
        2. Select **Properties**.
        3. If an **Unblock** checkbox is present, enable it.
        4. Click **Apply**, then **OK**.

        Alternatively, use PowerShell:

        ```powershell
        Unblock-File "$env:USERPROFILE\Downloads\CloudScope-vX.Y.Z-windows-x64.zip"
        ```

    ### Extract

    1. Right-click the ZIP file.
    2. Select **Extract All…**
    3. Wait for extraction to complete.

    Do not run CloudScope directly from inside the ZIP archive.

    ### Run

    Open the extracted folder and double-click **`CloudScope.exe`**:

    ```text
    CloudScope/
    └── CloudScope.exe
    ```

    If Windows SmartScreen appears, select **More info**, then **Run anyway**.

    ### Troubleshooting

    **CloudScope does not start**

    If CloudScope reports a `Python.Runtime.dll` or pythonnet error when starting:

    1. Delete the extracted CloudScope folder.
    2. Unblock the original ZIP file.
    3. Extract the ZIP again.
    4. Launch `CloudScope.exe`.

    This error is commonly caused by Windows marking downloaded ZIP files as originating from the Internet.

    !!! info "Validated on"
        Windows 11 Home, Version 21H2, OS Build 22000.2538, 64-bit.

=== "macOS"

    CloudScope for macOS is a signed, notarized **`.app`** bundle for **Apple Silicon (arm64)** Macs. Intel Macs and universal builds are not supported.

    ### Install and run

    1. Double-click the ZIP file to extract **`CloudScope.app`**.
    2. Drag **CloudScope.app** to **Applications** (recommended).
    3. Open CloudScope from Applications.

    No Unblock step or SmartScreen workaround is required. The application is code signed and
    notarized by Apple.

    !!! info "Validated on"
        macOS Tahoe 26.2, Apple Silicon.

<!-- ## Verify your download (optional)
Each desktop ZIP on the Releases page has a matching `.sha256` checksum file. Download both files,
then compare the hash of the ZIP to the contents of the checksum file.
=== "Windows"
    ```powershell
    Get-FileHash "CloudScope-vX.Y.Z-windows-x64.zip" -Algorithm SHA256
    ```
    The hash should match the first field in `CloudScope-vX.Y.Z-windows-x64.zip.sha256`.
=== "macOS"
    ```bash
    shasum -a 256 CloudScope-vX.Y.Z-macos.zip
    ```
    The hash should match the first field in `CloudScope-vX.Y.Z-macos.zip.sha256`. -->

## Next steps

- [Using the GUI](gui.md)
- [Saved file formats](saved-files.md)
- [End-user recipes](recipes/index.md) — load sample data to confirm your install
