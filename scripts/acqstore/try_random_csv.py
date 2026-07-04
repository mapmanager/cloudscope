"""Exercise AcqImageList manifest CSV randomization.

Edit the constants at the top of this script to point at a local dataset. The
script intentionally has no CLI arguments so it remains a simple development
probe for the backend API.
"""

from __future__ import annotations

from pathlib import Path

from acqstore.acq_image.acq_image_list import AcqImageList, PathKind

LOAD_PATH = Path('/Users/cudmore/Sites/cloudscope-data/declan-data/manuscript_velocity_202606')
GROUPBY_COLUMN = 'grandparent'
N_PER_GROUP = 5
# RANDOM_SEED = 123
OUTPUT_DIR = Path('/tmp/cloudscope_random_csv')
# MANIFEST_CSV_PATH = OUTPUT_DIR / 'manifest.csv'
MASTER_CSV_PATH = OUTPUT_DIR / 'randomized_master.csv'
SAMPLED_CSV_PATH = OUTPUT_DIR / 'randomized_sampled.csv'


def main() -> None:
    """Load a folder, write randomized manifests, and reload the sample."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'Loading: {LOAD_PATH}')
    result = AcqImageList.load_safe(str(LOAD_PATH), kind=PathKind.FOLDER)
    image_list = result.acq_image_list
    print(f'Loaded {len(image_list)} file(s); warnings={len(result.warnings)}')
    for warning in result.warnings:
        print(f'WARNING: {warning.message}: {warning.path}')

    # image_list.to_manifest_csv(MANIFEST_CSV_PATH, root_path=LOAD_PATH)
    image_list.to_randomized_manifest_master_csv(
        MASTER_CSV_PATH,
        groupby_column=GROUPBY_COLUMN,
        # random_seed=RANDOM_SEED,
        root_path=LOAD_PATH,
    )
    image_list.to_randomized_manifest_csv(
        SAMPLED_CSV_PATH,
        groupby_column=GROUPBY_COLUMN,
        n_per_group=N_PER_GROUP,
        # random_seed=RANDOM_SEED,
        root_path=LOAD_PATH,
        allow_unbalanced=False,
    )
    # print(f'Wrote manifest: {MANIFEST_CSV_PATH}')
    print(f'Wrote randomized master: {MASTER_CSV_PATH}')
    print(f'Wrote randomized sample: {SAMPLED_CSV_PATH}')

    reload_result = AcqImageList.load_safe(
        str(SAMPLED_CSV_PATH),
        kind=PathKind.CSV,
        root_path=LOAD_PATH,
    )
    print(
        f'Reloaded sampled manifest: {len(reload_result.acq_image_list)} file(s); '
        f'warnings={len(reload_result.warnings)}'
    )


if __name__ == '__main__':
    main()
