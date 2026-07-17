# Testing boundary

AcqStore Server tests are organized around the behavior the server owns.

## Server-owned behavior

The main v2 test suite uses injected, transport-neutral `OpenedAcquisition`
results or a small fake of the public `AcqImage` surface. These tests cover:

- request validation and stable error envelopes;
- forwarding ordered channel selections;
- JSON serialization and URL construction;
- little-endian float32 binary transport;
- session creation, lookup, expiry, and deletion;
- reference-image HTTP behavior;
- OpenAPI and maintained-client contracts.

These tests should be deterministic and should not require proprietary sample
files.

## AcqStore adapter drift

A very small adapter smoke suite opens generated TIFF files through the real
public `AcqImage` API. Its purpose is only to detect drift in the interface used
by `acqstore_server.v2.open_service`.

It does not establish format-decoding correctness.

## AcqStore-owned behavior

Whether TIFF, OIR, CZI, ND2, or another format is decoded correctly belongs in
`tests/acqstore/`. Format-specific metadata interpretation, dimensional
inference, and representative microscope fixtures should not be duplicated in
the server suite.
