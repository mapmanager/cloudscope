"""Tests for primary image grid mapping and plane payload selection."""

from __future__ import annotations

import numpy as np
import pytest

from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader

from cloudscope.views.primary_image_view import (
    _load_plane_payload,
    _placeholder_plane,
    raster_grid_spec_from_image_header,
)


def _minimal_header(
    *,
    dims: tuple[str, ...],
    shape: tuple[int, ...],
    sizes: dict[str, int],
    physical_units: tuple[float | None, ...],
    physical_units_labels: tuple[str, ...] = (),
) -> ImageHeader:
    labels = physical_units_labels if physical_units_labels else tuple('' for _ in physical_units)
    return ImageHeader(
        path='/tmp/test.oir',
        shape=shape,
        dims=dims,
        sizes=sizes,
        dtype=np.dtype('uint16'),
        num_channels=1,
        num_scenes=1,
        physical_units=physical_units,
        physical_units_labels=labels,
    )


def test_raster_grid_spec_from_image_header_maps_yx_steps_and_labels() -> None:
    h = _minimal_header(
        dims=('Y', 'X'),
        shape=(100, 200),
        sizes={'Y': 100, 'X': 200},
        physical_units=(0.4, 0.25),
        physical_units_labels=('space Y', 'space X'),
    )
    g = raster_grid_spec_from_image_header(h)
    assert g.dx == 0.4
    assert g.dy == 0.25
    assert g.x_unit == 'space Y'
    assert g.y_unit == 'space X'


def test_raster_grid_spec_raises_when_y_missing() -> None:
    h = _minimal_header(
        dims=('Z', 'X'),
        shape=(5, 10),
        sizes={'Z': 5, 'X': 10},
        physical_units=(1.0, 1.0),
    )
    with pytest.raises(ValueError, match='Y and X'):
        raster_grid_spec_from_image_header(h)


def test_raster_grid_spec_raises_on_nan_calibration() -> None:
    h = _minimal_header(
        dims=('Y', 'X'),
        shape=(10, 20),
        sizes={'Y': 10, 'X': 20},
        physical_units=(float('nan'), 1.0),
    )
    with pytest.raises(ValueError, match='calibration'):
        raster_grid_spec_from_image_header(h)


def test_load_plane_payload_placeholder_without_acq() -> None:
    plane, grid, is_placeholder = _load_plane_payload('/x', None, 0)
    assert plane.shape == (2, 2)
    assert grid.dx == 1.0 and grid.dy == 1.0
    assert is_placeholder is True


def test_placeholder_plane_returns_float32() -> None:
    plane, _ = _placeholder_plane()
    assert plane.dtype == np.float32

import asyncio

from acqstore.acq_image.image_contrast import ImageContrast
from cloudscope.event_bus import EventBus
from cloudscope.events.contrast import ImageContrastChanged
from cloudscope.events.raster import PrimaryPlaneLoaded
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.primary_image_view import PrimaryImageView
from cloudscope.views.view_ids import ViewId


def test_primary_image_view_is_base_view_and_not_disabled_when_busy() -> None:
    """PrimaryImageView should be display-only for app busy handling."""
    view = PrimaryImageView(EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.PRIMARY_IMAGE
    assert view.disable_when_busy is False


class _FakeViewer:
    """Tracks viewer calls for contrast tests.

    Surfaces ``colorscale_calls`` / ``contrast_calls`` views as a convenience
    so legacy assertions continue to read naturally even though the production
    code now uses the combined :meth:`set_heatmap_style` API. Each entry of
    ``style_calls`` is ``(colorscale, zmin, zmax)``.
    """

    def __init__(self) -> None:
        self.style_calls: list[tuple[object, float, float]] = []
        self.colorscale_calls: list[object] = []
        self.contrast_calls: list[tuple[float, float]] = []

    async def set_heatmap_style(
        self, *, colorscale, zmin: float, zmax: float
    ) -> None:
        self.style_calls.append((colorscale, float(zmin), float(zmax)))
        self.colorscale_calls.append(colorscale)
        self.contrast_calls.append((float(zmin), float(zmax)))


class _FakeAcqImage:
    def __init__(self, contrast: ImageContrast | None) -> None:
        self._contrast = contrast

    def get_image_contrast(self, _channel: int) -> ImageContrast | None:
        return self._contrast


def test_apply_contrast_pushes_lut_and_window_to_viewer() -> None:
    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakeViewer()
    view._viewer = fake  # type: ignore[assignment]
    acq = _FakeAcqImage(
        ImageContrast(color_lut='Plasma', value_min=10, value_max=200, img_min=0, img_max=255)
    )
    asyncio.run(view._apply_contrast(acq, 0))
    assert fake.colorscale_calls == ['Plasma']
    assert fake.contrast_calls == [(10.0, 200.0)]


def test_apply_contrast_uses_single_combined_style_call() -> None:
    """LUT + window must reach the viewer through exactly one ``set_heatmap_style`` call.

    Two separate ``set_heatmap_colorscale`` + ``set_heatmap_contrast`` calls
    can race in the browser layer when both are awaited back-to-back; a single
    combined call keeps the heatmap restyle atomic.
    """
    view = PrimaryImageView(EventBus())
    fake = _FakeViewer()
    view._viewer = fake  # type: ignore[assignment]
    acq = _FakeAcqImage(
        ImageContrast(color_lut='Plasma', value_min=10, value_max=200, img_min=0, img_max=255)
    )
    asyncio.run(view._apply_contrast(acq, 0))
    assert fake.style_calls == [('Plasma', 10.0, 200.0)]


def test_apply_contrast_translates_named_channel_lut() -> None:
    """``Green`` is mapped through ``get_colorscale`` to Plotly's ``Greens``."""
    view = PrimaryImageView(EventBus())
    fake = _FakeViewer()
    view._viewer = fake  # type: ignore[assignment]
    acq = _FakeAcqImage(
        ImageContrast(color_lut='Green', value_min=5, value_max=240, img_min=0, img_max=255)
    )
    asyncio.run(view._apply_contrast(acq, 1))
    assert fake.colorscale_calls == ['Greens']


def test_apply_contrast_passes_inverted_grays_list_form() -> None:
    """``inverted_grays`` reaches the viewer as a 2-stop list, not ``'Greys'``."""
    view = PrimaryImageView(EventBus())
    fake = _FakeViewer()
    view._viewer = fake  # type: ignore[assignment]
    acq = _FakeAcqImage(
        ImageContrast(
            color_lut='inverted_grays', value_min=0, value_max=255, img_min=0, img_max=255
        )
    )
    asyncio.run(view._apply_contrast(acq, 0))
    assert len(fake.colorscale_calls) == 1
    scale = fake.colorscale_calls[0]
    assert isinstance(scale, list)
    assert scale == [[0, 'rgb(255,255,255)'], [1, 'rgb(0,0,0)']]


def test_apply_contrast_noop_without_contrast_entry() -> None:
    view = PrimaryImageView(EventBus())
    fake = _FakeViewer()
    view._viewer = fake  # type: ignore[assignment]
    asyncio.run(view._apply_contrast(_FakeAcqImage(None), 0))
    assert fake.colorscale_calls == []
    assert fake.contrast_calls == []


def test_on_image_contrast_changed_only_for_current_selection() -> None:
    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakeViewer()
    view._viewer = fake  # type: ignore[assignment]
    contrast = ImageContrast(
        color_lut='Plasma', value_min=10, value_max=200, img_min=0, img_max=255
    )
    acq = _FakeAcqImage(contrast)
    view.current_selection = PrimarySelection(file_id='f', channel=0)
    view.get_selected_acq_image = lambda: acq  # type: ignore[assignment]

    async def _run() -> None:
        view._on_image_contrast_changed(
            ImageContrastChanged(file_id='other', channel=0, contrast=contrast)
        )
        view._on_image_contrast_changed(
            ImageContrastChanged(file_id='f', channel=0, contrast=contrast)
        )
        # Yield enough times for the scheduled task to complete.
        for _ in range(5):
            await asyncio.sleep(0)

    asyncio.run(_run())
    assert fake.colorscale_calls == ['Plasma']
    assert fake.contrast_calls == [(10.0, 200.0)]


def test_publishes_primary_plane_loaded_after_set_data() -> None:
    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakeViewer()

    class _DataViewer(_FakeViewer):
        has_data = True

        async def set_data(self, *_a, **_k) -> None:
            return None

        async def set_data_from_pyramid(self, *_a, **_k) -> None:
            return None

    fake = _DataViewer()
    view._viewer = fake  # type: ignore[assignment]

    plane = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    grid = raster_grid_spec_from_image_header

    contrast = ImageContrast(
        color_lut='Gray', value_min=0, value_max=4, img_min=0, img_max=4
    )

    class _Acq:
        rois: list = []  # type: ignore[assignment]

        def get_image_contrast(self, _c: int):
            return contrast

    seen: list[PrimaryPlaneLoaded] = []
    bus.subscribe(PrimaryPlaneLoaded, seen.append)

    async def _run() -> None:
        from cloudscope.views import primary_image_view as pim

        original = pim._load_primary_display_payload
        from nicewidgets.raster_viewer.backend.image_model import (
            RasterGridSpec as RGS,
        )

        pim._load_primary_display_payload = (
            lambda *_a, **_k: (plane, RGS(dx=1.0, dy=1.0, x_unit='Y', y_unit='X'), None, False)
        )
        view._refresh_roi_overlays = lambda **_k: None  # type: ignore[assignment]
        view._refresh_diameter_trace_overlays = lambda **_k: None  # type: ignore[assignment]
        try:
            await view._refresh_raster_async('f', _Acq(), 0)
        finally:
            pim._load_primary_display_payload = original

    asyncio.run(_run())
    assert len(seen) == 1
    assert seen[0].file_id == 'f'
    assert seen[0].channel == 0
    assert seen[0].plane.flags.writeable is False


def test_does_not_publish_primary_plane_loaded_for_placeholder() -> None:
    bus = EventBus()
    view = PrimaryImageView(bus)

    class _Viewer:
        has_data = True

        async def set_data(self, *_a, **_k) -> None:
            return None

        async def set_heatmap_style(self, **_k) -> None:
            return None

    view._viewer = _Viewer()  # type: ignore[assignment]
    seen: list[PrimaryPlaneLoaded] = []
    bus.subscribe(PrimaryPlaneLoaded, seen.append)
    view._refresh_roi_overlays = lambda **_k: None  # type: ignore[assignment]
    view._refresh_diameter_trace_overlays = lambda **_k: None  # type: ignore[assignment]

    async def _run() -> None:
        await view._refresh_raster_async(None, None, None)

    asyncio.run(_run())
    assert seen == []
