# JavaScript client

Open a server-accessible path:

```javascript
const response = await fetch('/api/v2/open', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    path: '/absolute/path/to/acquisition.oir',
    channelIndices: [0, 1],
  }),
});
const opened = await response.json();
if (!response.ok || opened.ok === false) {
  throw new Error(`${opened.error}: ${opened.message}`);
}
```

Download one channel:

```javascript
const channel = opened.channels[0];
const binaryResponse = await fetch(channel.dataUrl, {cache: 'no-store'});
const buffer = await binaryResponse.arrayBuffer();
if (buffer.byteLength !== channel.byteLength) {
  throw new Error('binary byteLength mismatch');
}
const values = new Float32Array(buffer);
const [rows, columns] = opened.plane.shape;
if (values.length !== rows * columns) {
  throw new Error('binary sample count mismatch');
}
```

The bytes are row-major little-endian float32. JavaScript typed arrays use the
platform byte order; supported browser platforms are little-endian in practice.
For an explicit portable decoder, use `DataView.getFloat32(offset, true)`.

See the maintained complete example at `/demo/v2/`.
