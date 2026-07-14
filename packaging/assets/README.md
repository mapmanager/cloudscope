# Packaging assets

Shared desktop packaging icons for CloudScope.

| File | Role |
|------|------|
| `CloudScope.png` | Master artwork (1024×1024, black **CS** on white) |
| `CloudScope.icns` | macOS `.app` icon (`nicegui-pack --icon`) |
| `CloudScope.ico` | Windows exe icon (`nicegui-pack --icon`) |
| `build_icons.sh` | Regenerates `.icns` / `.ico` from the master PNG |

Normal builds use the committed `.icns` / `.ico` files. Re-run
`./packaging/assets/build_icons.sh` only after changing `CloudScope.png`.
