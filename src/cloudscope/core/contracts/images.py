"""Image-access contract for one acquisition file."""

from __future__ import annotations

from typing import Any, Protocol


class AcqImagesProtocol(Protocol):
    """Backend-facing image access surface for one acquisition file.

    This protocol is intentionally explicit. Callers must provide the channel to
    load. The protocol does not define hidden defaults for channel selection.
    """

    @property
    def num_channels(self) -> int:
        """Return the number of backend-native channels available."""

    @property
    def channel_indices(self) -> list[int]:
        """Return valid backend-native channel indices in display order."""

    @property
    def default_channel(self) -> int | None:
        """Return the explicitly defined default channel, if any.

        Returns:
            The backend-native channel index used for initial app selection, or
            ``None`` when no explicit default is defined.
        """

    def get_channel_image(self, channel: int) -> Any:
        """Return image data for one required channel.

        Args:
            channel: Backend-native channel index to load.

        Returns:
            Image payload for the requested channel. The exact concrete type is
            backend-defined.

        Raises:
            KeyError: If the requested channel is not available.
            ValueError: If the requested channel is invalid for the file.
        """

    def get_reference_image(self, channel: int | None = None) -> Any | None:
        """Return optional reference image data.

        Args:
            channel: Optional backend-native channel index when the backend ties
                reference imagery to a channel.

        Returns:
            Reference image payload, or ``None`` when this file has no reference
            image.
        """
