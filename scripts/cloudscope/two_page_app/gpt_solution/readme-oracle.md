# Oracle deployment recipe for the multi-window demo

This recipe runs the demo beside the existing CloudScope deployment on the same Oracle VM.

The important idea is:

```text
CloudScope app:       host 8080 -> container 8080
Multi-window demo:    host 8081 -> container 8080
```

The demo uses one NiceGUI server. The pool view is `/pool`, not a second port:

```text
http://<host>:8081/
http://<host>:8081/pool
```

## Phase 1 — commit and pull source

On macOS:

```bash
git status
git add scripts/cloudscope/two_page_app/gpt_solution
git commit -m "Add multi-window NiceGUI demo"
git push
```

On Oracle:

```bash
cd ~/cloudscope
git pull
```

## Phase 2 — run the demo container

On Oracle:

```bash
cd ~/cloudscope/scripts/cloudscope/two_page_app/gpt_solution
docker compose up --build -d
```

Check containers:

```bash
docker ps
```

Expected port mapping for the demo:

```text
0.0.0.0:8081->8080/tcp
```

Test from the Oracle VM itself:

```bash
curl http://127.0.0.1:8081
```

If this fails, stop and fix Docker before changing Cloudflare.

Useful commands:

```bash
docker compose logs -f
docker compose down
docker compose up --build -d
```

## Phase 3 — Cloudflare Tunnel / cloudflared

If CloudScope is already using `cloudflared`, you usually do **not** need to open Oracle port 8081 to the public internet. Cloudflare Tunnel reaches the local service from inside the VM.

Your existing `~/.cloudflared/config.yml` may look like:

```yaml
tunnel: <UUID>
credentials-file: /home/ubuntu/.cloudflared/<UUID>.json

ingress:
  - hostname: cloudscope.mapmanager.net
    service: http://localhost:8080
  - service: http_status:404
```

Add a second hostname for the demo:

```yaml
tunnel: <UUID>
credentials-file: /home/ubuntu/.cloudflared/<UUID>.json

ingress:
  - hostname: cloudscope.mapmanager.net
    service: http://localhost:8080

  - hostname: cloudscope-demo.mapmanager.net
    service: http://localhost:8081

  - service: http_status:404
```

Restart cloudflared:

```bash
sudo systemctl restart cloudflared
sudo systemctl status cloudflared --no-pager
```

Then test:

```text
https://cloudscope-demo.mapmanager.net
```

## Phase 4 — Cloudflare portal / DNS

You may need to add `cloudscope-demo.mapmanager.net` in Cloudflare. The exact step depends on how the original hostname was created.

### If using Cloudflare Zero Trust web UI

Go to:

```text
Cloudflare Dashboard
  -> Zero Trust
  -> Networks
  -> Tunnels
  -> your existing tunnel
  -> Public Hostnames
  -> Add a public hostname
```

Use:

```text
Subdomain: cloudscope-demo
Domain: mapmanager.net
Service type: HTTP
URL: localhost:8081
```

### If using CLI-managed tunnel DNS

You can route DNS with a command similar to:

```bash
cloudflared tunnel route dns <tunnel-name-or-uuid> cloudscope-demo.mapmanager.net
```

Then keep the local `~/.cloudflared/config.yml` ingress rule pointing that hostname to `http://localhost:8081`.

## Oracle firewall / security list

If you access the demo only through Cloudflare Tunnel, you usually do **not** need to open inbound port 8081 in Oracle.

Only open Oracle port 8081 if you want direct public access such as:

```text
http://<oracle-public-ip>:8081
```

For tunnel-based access, leave Oracle firewall closed and use:

```text
https://cloudscope-demo.mapmanager.net
```

## Stop the demo

```bash
cd ~/cloudscope/scripts/cloudscope/two_page_app/gpt_solution
docker compose down
```
