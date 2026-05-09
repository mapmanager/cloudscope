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

from cloudscope.events import (
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
