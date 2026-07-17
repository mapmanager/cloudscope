# Client Roadmap

This document is the only onboarding guide for a new JavaScript client.

**Goal:** Load an acquisition and display one image plane using the AcqStore Server v2 API.

## Step 1 — Start AcqStore Server

Run the packaged **AcqStore Server.app** or start the server from Python.

## Step 2 — Verify the server

Send:

```
GET /api/v2/health
```

Confirm the server reports that it is healthy.

## Step 3 — Discover capabilities

Send:

```
GET /api/v2/capabilities
```

Inspect the returned capabilities before opening an acquisition.

## Step 4 — Open an acquisition

Use either:

```
POST /api/v2/pick-and-open
```

or

```
POST /api/v2/open
```

The response returns a session identifier together with acquisition metadata and the acquisition header.

## Step 5 — Read the acquisition header

Use the header returned by the open request to understand the acquisition before requesting image data.

## Step 6 — Download one source image plane

Request a single source image plane for the session.

The returned binary is little-endian Float32.

Transpose the plane before displaying it.

## Step 7 — Display the image

Render the transposed image with the graphics library of your choice.

## Step 8 — Close the session

When finished:

```
DELETE /api/v2/sessions/{sessionId}
```

## Finished

If you completed these steps, you have successfully integrated with AcqStore Server.

Only after completing this workflow should you consult the documents under `reference/` for additional implementation details.
