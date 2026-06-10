# Sample data and cloudscope-data

Example datasets are maintained in the `cloudscope-data` repository:

<https://github.com/mapmanager/cloudscope-data>

The repository is used for documentation examples, GUI sample-data loading, and data-oriented testing. In the GUI, use the sample-data menu item to fetch and load the default sample dataset. In Python, use `acqstore.sample_data` to fetch the same data for scripts and notebooks.

```python
from acqstore.sample_data import ensure_sample

sample_folder = ensure_sample("demo-small")
print(sample_folder)
```
