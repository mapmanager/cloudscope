from typing import Any
from dataclasses import dataclass, fields
import math
import numpy as np
from typing import BinaryIO, Self

@dataclass(frozen=True)
class ImageHeader:
    """Header information for an imported image file.

    Attributes:
        path: Filesystem path when loading from disk, or the upload **filename**
            when loading from a binary stream (not necessarily on disk).
        shape: Raw array shape in file/native order.
        dims: Dimension labels in file/native order.
        sizes: Mapping from dimension label to number of elements.
        dtype: NumPy dtype of the pixel data.
        num_channels: Number of channels in the image.
        num_scenes: Number of scenes in the file (OIR uses ``1``).
        physical_units: Per-axis calibration steps or placeholders from the file.
        physical_units_labels: Human-readable labels aligned with ``physical_units``.
        date: Acquisition calendar date as ``YYYYMMDD``, or ``""`` if unknown.
        time: Acquisition time-of-day as ``HH:MM:SS`` (24-hour), or ``""`` if unknown.
    """

    path: str
    shape: tuple[int, ...]
    dims: tuple[str, ...]
    sizes: dict[str, int]
    dtype: np.dtype
    num_channels: int
    num_scenes: int
    physical_units: tuple[Any, ...]
    physical_units_labels: tuple[str, ...]
    date: str = ""
    time: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the header as a plain dictionary."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def as_json_dict(self) -> dict[str, Any]:
        """Return a dict suitable for :func:`json.dumps` (dtype as string, NaN/inf → None)."""
        d = self.as_dict()
        fixed_units: list[Any] = []
        for x in d["physical_units"]:
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                fixed_units.append(None)
            else:
                fixed_units.append(x)
        return {
            "path": d["path"],
            "shape": list(d["shape"]),
            "dims": list(d["dims"]),
            "sizes": dict(d["sizes"]),
            "dtype": str(d["dtype"]),
            "num_channels": d["num_channels"],
            # "num_scenes": d["num_scenes"],
            "physical_units": fixed_units,
            "physical_units_labels": list(d["physical_units_labels"]),
            "date": d["date"],
            "time": d["time"],
        }

    @staticmethod
    def default_physical_for_dims(
        dims: tuple[str, ...],
    ) -> tuple[tuple[float, ...], tuple[str, ...]]:
        """Default per-axis calibration when unknown (e.g. TIFF).

        Args:
            dims: Axis labels; one value per axis.

        Returns:
            ``physical_units`` all ``1.0`` and ``physical_units_labels`` all ``\"Pixels\"``.
        """
        n = len(dims)
        units = tuple(1.0 for _ in range(n))
        labels = tuple("Pixels" for _ in range(n))
        return units, labels

    def _physical_step_for_dim(self, dim: str) -> float | None:
        """Return a finite positive calibration step for ``dim``, or ``None`` if unknown."""
        if dim not in self.dims:
            return None
        i = self.dims.index(dim)
        if i >= len(self.physical_units):
            return None
        u = self.physical_units[i]
        if u is None:
            return None
        if isinstance(u, float) and (math.isnan(u) or math.isinf(u)):
            return None
        try:
            v = float(u)
        except (TypeError, ValueError):
            return None
        if v <= 0.0 or math.isnan(v) or math.isinf(v):
            return None
        return v

    def _physical_label_for_dim(self, dim: str) -> str:
        if dim not in self.dims:
            return dim
        i = self.dims.index(dim)
        if i < len(self.physical_units_labels):
            lab = self.physical_units_labels[i]
            if lab:
                return str(lab)
        return dim

@dataclass(frozen=True, eq=False)
class ReferenceImage:
    """Immutable snapshot of a microscopy reference/overview image (e.g. OIR linescan ref).

    ``array`` and every ndarray in ``coords`` are **read-only views** where possible;
    callers must not mutate them. ``eq=False`` avoids elementwise array equality on ``==``.
    """

    array: np.ndarray
    dims: tuple[str, ...]
    num_channels: int
    line_roi: tuple[float, float, float, float] | None
    coord_units: tuple[tuple[str, str], ...]
    coord_scales: tuple[tuple[str, float], ...]
    coords: tuple[tuple[str, np.ndarray], ...]

class BaseFileLoader:
    """Base class for lazy-loading image readers with a shared header and pixel API.
    """

    def __init__(self, path: str, header: ImageHeader | None = None) -> None:
        """Load metadata from disk unless a precomputed header is supplied.

        Args:
            path: Filesystem path to the image file.
            header: Optional pre-built header; if omitted, :meth:`read_header` is used.
        """
        self.path = path
        self._stream: BinaryIO | None = None
        self._post_init(header)

    @classmethod
    def from_stream(
        cls,
        stream: BinaryIO,
        filename: str,
        header: ImageHeader | None = None,
    ) -> Self:  # Use 'Self' for the return type (from typing)
        """Generic factory to create any loader from a stream."""
        inst = object.__new__(cls)
        inst.path = filename
        inst._stream = stream
        inst._post_init(header)    
        return inst

    def _post_init(self, header: ImageHeader | None) -> None:
        """Centralized state initialization for both __init__ and from_stream."""
        self._img_data = None
        self._referenceImage = None
        
        # Look up '_squeeze' on the class or instance; default to True
        self._squeeze = getattr(self, "_squeeze", True)
        
        # Ensure the header is always initialized
        if header is None:
            self._header = self.read_header()
        else:
            self._header = header
            
    @property
    def header(self) -> ImageHeader:
        """Header read at construction or injected."""
        return self._header

    @property
    def reference_image(self) -> ReferenceImage | None:
        """Return a reference image.
        """
        return self._referenceImage

    def read_header(self) -> ImageHeader:
        """Read header metadata for this loader's path.

        Returns:
            Parsed :class:`ImageHeader`.

        Raises:
            NotImplementedError: If the concrete subclass does not implement this.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement read_header()")

    @classmethod
    def read_header_from_path(cls, path: str) -> ImageHeader:
        """Read header from disk without keeping the loader instance.

        Args:
            path: Filesystem path to the image file.

        Returns:
            Parsed :class:`ImageHeader`.
        """
        return cls(path).header

    @classmethod
    def read_header_from_stream(cls, stream: BinaryIO, filename: str) -> ImageHeader:
        """Read header from a stream without retaining the loader instance."""
        return cls.from_stream(stream, filename).header

    def _load_full_image_array(self) -> np.ndarray:
        """Load the full pixel array for this loader's active scene(s).

        Returns:
            NumPy array in native dimension order.

        Raises:
            NotImplementedError: If the subclass does not implement loading.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _load_full_image_array()"
        )

    def load_image_data(self) -> np.ndarray:
        """Load and cache the full image array (lazy, idempotent).

        Returns:
            The full pixel array for this file/scene.
        """
        if self._img_data is None:
            self._img_data = self._load_full_image_array()
        return self._img_data

    def unload_image_data(self) -> None:
        """Drop cached primary pixel data; header unchanged."""
        self._img_data = None

    def unload_reference_data(self) -> None:
        """Drop reference-image caches."""
        self._referenceImage = None

    def unload_all_cached_data(self) -> None:
        """Clear primary pixels, and reference caches."""
        self.unload_image_data()
        self.unload_reference_data()

    @staticmethod
    def yx_slice_from_volume(
        arr: np.ndarray,
        dims: tuple[str, ...],
        num_channels: int,
        channel: int,
        *,
        z: int = 0,
        t: int = 0,
    ) -> np.ndarray:
        """Select ``T`` / ``Z`` / ``C`` and return a 2D ``(Y, X)`` view or copy of ``arr``."""
        if channel < 0 or channel >= num_channels:
            raise IndexError(
                f"Channel index {channel} out of range for {num_channels} channels"
            )
        dims_list = list(dims)
        if "Y" not in dims_list or "X" not in dims_list:
            raise ValueError(f"Expected dims to include Y and X; got dims={dims}")
        if "C" not in dims_list:
            if num_channels != 1:
                raise ValueError(
                    f"No C axis in dims but num_channels={num_channels}"
                )
            if channel != 0:
                raise IndexError(f"No C axis; only channel 0 is valid, got {channel}")

        arr_work = arr

        def _take_and_drop(dim_label: str, index: int) -> None:
            nonlocal arr_work, dims_list
            if dim_label not in dims_list:
                return
            axis = dims_list.index(dim_label)
            size = arr_work.shape[axis]
            if index < 0 or index >= size:
                raise IndexError(
                    f"{dim_label} index {index} out of range for size {size} (dims={tuple(dims_list)})"
                )
            arr_work = np.take(arr_work, indices=index, axis=axis)
            dims_list.pop(axis)

        _take_and_drop("T", t)
        _take_and_drop("Z", z)
        if "C" in dims_list:
            _take_and_drop("C", channel)

        if tuple(dims_list) != ("Y", "X"):
            raise ValueError(
                f"After selecting T/Z/C, expected remaining dims (Y, X); got {tuple(dims_list)} "
                f"with shape {arr_work.shape}"
            )

        return arr_work

    def get_slice_data(self, channel: int, z: int = 0, t: int = 0) -> np.ndarray:
        """Return a single 2D ``(Y, X)`` slice after optional ``T``/``Z``/``C`` selection.

        Loads pixel data on first use.

        Args:
            channel: Channel index along ``C`` (or ``0`` when there is no ``C`` axis).
            z: Index along ``Z`` if present; ignored if ``Z`` is absent.
            t: Index along ``T`` if present; ignored if ``T`` is absent.

        Returns:
            Two-dimensional array with dimensions ``(Y, X)``.

        Raises:
            IndexError: If any index is out of range.
            ValueError: If dims cannot be reduced to ``(Y, X)``.
        """
        self.load_image_data()
        assert self._img_data is not None
        return self.yx_slice_from_volume(
            self._img_data,
            self._header.dims,
            self._header.num_channels,
            channel,
            z=z,
            t=t,
        )

    def get_channel_data(self, channel: int) -> np.ndarray:
        """Return the full array for one channel (``C`` axis removed).

        Loads pixel data on first use. Remaining dimensions stay in file order
        (e.g. ``T, Y, X`` or ``Z, Y, X``).

        Args:
            channel: Index along the ``C`` dimension, or ``0`` when there is no ``C`` axis.

        Returns:
            NumPy array without the channel axis.

        Raises:
            IndexError: If ``channel`` is invalid.
            ValueError: If the header implies multiple channels but there is no ``C`` dim.
        """
        self.load_image_data()
        if channel < 0 or channel >= self._header.num_channels:
            raise IndexError(
                f"Channel index {channel} out of range for {self._header.num_channels} channels"
            )

        if "C" not in self._header.dims:
            if self._header.num_channels != 1:
                raise ValueError(
                    f"No C axis in dims but num_channels={self._header.num_channels}"
                )
            if channel != 0:
                raise IndexError(f"No C axis; only channel 0 is valid, got {channel}")
            assert self._img_data is not None
            return self._img_data

        assert self._img_data is not None
        c_axis = self._header.dims.index("C")
        return np.take(self._img_data, indices=channel, axis=c_axis)

    # --- AcqImagesProtocol Implementation ---

    @property
    def num_channels(self) -> int:
        """Conforms to AcqImagesProtocol."""
        return self._header.num_channels

    @property
    def channel_indices(self) -> list[int]:
        """Conforms to AcqImagesProtocol."""
        return list(range(self.num_channels))

    @property
    def default_channel(self) -> int | None:
        """Conforms to AcqImagesProtocol. 
        Defaults to 0 if channels exist, otherwise None.
        """
        return 0 if self.num_channels > 0 else None

    def get_channel_image(self, channel: int) -> np.ndarray:
        """Conforms to AcqImagesProtocol using existing backend logic."""
        try:
            # Re-uses your existing, validated channel loader
            return self.get_channel_data(channel)
        except IndexError as e:
            raise KeyError(f"Channel {channel} not found") from e

    def get_reference_image(self, channel: int | None = None) -> np.ndarray | None:
        """Conforms to AcqImagesProtocol.
        Returns the pixel array of the ReferenceImage snapshot if it exists.
        """
        ref = self.reference_image
        if ref is None:
            return None
            
        # If your backend tie reference imagery to channels, you'd filter here.
        # Otherwise, return the main reference array.
        return ref.array