"""Phase 0 profiling for raster file/channel switching and pyramid cache."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from acqstore.acq_image.acq_image import AcqImage
from cloudscope.raster_display_cache import RasterDisplayCache
from cloudscope.views.primary_image_view import _load_primary_display_payload, raster_grid_spec_from_image_header
from nicewidgets.raster_viewer.backend.image_model import BackendImage
from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid

DEFAULT_PATHS = (
    '/Users/cudmore/Dropbox/data/sanpy-users/kym-users/czi-data/disjointedlinescansandframescans/Image 10.czi',
    '/Users/cudmore/Dropbox/data/sanpy-users/kym-users/czi-data/disjointedlinescansandframescans/Image 17.czi',
)


def _load_acq_image(path: str) -> AcqImage:
    image = AcqImage(path)
    image.images.load_image_data()
    return image


def _time_pyramid_build(plane: np.ndarray, grid) -> float:
    source = BackendImage(plane, grid=grid)
    started = time.perf_counter()
    ImagePyramid(source)
    return time.perf_counter() - started


def _profile_switch(paths: tuple[str, ...]) -> None:
    existing = [path for path in paths if Path(path).expanduser().exists()]
    if len(existing) < 2:
        print('Skipping profile: need at least two existing CZI paths.')
        for path in paths:
            print(f'  missing or unavailable: {path}')
        return

    images = [_load_acq_image(path) for path in existing[:2]]
    file_ids = ['image-10', 'image-17']
    channel = 0
    cache = RasterDisplayCache(max_entries=3)

    print('=== cold load (no cache) ===')
    for file_id, image in zip(file_ids, images, strict=True):
        plane = np.asarray(image.images.get_slice_data(channel))
        grid = raster_grid_spec_from_image_header(image.images.header)
        elapsed = _time_pyramid_build(plane, grid)
        print(f'{file_id}: shape={plane.shape} pyramid_build={elapsed * 1000:.2f} ms')

    print('=== alternating selection with cache ===')
    timings: list[tuple[str, str, float]] = []
    for repeat in range(3):
        for file_id, image in zip(file_ids, images, strict=True):
            started = time.perf_counter()
            _load_primary_display_payload(file_id, image, channel, cache)
            elapsed = time.perf_counter() - started
            timings.append((f'pass-{repeat + 1}', file_id, elapsed))
            print(f'pass {repeat + 1} {file_id}: cached_fetch={elapsed * 1000:.2f} ms')

    print(f'cache entries: {len(cache)} / max {cache.max_entries}')


if __name__ == '__main__':
    _profile_switch(DEFAULT_PATHS)
