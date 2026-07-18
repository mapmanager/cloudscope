# AcqStore Server — roadmap (living)

**Calcium HTML:** in-repo working fork lives under
`scripts/acqstore_server/clients/neuronal_calcium_linescan/`
(additive AcqStore load + reference overview). Upstream TIFF path stays.
External colleagues may still integrate via the API handouts alone.

**Our job:** stable localhost API + docs/demo + optional native status UI.

## Sequence (KISS)

| # | Item | Status |
|---|------|--------|
| 1 | Health + open-by-path + channel binaries | Done (038) |
| 2 | macOS pick-and-open | Done (039) |
| 3 | Reference image + scan path on open session | Done (040, 043) |
| 4 | Tiny demo HTML (`/demo/`) | Done (040, 046) |
| 5 | Logging (console + file + native UI buffer) | Done (040, 051) |
| 6 | Packaging `.app` + native status window | Done (041–044); **rebuild** after 048–051 |
| 7 | In-repo HTML: linescan load | Done (049) |
| 8 | In-repo HTML: reference overview | Done (050) |
| 9 | Docs / LLM handoff refresh | Done (052) |
| 10 | Native port-busy UX | Open (optional) |
| 11 | Windows pack / Dock “View Log” | Later / optional |

### Run modes

| Mode | Command |
|------|---------|
| API only (default CLI) | `uv run python -m acqstore_server` |
| Native status window | `uv run python -m acqstore_server.desktop` |
| Packaged macOS | `./packaging/acqstore_server/build_app.sh` → `AcqStore Server.app` |

Packaged Quit stops the server. CLI escape hatch: see README `kill $(lsof …8767…)`.

**Start here for agents:** [`llm_agent_guide_v0.md`](llm_agent_guide_v0.md).

## Confirmed product boundaries

- AcqStore Server is a **file open API** (+ optional status UI / demo).
- Analysis stays in the calcium HTML (or CloudScope), not in this server.
- Demo at `/demo/` is **ours** (contract smoke), not the 5k app.
- `/api/v1/` : add fields carefully; **do not** rename existing keys or restore deleted routes without an explicit ticket.
- **No** default NiceGUI GZip on native (048).

## API sticky?

Prefer not renaming fields once external HTML authors integrate. Adding fields is fine; deleting/renaming needs a ticket and handout update.

## Dock right-click “View Log”?

Not required for v1. Status UI has **Open log** + live log pane. Revisit only if needed.

## Dev run

```bash
uv run python -m acqstore_server
# http://127.0.0.1:8767/demo/
# http://127.0.0.1:8767/api/v1/health
# log: ~/Library/Logs/AcqStore Server/acqstore_server.log
```
