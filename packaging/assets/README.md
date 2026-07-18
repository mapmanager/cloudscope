# Packaging assets

Shared desktop packaging icons for CloudScope and AcqStore Server.

| File | Role |
|------|------|
| `CloudScope.png` | Master artwork (1024×1024, black **CS** on white) |
| `CloudScope.icns` | CloudScope macOS `.app` icon |
| `CloudScope.ico` | CloudScope Windows exe icon |
| `AcqStoreServer.png` | Master artwork (1024×1024, teal **AS** on white) |
| `AcqStoreServer.icns` | AcqStore Server macOS `.app` icon |
| `AcqStoreServer.ico` | AcqStore Server Windows exe icon (future) |
| `build_icons.sh` | Regenerates `.icns` / `.ico` from master PNGs |

Normal builds use the committed `.icns` / `.ico` files. Re-run
`./packaging/assets/build_icons.sh` only after changing a master PNG.

```bash
./packaging/assets/build_icons.sh                 # both
./packaging/assets/build_icons.sh AcqStoreServer  # one app
```
