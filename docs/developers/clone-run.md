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

Sometimes need this (mkdocs hot reload is broken)

```bash
uv run mkdocs serve --livereload --dirtyreload
```

