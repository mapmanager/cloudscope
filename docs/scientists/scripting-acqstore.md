# Scripting with acqstore

`acqstore` is the scriptable scientific backend used by CloudScope. Scripts should import `acqstore` directly rather than importing CloudScope GUI views.

A typical script loads sample data or a local file, creates an acquisition object, gets image data, runs analysis, and exports results.

```python
from acqstore.acq_image.acq_image import AcqImage

acq = AcqImage("/path/to/file.oir")
print(acq.name)
print(acq.images.header)
```

See the notebooks for executable examples.
