# Clone and run locally

Clone the repository and install dependencies with `uv`.

```bash
git clone https://github.com/mapmanager/cloudscope.git
cd cloudscope
uv sync
```

Run the app locally in native desktop mode:

```bash
uv run python src/cloudscope/app.py
```

Run the app locally in browser mode:

```bash
CLOUDSCOPE_NATIVE=0 uv run python src/cloudscope/app.py
```
