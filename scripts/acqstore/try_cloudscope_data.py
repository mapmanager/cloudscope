"""Exercise the public AcqStore sample-data API.

This script demonstrates the intended sample-data workflow:

1. Fetch and list the datasets defined by ``cloudscope-data/catalog.json``.
2. Select one dataset by its stable catalog ID.
3. Retrieve its metadata with ``get_sample()``.
4. Download, verify, and install it with ``ensure_sample()``.
5. Open the installed dataset folder with ``AcqImageList``.

Change ``SAMPLE_ID`` below to exercise a different catalog dataset.
"""

from pprint import pprint

from acqstore.acq_image import AcqImageList
from acqstore.sample_data import ensure_sample, get_sample, list_samples
from acqstore.utils.logging import get_logger, setup_logging


logger = get_logger(__name__)
setup_logging()


# Stable dataset ID from cloudscope-data/catalog.json.
SAMPLE_ID = 'diameter-sample-data'


def print_catalog() -> None:
    """Print all available sample datasets in catalog display order."""
    samples = list_samples()

    print(f'=== available sample datasets: {len(samples)}')
    for index, sample in enumerate(samples):
        print(f'{index}: {sample.name}')
        print(f'  label: {sample.label}')
        print(f'  description: {sample.description}')
        print(f'  url: {sample.url}')
        print(f'  sha256: {sample.sha256}')


def print_sample_metadata(sample_id: str) -> None:
    """Print metadata for one selected sample dataset.

    Args:
        sample_id: Stable dataset ID from the sample-data catalog.
    """
    sample = get_sample(sample_id)

    print(f'\n=== selected sample: {sample_id}')
    pprint(
        {
            'name': sample.name,
            'label': sample.label,
            'description': sample.description,
            'url': sample.url,
            'sha256': sample.sha256,
            'cache_key': sample.cache_key,
            'archive_filename': sample.archive_filename,
        },
        indent=4,
        width=120,
        sort_dicts=False,
    )


def load_sample(sample_id: str) -> AcqImageList:
    """Download and open one sample dataset.

    Args:
        sample_id: Stable dataset ID from the sample-data catalog.

    Returns:
        Loaded acquisition-image collection.
    """
    print(f'\n=== ensuring sample: {sample_id}')
    sample_path = ensure_sample(sample_id)

    print(f'  installed sample path: {sample_path}')

    print('\n=== loading sample with AcqImageList')
    acq_image_list = AcqImageList(str(sample_path))

    print(f'  loaded acquisitions: {len(acq_image_list)}')
    return acq_image_list


def print_loaded_files(acq_image_list: AcqImageList) -> None:
    """Print a concise summary of each loaded acquisition.

    Args:
        acq_image_list: Loaded sample acquisition collection.
    """
    print('\n=== loaded acquisition files')

    for index, acq_image in enumerate(acq_image_list):
        print(f'{index}: {acq_image.name}')
        print(f'  file_id: {acq_image.file_id}')
        print(f'  path: {acq_image.path}')

        schema_row = acq_image.get_schema_row()
        pprint(
            schema_row,
            indent=4,
            width=120,
            sort_dicts=False,
        )


def run() -> None:
    """Exercise the complete public sample-data workflow."""
    print_catalog()
    print_sample_metadata(SAMPLE_ID)

    acq_image_list = load_sample(SAMPLE_ID)
    print_loaded_files(acq_image_list)


if __name__ == '__main__':
    run()