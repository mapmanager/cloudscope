# AcqStore Server

AcqStore Server exposes the Python **AcqStore** API over local HTTP. It uses AcqStore, including `AcqImage`, to open scientific image acquisitions and serve image planes, reference images, calibrated coordinates, and metadata to thin HTTP clients.

The maintained generic browser client is [`src/acqstore_server/static/demo/v2/index.html`](../../src/acqstore_server/static/demo/v2/index.html), served at `/demo/v2/`.

## Start here

- **New JavaScript client developers:** [API v2 JavaScript client guide](v2/javascript-client.md)
- **API v2 overview:** [v2/README.md](v2/README.md)
- **Existing v1 integrations:** [v1/README.md](v1/README.md)
- **Interactive API documentation:** `http://127.0.0.1:8767/docs` while the server is running

## A running server is required

A browser or JavaScript client does not open microscope formats itself. It connects to a running AcqStore Server, which uses AcqStore to open the acquisition and expose the resulting data over HTTP.

### JavaScript developers and end users

External JavaScript developers and end users are not expected to clone CloudScope or manage Python. They normally run the packaged **AcqStore Server.app** supplied by the AcqStore Server developers. The app starts the local server and provides a small status window.

The packaged macOS app is currently available on request from Robert Cudmore at `robert.cudmore@gmail.com`.

After the app is running, begin with:

```text
http://127.0.0.1:8767/demo/v2/
http://127.0.0.1:8767/api/v2
http://127.0.0.1:8767/docs
```

### Python developers

From the CloudScope repository:

```bash
uv run python -m acqstore_server
```

Optional native status window:

```bash
ACQSTORE_SERVER_NATIVE=1 uv run python -m acqstore_server
```

## Building the packaged macOS app

This section is for Python and release developers, not thin-client authors.

Local build entry point:

```bash
./packaging/acqstore_server/build_app.sh
```

The signed and notarized CI build is defined by:

```text
.github/workflows/build-acqstore-server-macos.yml
```

Supporting release scripts live under:

```text
packaging/acqstore_server/
```

## Version policy

- **API v2** is the active development target.
- **API v1** remains intact for existing clients.
- The generic v2 demo is the maintained reference client for new integrations.
- External application-specific clients are outside the AcqStore Server source and v2 documentation boundary.
