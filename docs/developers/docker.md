# Docker and web deployment

CloudScope can run as a browser application from a container.

```bash
docker compose up --build cloudscope
```

For server-side files, mount a data folder and load files from the mounted path inside the CloudScope UI.
