---
hide:
  - toc
---

# CloudScope

CloudScope is a desktop and browser application for viewing, annotating, and analyzing acquisition-backed microscopy files.

<div class="grid cards" markdown>

-   :material-web:{ .lg .middle } **Launch the web app**

    ---

    Try CloudScope in your browser before installing a desktop build.

    [:octicons-arrow-right-24: Open cloudscope.mapmanager.net](https://cloudscope.mapmanager.net){target="_blank" rel="noopener"}

-   :material-download:{ .lg .middle } **Download the desktop app**

    ---

    CloudScope desktop is the same application on macOS and Windows. Choose the build for your operating system from GitHub Releases.

    [:material-apple: macOS](https://github.com/mapmanager/cloudscope/releases){target="_blank" rel="noopener"} · [:material-microsoft-windows: Windows](https://github.com/mapmanager/cloudscope/releases){target="_blank" rel="noopener"}

</div>

![CloudScope architecture](assets/cloudscope-architecture.svg)

## One backend, multiple interfaces

The desktop application, browser application, and Python scripting workflows all use the same `acqstore` scientific backend. This design keeps scientific logic out of the GUI and supports reproducibility: GUI workflows and scripted workflows execute the same analysis code.

## Supported file formats

CloudScope supports commercial microscopy formats including Olympus / Evident `.oir` and Zeiss `.czi`, as well as open formats including TIFF `.tif` and OME-Zarr.

## Who is this documentation for?

- **End users** should start with installation, the browser app, quickstart recipes, and GUI reference pages.
- **Scientific users and data scientists** should start with reproducibility, algorithms, parameters, sample data, notebooks, and the `acqstore` scripting guide.
- **Developers** should start with architecture, performance, local development, testing, release builds, and API reference pages.
