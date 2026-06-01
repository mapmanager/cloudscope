"""Tests for CloudScope image-toolbar view helpers."""

from __future__ import annotations

from cloudscope.views.image_toolbar_view import (
    channel_options_for_acq_image,
    roi_options_for_acq_image,
)


class FakeImages:
    """Fake image helper exposing channel indices."""

    @property
    def channel_indices(self) -> list[int]:
        """Return fake channel indices."""
        return [0, 1, 2]


class FakeRois:
    """Fake ROI helper exposing integer ROI identifiers."""

    def get_roi_ids(self) -> list[int]:
        """Return fake ROI identifiers."""
        return [10, 20]


class FakeAcqImage:
    """Fake acquisition image for toolbar helper tests."""

    @property
    def images(self) -> FakeImages:
        """Return fake image helper."""
        return FakeImages()

    @property
    def rois(self) -> FakeRois:
        """Return fake ROI helper."""
        return FakeRois()


def test_channel_options_for_acq_image_returns_string_options() -> None:
    """Toolbar channel options should be strings expected by ImageToolbarWidget."""
    assert channel_options_for_acq_image(FakeAcqImage()) == ["0", "1", "2"]


def test_roi_options_for_acq_image_returns_int_options() -> None:
    """Toolbar ROI options should remain integer backend ROI ids."""
    assert roi_options_for_acq_image(FakeAcqImage()) == [10, 20]

from cloudscope.event_bus import EventBus
from cloudscope.views.base_view import BaseView
from cloudscope.views.image_toolbar_view import ImageToolbarView
from cloudscope.views.view_ids import ViewId


def test_image_toolbar_view_is_base_view() -> None:
    """ImageToolbarView should participate in BaseView lifecycle."""
    view = ImageToolbarView(event_bus=EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.IMAGE_TOOLBAR
    assert view.disable_when_busy is True

from cloudscope.events.roi import (
    AddRoiIntent,
    ApplyRoiFullHeightIntent,
    ApplyRoiFullWidthIntent,
    BeginEditRoiIntent,
    CancelEditRoiIntent,
    DeleteRoiIntent,
    RoiChanged,
    RoiChangeKind,
    SubmitEditRoiIntent,
)
from cloudscope.state import PrimarySelection
from nicewidgets.image_toolbar_widget.intent import (
    ImageToolbarRoiAddRequestIntent,
    ImageToolbarRoiApplyFullHeightIntent,
    ImageToolbarRoiApplyFullWidthIntent,
    ImageToolbarRoiDeleteRequestIntent,
    ImageToolbarRoiEditCancelIntent,
    ImageToolbarRoiEditStartIntent,
    ImageToolbarRoiEditSubmitIntent,
)


def test_image_toolbar_view_maps_roi_crud_intents() -> None:
    """Toolbar view should translate nicewidgets ROI CRUD intents to CloudScope intents."""
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id="file-a", channel=1, roi_id=2)
    added: list[AddRoiIntent] = []
    deleted: list[DeleteRoiIntent] = []
    edited: list[BeginEditRoiIntent] = []
    bus.subscribe(AddRoiIntent, added.append)
    bus.subscribe(DeleteRoiIntent, deleted.append)
    bus.subscribe(BeginEditRoiIntent, edited.append)

    view._on_toolbar_intent(ImageToolbarRoiAddRequestIntent())
    view._on_toolbar_intent(ImageToolbarRoiDeleteRequestIntent(roi_id=3))
    view._on_toolbar_intent(ImageToolbarRoiEditStartIntent(roi_id=4))

    assert added == [AddRoiIntent(selection=PrimarySelection(file_id="file-a", channel=1, roi_id=2))]
    assert deleted == [DeleteRoiIntent(selection=PrimarySelection(file_id="file-a", channel=1, roi_id=3))]
    assert edited == [BeginEditRoiIntent(selection=PrimarySelection(file_id="file-a", channel=1, roi_id=4))]


def test_image_toolbar_view_refreshes_on_roi_changed() -> None:
    """ROI model changes should resync toolbar options for the current file."""
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    calls = []
    view.current_selection = PrimarySelection(file_id="file-a", channel=0, roi_id=1)
    view._sync_toolbar_from_selection = lambda: calls.append("sync")  # type: ignore[method-assign]

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.ADD,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=2),
        )
    )
    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.ADD,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=2),
        )
    )

    assert calls == ["sync"]


def test_image_toolbar_view_maps_roi_edit_lifecycle_intents() -> None:
    """Toolbar view should translate nicewidgets ROI edit lifecycle intents."""
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id="file-a", channel=1, roi_id=2)
    cancelled: list[CancelEditRoiIntent] = []
    submitted: list[SubmitEditRoiIntent] = []
    full_width: list[ApplyRoiFullWidthIntent] = []
    full_height: list[ApplyRoiFullHeightIntent] = []
    bus.subscribe(CancelEditRoiIntent, cancelled.append)
    bus.subscribe(SubmitEditRoiIntent, submitted.append)
    bus.subscribe(ApplyRoiFullWidthIntent, full_width.append)
    bus.subscribe(ApplyRoiFullHeightIntent, full_height.append)

    view._on_toolbar_intent(ImageToolbarRoiEditCancelIntent(roi_id=3))
    view._on_toolbar_intent(ImageToolbarRoiEditSubmitIntent(roi_id=4))
    view._on_toolbar_intent(ImageToolbarRoiApplyFullWidthIntent(roi_id=5))
    view._on_toolbar_intent(ImageToolbarRoiApplyFullHeightIntent(roi_id=6))

    assert cancelled == [CancelEditRoiIntent(selection=PrimarySelection(file_id="file-a", channel=1, roi_id=3))]
    assert submitted == [SubmitEditRoiIntent(selection=PrimarySelection(file_id="file-a", channel=1, roi_id=4))]
    assert full_width == [ApplyRoiFullWidthIntent(selection=PrimarySelection(file_id="file-a", channel=1, roi_id=5))]
    assert full_height == [ApplyRoiFullHeightIntent(selection=PrimarySelection(file_id="file-a", channel=1, roi_id=6))]


import numpy as np
from acqstore.acq_image.image_contrast import ImageContrast
from cloudscope.events.contrast import ImageContrastChanged, UpdateImageContrastIntent
from cloudscope.events.raster import PrimaryPlaneLoaded
from nicewidgets.contrast_widget.intent import ContrastChangedIntent


class _ContrastSpy:
    """Stand-in for ``ContrastWidget`` that records ``*_ext`` calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def set_image_ext(self, image) -> None:
        self.calls.append(('set_image_ext', (image,), {}))

    def set_lut_ext(self, lut: str) -> None:
        self.calls.append(('set_lut_ext', (lut,), {}))

    def set_range_ext(self, *, value_min: int, value_max: int) -> None:
        self.calls.append(('set_range_ext', (), {'value_min': value_min, 'value_max': value_max}))

    def set_enabled_ext(self, enabled: bool) -> None:
        self.calls.append(('set_enabled_ext', (enabled,), {}))


def test_contrast_widget_intent_publishes_update_image_contrast_intent() -> None:
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id='f', channel=0)
    seen: list[UpdateImageContrastIntent] = []
    bus.subscribe(UpdateImageContrastIntent, seen.append)
    view._on_contrast_intent(
        ContrastChangedIntent(color_lut='Plasma', value_min=5, value_max=240)
    )
    assert seen == [
        UpdateImageContrastIntent(
            file_id='f', channel=0, color_lut='Plasma', value_min=5, value_max=240
        )
    ]


def test_contrast_widget_intent_dropped_without_selection() -> None:
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    seen: list[UpdateImageContrastIntent] = []
    bus.subscribe(UpdateImageContrastIntent, seen.append)
    view._on_contrast_intent(
        ContrastChangedIntent(color_lut='Plasma', value_min=5, value_max=240)
    )
    assert seen == []


class _AcqStub:
    def __init__(self) -> None:
        self.ensure_calls: list[dict] = []
        self._contrast = ImageContrast(
            color_lut='Green', value_min=10, value_max=200, img_min=0, img_max=255
        )

    def ensure_image_contrast_from_plane(
        self, channel, plane, *, default_color_lut, percentile_low, percentile_high
    ):
        self.ensure_calls.append(
            {
                'channel': channel,
                'plane_shape': plane.shape,
                'default_color_lut': default_color_lut,
                'percentile_low': percentile_low,
                'percentile_high': percentile_high,
            }
        )
        return self._contrast


def test_on_plane_loaded_seeds_widget_and_calls_ensure_once() -> None:
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id='f', channel=0)
    acq = _AcqStub()
    view.current_acq_image = acq  # type: ignore[assignment]
    spy = _ContrastSpy()
    view._contrast = spy  # type: ignore[assignment]
    plane = np.array([[0, 100, 200, 255]], dtype=np.uint8)

    view._on_plane_loaded(PrimaryPlaneLoaded(file_id='f', channel=0, plane=plane))

    assert len(acq.ensure_calls) == 1
    assert acq.ensure_calls[0]['channel'] == 0
    assert acq.ensure_calls[0]['plane_shape'] == plane.shape
    names = [c[0] for c in spy.calls]
    assert names == ['set_image_ext', 'set_lut_ext', 'set_range_ext', 'set_enabled_ext']
    assert spy.calls[3] == ('set_enabled_ext', (True,), {})


def test_on_plane_loaded_ignored_for_non_matching_selection() -> None:
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id='f', channel=0)
    acq = _AcqStub()
    view.current_acq_image = acq  # type: ignore[assignment]
    spy = _ContrastSpy()
    view._contrast = spy  # type: ignore[assignment]

    view._on_plane_loaded(
        PrimaryPlaneLoaded(file_id='other', channel=0, plane=np.zeros((2, 2)))
    )
    assert acq.ensure_calls == []
    assert spy.calls == []


def test_on_image_contrast_changed_pushes_to_widget_without_emit() -> None:
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id='f', channel=0)
    spy = _ContrastSpy()
    view._contrast = spy  # type: ignore[assignment]

    view._on_image_contrast_changed(
        ImageContrastChanged(
            file_id='f',
            channel=0,
            contrast=ImageContrast(
                color_lut='Hot', value_min=20, value_max=180, img_min=0, img_max=255
            ),
        )
    )
    names = [c[0] for c in spy.calls]
    assert names == ['set_lut_ext', 'set_range_ext']
    assert spy.calls[1] == ('set_range_ext', (), {'value_min': 20, 'value_max': 180})


def test_selection_change_disables_contrast_until_plane_loaded() -> None:
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus)
    spy = _ContrastSpy()
    view._contrast = spy  # type: ignore[assignment]
    view._sync_toolbar_from_selection = lambda: None  # type: ignore[method-assign]

    view.current_selection = PrimarySelection(file_id='f', channel=0)
    view.on_primary_selection_changed()

    disables = [c for c in spy.calls if c[0] == 'set_enabled_ext']
    assert disables == [('set_enabled_ext', (False,), {})]


def test_compute_auto_contrast_uses_app_config_percentiles(tmp_path) -> None:
    from cloudscope.app_config import AppConfig

    cfg = AppConfig(path=tmp_path / 'cfg.json')
    cfg.set_contrast_auto_percentiles(0.0, 100.0)
    bus = EventBus()
    view = ImageToolbarView(event_bus=bus, app_config=cfg)
    plane = np.array([[0, 100, 200, 255]], dtype=np.uint8)
    assert view._compute_auto_contrast(plane) == (0, 255)
