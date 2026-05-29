# AcqStore Sample Data

AcqStore owns reusable sample-data download helpers so scripts and CloudScope can
load the same datasets without GUI-specific code.

## Runtime contract

```python
from acqstore.acq_image.acq_image_list import AcqImageList
from acqstore.sample_data import ensure_sample

folder = ensure_sample("demo-small")
acq_list = AcqImageList(str(folder), path_kind="folder")
```

`ensure_sample()` returns a local directory that has the same structure as a
normal user-selected acquisition folder. CloudScope should pass that path through
its existing folder-load path.

## Default storage location

Sample data is stored under:

```text
platformdirs.user_data_dir("cloudscope") / "sample-data"
```

On macOS this is usually:

```text
~/Library/Application Support/cloudscope/sample-data
```

Deployments can override this with:

```bash
export CLOUDSCOPE_SAMPLE_DATA_DIR=/data/sample-data
```

For Docker/cloud deployments, mount that directory to persistent storage so the
sample archive is not downloaded again whenever the container is recreated.

## Zip archive convention

Each release asset should be a zip file named with the sample name and version:

```text
demo-small-v1.zip
```

The zip should contain exactly one loadable top-level dataset folder:

```text
demo-small-v1.zip
  demo-small/
    cond1/
    cond2/
```

Create the archive from the parent directory with:

```bash
zip -r demo-small-v1.zip demo-small
```

The `SampleDataset.extracted_dir` field should match that top-level folder:

```python
SampleDataset(
    name="demo-small",
    version="v1",
    extracted_dir="demo-small",
    ...
)
```

## Docker Compose example

```yaml
services:
  cloudscope:
    environment:
      CLOUDSCOPE_SAMPLE_DATA_DIR: "/data/sample-data"
    volumes:
      - ./example-data:/data
```

Inside the container, `ensure_sample("demo-small")` returns a path similar to:

```text
/data/sample-data/demo-small-v1/demo-small
```

## Architecture notes

- `acqstore.sample_data` owns the registry, download, hash validation, zip
  extraction, and returned filesystem path.
- `acqstore.sample_data` must not import `cloudscope`, `nicegui`, or
  `nicewidgets`.
- `cloudscope` owns UI buttons, notifications, and progress.
- `AcqImageList` remains path-based and does not know whether a path came from a
  native picker, Docker mount, or downloaded sample data.
