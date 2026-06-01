"""Tests for :class:`ContrastController`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acqstore.acq_image.image_contrast import ImageContrast

from cloudscope.controllers.contrast_controller import ContrastController
from cloudscope.event_bus import EventBus
from cloudscope.events.contrast import ImageContrastChanged, UpdateImageContrastIntent


@dataclass
class FakeState:
    acq_image_list: Any | None


@dataclass
class FakeHomeController:
    state: FakeState


class FakeAcqImage:
    """Stand-in for AcqImage exposing the contrast surface used by the controller."""

    def __init__(self) -> None:
        self._contrasts: dict[int, ImageContrast] = {}
        self.slice_calls = 0

    # Loader instrumentation; controller MUST NOT touch this.
    def get_slice_data(self, *_a, **_k) -> None:
        self.slice_calls += 1
        raise AssertionError('ContrastController must not decode slices')

    def get_image_contrast(self, channel: int) -> ImageContrast | None:
        return self._contrasts.get(int(channel))

    def set_image_contrast(self, channel: int, contrast: ImageContrast) -> None:
        self._contrasts[int(channel)] = contrast


class FakeAcqImageList:
    def __init__(self, files: dict[str, FakeAcqImage]) -> None:
        self._files = files

    def get_file_by_id(self, file_id: str) -> FakeAcqImage | None:
        return self._files.get(file_id)


def _make_controller(
    *, acq_image_list: FakeAcqImageList | None
) -> tuple[ContrastController, EventBus]:
    bus = EventBus()
    home = FakeHomeController(state=FakeState(acq_image_list=acq_image_list))
    ctrl = ContrastController(event_bus=bus, home_controller=home)
    ctrl.bind()
    return ctrl, bus


def test_happy_path_publishes_image_contrast_changed() -> None:
    acq = FakeAcqImage()
    acq.set_image_contrast(
        0,
        ImageContrast(color_lut='Gray', value_min=0, value_max=255, img_min=0, img_max=255),
    )
    _, bus = _make_controller(acq_image_list=FakeAcqImageList({'f': acq}))
    seen: list[ImageContrastChanged] = []
    bus.subscribe(ImageContrastChanged, seen.append)

    bus.publish(
        UpdateImageContrastIntent(
            file_id='f', channel=0, color_lut='Plasma', value_min=10, value_max=200
        )
    )

    stored = acq.get_image_contrast(0)
    assert stored is not None
    assert (stored.color_lut, stored.value_min, stored.value_max) == ('Plasma', 10, 200)
    assert (stored.img_min, stored.img_max) == (0, 255)  # preserved from existing entry
    assert seen == [ImageContrastChanged(file_id='f', channel=0, contrast=stored)]
    assert acq.slice_calls == 0


def test_missing_acq_image_list_is_ignored() -> None:
    _, bus = _make_controller(acq_image_list=None)
    seen: list[ImageContrastChanged] = []
    bus.subscribe(ImageContrastChanged, seen.append)
    bus.publish(
        UpdateImageContrastIntent(
            file_id='f', channel=0, color_lut='Plasma', value_min=10, value_max=200
        )
    )
    assert seen == []


def test_unknown_file_id_is_ignored() -> None:
    _, bus = _make_controller(acq_image_list=FakeAcqImageList({}))
    seen: list[ImageContrastChanged] = []
    bus.subscribe(ImageContrastChanged, seen.append)
    bus.publish(
        UpdateImageContrastIntent(
            file_id='missing', channel=0, color_lut='Plasma', value_min=10, value_max=200
        )
    )
    assert seen == []


def test_missing_prior_contrast_does_not_crash_or_publish() -> None:
    """No prior ``ImageContrast`` -> drop the stale intent (no slice loading)."""
    acq = FakeAcqImage()
    _, bus = _make_controller(acq_image_list=FakeAcqImageList({'f': acq}))
    seen: list[ImageContrastChanged] = []
    bus.subscribe(ImageContrastChanged, seen.append)
    bus.publish(
        UpdateImageContrastIntent(
            file_id='f', channel=0, color_lut='Plasma', value_min=10, value_max=200
        )
    )
    assert seen == []
    assert acq.get_image_contrast(0) is None
    assert acq.slice_calls == 0


def test_controller_does_not_touch_loader() -> None:
    """Contract: contrast controller MUST NOT invoke any slice-loading method."""
    acq = FakeAcqImage()
    acq.set_image_contrast(
        1,
        ImageContrast(color_lut='Gray', value_min=0, value_max=255, img_min=0, img_max=255),
    )
    _, bus = _make_controller(acq_image_list=FakeAcqImageList({'f': acq}))
    bus.publish(
        UpdateImageContrastIntent(
            file_id='f', channel=1, color_lut='Hot', value_min=5, value_max=240
        )
    )
    assert acq.slice_calls == 0
