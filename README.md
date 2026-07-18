# CloudScope

[![Tests](https://github.com/mapmanager/cloudscope/actions/workflows/tests.yml/badge.svg)](https://github.com/mapmanager/cloudscope/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/mapmanager/cloudscope/branch/main/graph/badge.svg)](https://codecov.io/gh/mapmanager/cloudscope)
[![Docs](https://img.shields.io/badge/docs-mapmanager.github.io-blue)](https://mapmanager.github.io/cloudscope/)

CloudScope is a desktop and browser application for viewing, annotating, and analyzing
acquisition-backed microscopy files. The GUI, notebooks, and scripts share the same Python backend so analyses stay reproducible across interfaces.

## Try CloudScope

- **Web app:** <https://cloudscope.mapmanager.net>
- **Desktop app:** [Get the desktop app](https://mapmanager.github.io/cloudscope/users/install/)
  (request a build via the form, then follow the install steps)

## Documentation

Full guides live on the docs site (preferred over this README):

- [CloudScope documentation](https://mapmanager.github.io/cloudscope/)
- [End users](https://mapmanager.github.io/cloudscope/users/) — GUI, recipes, file formats, desktop install
- [Data scientists](https://mapmanager.github.io/cloudscope/scientists/) — algorithms, notebooks, scripting
- [Developers](https://mapmanager.github.io/cloudscope/developers/) — architecture, testing, builds, deploy

Quick links: [supported formats](https://mapmanager.github.io/cloudscope/users/supported-file-formats/),
[velocity](https://mapmanager.github.io/cloudscope/users/recipes/velocity-analysis/),
[diameter](https://mapmanager.github.io/cloudscope/users/recipes/diameter-analysis/),
[peak detection](https://mapmanager.github.io/cloudscope/users/recipes/sum-intensity-analysis/),
[pool plots](https://mapmanager.github.io/cloudscope/users/pool-plots/),
[blinded mode](https://mapmanager.github.io/cloudscope/users/blinded-mode/),
[sample data](https://github.com/mapmanager/cloudscope-data).

## Developer install

Requires [uv](https://docs.astral.sh/uv/). From the repository root:

```bash
git clone git@github.com:mapmanager/cloudscope.git
cd cloudscope
uv sync
./scripts/run app
```

Browser mode: `./scripts/run web`

Tests: `uv run pytest`

See the [developer documentation](https://mapmanager.github.io/cloudscope/developers/) for Docker,
environment variables, coverage, and release builds.
