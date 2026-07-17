# AcqStore Server

AcqStore Server is a local HTTP service that exposes the Python **AcqStore** API to thin clients. It uses AcqStore, including `AcqImage`, to open scientific image acquisitions and serve image planes, reference images, coordinates, and metadata as JSON and binary HTTP resources.

The maintained generic browser client is API v2 at:

```text
http://127.0.0.1:8767/demo/v2/
```

Its source is:

```text
src/acqstore_server/static/demo/v2/index.html
```

## Two ways to run it

### Python development installation

For developers working from a CloudScope checkout:

```bash
uv run python -m acqstore_server
```

Then open:

```text
http://127.0.0.1:8767/demo/v2/
```

Optional native NiceGUI status window:

```bash
ACQSTORE_SERVER_NATIVE=1 uv run python -m acqstore_server
```

This mode requires the repository's Python environment and is intended for AcqStore Server development, testing, and debugging.

### Packaged desktop application

External HTML/JavaScript client developers and end users are not expected to clone CloudScope or manage Python. They run the packaged **AcqStore Server.app**, which starts the same local HTTP API and provides a small NiceGUI status window.

The packaged application is built by:

```text
.github/workflows/build-acqstore-server-macos.yml
```

and the scripts under:

```text
packaging/acqstore_server/
```

The thin client still requires a running AcqStore Server; the packaged app supplies that server without requiring the client user to install or operate Python directly.

## Why a thin client uses it

A browser or other thin client can use AcqStore's acquisition loading without implementing microscope file readers or importing Python libraries itself. The client sends HTTP requests to a running AcqStore Server, receives acquisition metadata as JSON, and downloads selected planes as binary float32 data.

## Primary v2 resources

| Resource | Purpose |
|---|---|
| [`v2/README.md`](v2/README.md) | API v2 overview and design boundary |
| [`v2/api.md`](v2/api.md) | Endpoint contract |
| [`v2/demo.md`](v2/demo.md) | Maintained generic JavaScript demo |
| [`v2/javascript-client.md`](v2/javascript-client.md) | JavaScript client guidance |
| [`v2/python-client.md`](v2/python-client.md) | Python HTTP client guidance |
| [`v2/testing.md`](v2/testing.md) | Server-versus-AcqStore testing boundary |
| [`entry_point_and_packaging.md`](entry_point_and_packaging.md) | Entry-point and packaging details |

Live discovery while the server is running:

```text
http://127.0.0.1:8767/api/v2
http://127.0.0.1:8767/docs
http://127.0.0.1:8767/openapi.json
```

## Scope

Active v2 development is limited to:

```text
src/acqstore_server/
tests/acqstore_server/
docs-dev/acqstore_server/
src/acqstore_server/static/demo/v2/
```

API v1 and `/demo/` remain frozen compatibility surfaces. Historical v1 documentation may describe earlier application-specific clients; those clients are external to the API v2 implementation and do not define the v2 contract.

## Stop the server

In terminal mode, press **Ctrl+C**. In native mode, quit the status window.

If port `8767` is already occupied on macOS:

```bash
lsof -nP -iTCP:8767 -sTCP:LISTEN
kill $(lsof -nP -iTCP:8767 -sTCP:LISTEN -t)
```
