# Clone and run locally

Clone the repository, install dependencies with `uv`, and run CloudScope from the source tree.

```bash
uv sync
uv run python src/cloudscope/app.py
```

Run the browser version locally:

```bash
CLOUDSCOPE_NATIVE=0 uv run python src/cloudscope/app.py
```

## Serve documentation locally

Install the documentation dependency group and start the MkDocs development server:

```bash
uv sync --group docs
uv run mkdocs serve
```

`mkdocs serve` normally watches documentation files and live-reloads the browser when files change. If edits do not appear, check that you are editing files under the active MkDocs `docs_dir`, refresh the browser once, and make sure the terminal running `mkdocs serve` has not reported a build error.
