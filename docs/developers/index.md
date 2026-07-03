# Developer Guide

CloudScope is developed as a single codebase that supports desktop, browser, scripting, and notebook workflows while sharing the same `acqstore` backend.

The repository is organized into three primary packages:

```text
src/acqstore/
src/nicewidgets/
src/cloudscope/
```

The guiding design principle is scientific reproducibility. The same analysis code used by the desktop application is used by the web application and can also be called directly from Python scripts and Jupyter notebooks.

## Architecture goals

CloudScope was designed around several goals:

- one shared backend (`acqstore`)
- multiple user interfaces
- reproducible analysis
- testable code
- versioned releases
- long-term maintainability

The `acqstore` package owns image loading, metadata, ROIs, and analysis. The desktop application, browser application, notebooks, and scripts call into the same `acqstore` code.

The GUI uses an event-driven MVC architecture so user interactions can update related views consistently. Long-running analysis tasks are routed through controlled task execution, while image pyramids keep visualization responsive without changing the full-resolution data used for analysis.

Velocity, diameter, and sum intensity analysis can use parallel execution where available, and those performance paths are available from the GUI and scripted workflows because they are implemented in the shared backend.

## Repository organization

```text
src/acqstore/
    Scientific data model, file loading, ROIs, metadata, analysis, and saved results.

src/nicewidgets/
    Reusable NiceGUI widgets that are not specific to CloudScope.

src/cloudscope/
    Application controllers, views, dialogs, user workflows, and deployment entry points.

tests/
    Unit tests.

docs/
    MkDocs documentation.

.github/workflows/
    CI/CD workflows.
```

## Getting started

Clone the repository:

```bash
git clone https://github.com/mapmanager/cloudscope.git
cd cloudscope
```

Install dependencies:

```bash
uv sync
```

Run the application:

```bash
uv run python src/cloudscope/app.py
```

Run the test suite:

```bash
uv run pytest
```

Run the documentation locally:

```bash
uv sync --group docs
uv run mkdocs serve
```

## Unit testing

CloudScope uses pytest for unit testing. Tests are stored under:

```text
tests/acqstore/
tests/cloudscope/
tests/nicewidgets/
```

Unit tests must live only under the top-level `tests/` tree — never under `src/`.

Run all tests:

```bash
uv run pytest
```

Run a specific file:

```bash
uv run pytest tests/acqstore/test_acq_image.py
```

New features should include accompanying unit tests whenever practical.

## GitHub workflows

CloudScope uses GitHub Actions for continuous integration and release automation.

Current workflows include:

| Workflow | Purpose |
|---|---|
| `tests.yml` | Run unit tests. |
| `docs.yml` | Build and publish MkDocs documentation to GitHub Pages. |
| `release.yml` | Create reproducible tagged releases. |
| `build-macos.yml` | Build the macOS desktop application. |
| `build-windows.yml` | Build the Windows desktop application. |

Official releases are created from git tags. A tagged release archives the source code, documentation, desktop artifacts, and version metadata needed to reproduce analyses with a specific CloudScope version.

## Docker

CloudScope can run as a containerized browser application.

Repository files:

- [Dockerfile](https://github.com/mapmanager/cloudscope/blob/main/Dockerfile){target="_blank" rel="noopener"}
- [docker-compose.yml](https://github.com/mapmanager/cloudscope/blob/main/docker-compose.yml){target="_blank" rel="noopener"}

The Docker Compose deployment is used to run CloudScope on an Oracle Cloud server. The public browser version is available at [cloudscope.mapmanager.net](https://cloudscope.mapmanager.net){target="_blank" rel="noopener"}.

The public deployment allows users to load sample data from the [cloudscope-data Repository](https://github.com/mapmanager/cloudscope-data){target="_blank" rel="noopener"} and upload supported image files such as `.oir`, `.czi`, and `.tif`.

## cloudscope-data

Sample data and testing data are maintained in the [cloudscope-data Repository](https://github.com/mapmanager/cloudscope-data){target="_blank" rel="noopener"}.

The repository contains:

- example datasets
- documentation data
- testing datasets

The CloudScope GUI can fetch sample data directly from this repository.

## AI-assisted development

CloudScope development makes use of modern large language models for planning, implementation support, code review, documentation generation, unit test design, and refactoring strategy.

Tools used during development include ChatGPT, Cursor, and Gemini. AI-generated suggestions are reviewed, tested, and checked against the project architecture before inclusion.

## More information

- [Architecture](architecture.md)
- [Release and Deployment](release-and-deployment.md)
- [Contributing](contributing.md)
