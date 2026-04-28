from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict, MISSING
from typing import Any, ClassVar
import itertools

import pandas as pd

from acqstore.schema import (
    FieldSchema,
    SchemaDefinition,
    ValueType,
    validate_patch_for_schema,
    validate_values_for_schema,
)
from acqstore.utils.logging import get_logger

logger = get_logger(__name__)


EXPERIMENT_METADATA_SCHEMA = SchemaDefinition(
    schema_id='experiment_metadata',
    version=1,
    fields=(
        FieldSchema(
            name='species',
            display_name='Species',
            value_type=ValueType.STR,
            description='Animal species (e.g., mouse, rat).',
            editable=True,
            group='Animal',
        ),
        FieldSchema(
            name='sex',
            display_name='Sex',
            value_type=ValueType.STR,
            description='Biological sex or experimental sex label.',
            editable=True,
            group='Animal',
        ),
        FieldSchema(
            name='genotype',
            display_name='Genotype',
            value_type=ValueType.STR,
            description='Genotype or strain label.',
            editable=True,
            group='Animal',
        ),
        FieldSchema(
            name='region',
            display_name='Region',
            value_type=ValueType.STR,
            description='Brain region or anatomical location.',
            editable=True,
            group='Sample',
        ),
        FieldSchema(
            name='cell_type',
            display_name='Cell type',
            value_type=ValueType.STR,
            description='Type of cell or vessel being imaged.',
            editable=True,
            group='Sample',
        ),
        FieldSchema(
            name='depth',
            display_name='Depth',
            value_type=ValueType.FLOAT,
            description='Imaging depth in micrometers.',
            editable=True,
            group='Sample',
        ),
        FieldSchema(
            name='branch_order',
            display_name='Branch order',
            value_type=ValueType.INT,
            description='Branch order for vascular structures.',
            editable=True,
            group='Sample',
        ),
        FieldSchema(
            name='direction',
            display_name='Direction',
            value_type=ValueType.STR,
            description='Flow direction or vessel orientation.',
            editable=True,
            group='Sample',
        ),
        FieldSchema(
            name='condition',
            display_name='Condition',
            value_type=ValueType.STR,
            description='Experimental condition or treatment.',
            editable=True,
            group='Experiment',
        ),
        FieldSchema(
            name='condition2',
            display_name='Condition 2',
            value_type=ValueType.STR,
            description='Second condition field.',
            editable=True,
            group='Experiment',
        ),
        FieldSchema(
            name='treatment',
            display_name='Treatment',
            value_type=ValueType.STR,
            description='Treatment applied.',
            editable=True,
            group='Experiment',
        ),
        FieldSchema(
            name='treatment2',
            display_name='Treatment 2',
            value_type=ValueType.STR,
            description='Second treatment field.',
            editable=True,
            group='Experiment',
        ),
        FieldSchema(
            name='date',
            display_name='Date',
            value_type=ValueType.STR,
            description='User-editable date (e.g., experiment date).',
            editable=True,
            group='Experiment',
        ),
        FieldSchema(
            name='note',
            display_name='Note',
            value_type=ValueType.STR,
            description='Free-form notes or comments.',
            editable=True,
            group='Notes',
        ),
    ),
)

@dataclass
class FieldMetadata:
    """Structured metadata for form field definitions.

    Provides type-safe field metadata to avoid typos in metadata dictionaries.
    Used by GUI forms to configure field visibility, editability, and layout.

    Attributes:
        editable: Whether the field can be edited by the user.
        label: Display label for the field.
        widget_type: Type of widget to use (e.g., "text", "number").
        grid_span: Number of grid columns this field spans.
        visible: Whether the field should be visible in forms.
        description: Human-readable description of the field for documentation.
    """

    editable: bool = True
    label: str = ""
    widget_type: str = "text"
    grid_span: int = 1
    visible: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for use in field(metadata=...).

        Returns:
            Dictionary containing all field metadata attributes
        """
        result = {
            "editable": self.editable,
            "label": self.label,
            "widget_type": self.widget_type,
            "grid_span": self.grid_span,
            "visible": self.visible,
            "description": self.description,
        }
        return result


def field_metadata(
    editable: bool = True,
    label: str = "",
    widget_type: str = "text",
    grid_span: int = 1,
    visible: bool = True,
    description: str = "",
) -> dict[str, Any]:
    """Create field metadata dictionary.

    Convenience function that creates a FieldMetadata instance and converts
    it to a dictionary suitable for use in dataclass field metadata.

    Args:
        editable: Whether the field can be edited by the user.
        label: Display label for the field.
        widget_type: Type of widget to use (e.g., "text", "number").
        grid_span: Number of grid columns this field spans.
        visible: Whether the field should be visible in forms.
        description: Human-readable description of the field for documentation.

    Returns:
        Dictionary containing field metadata attributes.
    """
    return FieldMetadata(
        editable=editable,
        label=label,
        widget_type=widget_type,
        grid_span=grid_span,
        visible=visible,
        description=description,
    ).to_dict()


def _generateDocs(dc: type, print_markdown: bool = True) -> pd.DataFrame:
    """Generate documentation DataFrame from a dataclass.

    Extracts field information from a dataclass including name, display name,
    default value, and description. Optionally prints a markdown table to console.

    Args:
        dc: The dataclass type to document.
        print_markdown: If True, print markdown table to console. Defaults to True.

    Returns:
        pandas DataFrame with columns: name, display_name, default_value, description.
    """
    rows = []
    for field_obj in fields(dc):
        # Get metadata
        meta = field_obj.metadata
        
        # Extract field information
        name = field_obj.name
        display_name = meta.get("label", "") or name
        description = meta.get("description", "")
        
        # Handle default value
        if field_obj.default is not MISSING:
            # Regular default value
            default_value = field_obj.default
        elif field_obj.default_factory is not MISSING:
            # default_factory case
            factory_name = getattr(field_obj.default_factory, '__name__', 'callable')
            default_value = f"<factory: {factory_name}>"
        else:
            # No default (required field)
            default_value = "<required>"
        
        # Convert default to string representation
        if default_value is None:
            default_str = "None"
        elif isinstance(default_value, str):
            default_str = f'"{default_value}"'
        else:
            default_str = str(default_value)
        
        rows.append({
            "name": name,
            "display_name": display_name,
            "default_value": default_str,
            "description": description,
        })
    
    df = pd.DataFrame(rows)
    
    if print_markdown:
        try:
            # Try using pandas to_markdown (requires tabulate)
            print(f"\n## {dc.__name__}\n")
            print(df.to_markdown(index=False))
            print()
        except (ImportError) as e:
            # Fallback if tabulate is not available
            # print(f"\n## {dc.__name__}\n")
            print(df.to_string(index=False))
            print("\nNote: Install 'tabulate' for markdown table format")
            print(f"  -->> e:{e}")
            print()
    
    return df


@dataclass
class ExperimentMetadata:
    """User-provided experimental metadata for acquisition files.

    Field definitions and validation are driven by ``EXPERIMENT_METADATA_SCHEMA``.
    String fields are stored as ``str`` and never ``None`` (empty string is used
    for "no value"). ``depth`` and ``branch_order`` may be ``None``.

    Attributes:
        species: Animal species (e.g., "mouse", "rat").
        region: Brain region or anatomical location.
        cell_type: Type of cell or vessel being imaged.
        depth: Imaging depth in micrometers.
        branch_order: Branch order for vascular structures.
        direction: Flow direction or vessel orientation.
        sex: Animal sex.
        genotype: Genetic background or modification.
        condition: Experimental condition or treatment.
        condition2: Second condition field.
        treatment: Treatment applied.
        treatment2: Second treatment field.
        date: User-editable date (e.g., experiment date).
        note: Free-form notes or comments.
    """

    section_id: ClassVar[str] = 'experiment_metadata'
    display_section_title: ClassVar[str] = 'Experiment Metadata'

    species: str = ''
    region: str = ''
    cell_type: str = ''
    depth: float | None = None
    branch_order: int | None = None
    direction: str = ''
    sex: str = ''
    genotype: str = ''
    condition: str = ''
    condition2: str = ''
    treatment: str = ''
    treatment2: str = ''
    date: str = ''
    note: str = ''

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> ExperimentMetadata:
        """Create instance from dictionary, ignoring unknown keys.

        String fields accept ``None`` in the payload and coerce to ``""``.

        Args:
            payload: Dictionary containing metadata fields. Can be None or empty.

        Returns:
            ``ExperimentMetadata`` instance with values from payload, or defaults
            if payload is None or empty.
        """
        payload = payload or {}
        valid = {f.name for f in fields(cls) if f.init}
        known: dict[str, Any] = {}
        for k in payload.keys() & valid:
            v = payload[k]
            if k in {
                'species',
                'region',
                'cell_type',
                'direction',
                'sex',
                'genotype',
                'condition',
                'condition2',
                'treatment',
                'treatment2',
                'date',
                'note',
            }:
                known[k] = '' if v is None else str(v)
            else:
                known[k] = v
        return cls(**known)

    def to_dict(self) -> dict[str, Any]:
        """Return all field values as a plain dictionary (not schema-validated)."""
        return asdict(self)

    def get_schema(self) -> SchemaDefinition:
        """Return the semantic schema for this metadata section."""
        return EXPERIMENT_METADATA_SCHEMA

    def get_values(self) -> dict[str, object]:
        """Return values keyed by ``FieldSchema.name`` for ``get_schema()``."""
        values: dict[str, object] = {}
        for fs in self.get_schema().fields:
            raw = getattr(self, fs.name)
            if fs.value_type is ValueType.STR:
                values[fs.name] = '' if raw is None else str(raw)
            else:
                values[fs.name] = raw
        validate_values_for_schema(self.get_schema(), values)
        return values

    @staticmethod
    def _coerce_patch_value(fs: FieldSchema, value: object) -> object:
        """Coerce a single patch value to a type suitable for ``setattr``."""
        if fs.value_type is ValueType.STR:
            return '' if value is None else str(value)
        if fs.value_type is ValueType.INT:
            if value is None or value == '':
                return None
            return int(value)  # type: ignore[arg-type]
        if fs.value_type is ValueType.FLOAT:
            if value is None or value == '':
                return None
            return float(value)  # type: ignore[arg-type]
        return value

    def update_values(self, patch: dict[str, object]) -> None:
        """Apply an edit patch to editable fields only.

        Args:
            patch: Mapping from schema field names to new values.

        Raises:
            KeyError: If a patch key is not declared by the schema.
            ValueError: If a patch targets a non-editable field.
        """
        schema = self.get_schema()
        validate_patch_for_schema(schema, patch)
        fields_by_name = {f.name: f for f in schema.fields}
        for name, value in patch.items():
            coerced = self._coerce_patch_value(fields_by_name[name], value)
            setattr(self, name, coerced)


@dataclass
class AcqImgHeader:
    """Header metadata for acquired images.
    
    Contains all header-related fields that can be set from metadata without
    loading the full image data. This enables lazy loading of image data while
    still providing access to essential metadata.
    
    Attributes:
        shape: Image shape tuple (e.g., (1000, 500) for 2D, (100, 1000, 500) for 3D).
        ndim: Number of dimensions (2 or 3).
        voxels: Physical unit of each voxel (e.g., [0.001, 0.284] for time and space).
        voxels_units: Units for each voxel (e.g., ['s', 'um']).
        labels: Labels for each dimension (e.g., ['time (s)', 'space (um)']).
        physical_size: Physical size along each dimension (shape[i] * voxels[i]).
        date_str: Acquisition date string from Olympus header (read-only, if available).
        time_str: Acquisition time string from Olympus header (read-only, if available).
    """
    
    # Note: Many fields are list/tuple types; the metadata here is mainly to
    # support future UI/schema usage (e.g., forms, column configs).
    shape: tuple[int, ...] | None = field(
        default=None,
        metadata=field_metadata(
            editable=False,
            label="Shape",
            widget_type="text",
            grid_span=1,
        ),
    )
    ndim: int | None = field(
        default=None,
        metadata=field_metadata(
            editable=False,
            label="Dimensions",
            widget_type="number",
            grid_span=1,
        ),
    )
    voxels: list[float] | None = field(
        default=None,
        metadata=field_metadata(
            editable=False,
            label="Voxel Size",
            widget_type="text",
            grid_span=1,
        ),
    )
    voxels_units: list[str] | None = field(
        default=None,
        metadata=field_metadata(
            editable=False,
            label="Voxel Units",
            widget_type="text",
            grid_span=1,
        ),
    )
    labels: list[str] | None = field(
        default=None,
        metadata=field_metadata(
            editable=False,
            label="Axis Labels",
            widget_type="text",
            grid_span=1,
        ),
    )
    physical_size: list[float] | None = field(
        default=None,
        metadata=field_metadata(
            editable=False,
            label="Physical Size",
            widget_type="text",
            grid_span=1,
        ),
    )
    date_str: str | None = field(
        default=None,
        metadata=field_metadata(
            editable=False,
            label="Acquisition Date",
            widget_type="text",
            grid_span=1,
        ),
    )
    time_str: str | None = field(
        default=None,
        metadata=field_metadata(
            editable=False,
            label="Acquisition Time",
            widget_type="text",
            grid_span=1,
        ),
    )
    
    def __post_init__(self) -> None:
        """Validate consistency after initialization.
        
        Checks that all fields are consistent with ndim if ndim is set.
        This is optional validation - fields can be set incrementally and
        validated explicitly when needed.
        """
        if self.ndim is not None:
            self._validate_consistency()
    
    def _validate_consistency(self) -> None:
        """Validate that all fields are consistent with ndim.
        
        Raises:
            ValueError: If any field length doesn't match ndim.
        """
        if self.ndim is None:
            return
        
        if self.ndim not in (2, 3):
            raise ValueError(f"ndim must be 2 or 3, got {self.ndim}")
        
        # Validate shape
        if self.shape is not None and len(self.shape) != self.ndim:
            raise ValueError(f"shape length {len(self.shape)} doesn't match ndim {self.ndim}")
        
        # Validate voxels
        if self.voxels is not None and len(self.voxels) != self.ndim:
            raise ValueError(f"voxels length {len(self.voxels)} doesn't match ndim {self.ndim}")
        
        # Validate voxels_units
        if self.voxels_units is not None and len(self.voxels_units) != self.ndim:
            raise ValueError(f"voxels_units length {len(self.voxels_units)} doesn't match ndim {self.ndim}")
        
        # Validate labels
        if self.labels is not None and len(self.labels) != self.ndim:
            raise ValueError(f"labels length {len(self.labels)} doesn't match ndim {self.ndim}")
    
    def validate_ndim(self, ndim: int) -> bool:
        """Validate that ndim is consistent with existing header fields.
        
        Args:
            ndim: Number of dimensions to validate.
            
        Returns:
            True if ndim is valid and consistent with existing fields.
        """
        if ndim not in (2, 3):
            return False
        
        # Check consistency with shape
        if self.shape is not None and len(self.shape) != ndim:
            return False
        
        # Check consistency with voxels
        if self.voxels is not None and len(self.voxels) != ndim:
            return False
        
        # Check consistency with voxels_units
        if self.voxels_units is not None and len(self.voxels_units) != ndim:
            return False
        
        # Check consistency with labels
        if self.labels is not None and len(self.labels) != ndim:
            return False
        
        return True
    
    def validate_shape(self, shape: tuple[int, ...]) -> bool:
        """Validate that shape is consistent with existing header fields.
        
        Args:
            shape: Shape tuple to validate.
            
        Returns:
            True if shape is valid and consistent with existing fields.
        """
        if not shape or len(shape) not in (2, 3):
            return False
        
        ndim = len(shape)
        
        # Check consistency with ndim
        if self.ndim is not None and self.ndim != ndim:
            return False
        
        # Check consistency with voxels
        if self.voxels is not None and len(self.voxels) != ndim:
            return False
        
        # Check consistency with voxels_units
        if self.voxels_units is not None and len(self.voxels_units) != ndim:
            return False
        
        # Check consistency with labels
        if self.labels is not None and len(self.labels) != ndim:
            return False
        
        return True
    
    def compute_physical_size(self) -> list[float] | None:
        """Compute physical size from shape and voxels.
        
        Returns:
            List of physical sizes (shape[i] * voxels[i]) for each dimension,
            or None if shape or voxels are not set.
        """
        if self.shape is None or self.voxels is None:
            return None
        
        if len(self.shape) != len(self.voxels):
            return None
        
        return [s * v for s, v in itertools.zip(self.shape, self.voxels)]
    
    # ------------------------------------------------------------------
    # New helper methods for AcqImage
    # ------------------------------------------------------------------
    def set_shape_ndim(self, shape: tuple[int, ...] | None, ndim: int | None) -> None:
        """Set shape and ndim with consistency validation."""
        if shape is not None:
            self.shape = shape
            if ndim is None:
                ndim = len(shape)
        self.ndim = ndim
        # Validate current state
        self._validate_consistency()

    def init_defaults_from_shape(self) -> None:
        """Initialize default voxels/units/labels based on ndim if not set."""
        if self.ndim is None:
            return
        # Only initialize if currently None
        if self.voxels is None:
            self.voxels = [1.0] * self.ndim
        if self.voxels_units is None:
            self.voxels_units = ["px"] * self.ndim
        if self.labels is None:
            self.labels = [""] * self.ndim
        # Compute physical size
        self.physical_size = self.compute_physical_size()
        # Validate
        self._validate_consistency()

    def to_dict(self) -> dict[str, Any]:
        """Serialize header to a dictionary for metadata save."""
        result = {
            "shape": list(self.shape) if self.shape is not None else None,
            "ndim": self.ndim,
            "voxels": self.voxels,
            "voxels_units": self.voxels_units,
            "labels": self.labels,
            "physical_size": self.physical_size,
        }
        # Include date_str and time_str if they are not None
        if self.date_str is not None:
            result["date_str"] = self.date_str
        if self.time_str is not None:
            result["time_str"] = self.time_str
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcqImgHeader:
        """Deserialize header from a dictionary."""
        header = cls()
        if not data:
            return header
        if "shape" in data:
            header.shape = tuple(data["shape"]) if data["shape"] is not None else None
        if "ndim" in data:
            header.ndim = data["ndim"]
        if "voxels" in data:
            header.voxels = data["voxels"]
        if "voxels_units" in data:
            header.voxels_units = data["voxels_units"]
        if "labels" in data:
            header.labels = data["labels"]
        if "physical_size" in data:
            header.physical_size = data["physical_size"]
        if "date_str" in data:
            header.date_str = data["date_str"]
        if "time_str" in data:
            header.time_str = data["time_str"]
        # If physical_size missing but shape+voxels present, compute
        if header.physical_size is None:
            header.physical_size = header.compute_physical_size()
        # Validate consistency
        header._validate_consistency()
        return header

    # ------------------------------------------------------------------
    # Optional schema helper for UI (similar to ExperimentMetadata)
    # ------------------------------------------------------------------
    @classmethod
    def form_schema(cls) -> list[dict[str, Any]]:
        """Return field schema for form generation.

        Mirrors the pattern used in ExperimentMetadata.form_schema(). This can
        be used by GUI code to dynamically build an AcqImageHeader form.
        """
        from dataclasses import fields

        schema: list[dict[str, Any]] = []
        for field_obj in fields(cls):
            meta = field_obj.metadata
            schema.append(
                {
                    "name": field_obj.name,
                    "label": meta.get(
                        "label", field_obj.name.replace("_", " ").title()
                    ),
                    "editable": meta.get("editable", False),
                    "widget_type": meta.get("widget_type", "text"),
                    "grid_span": meta.get("grid_span", 1),
                    "visible": meta.get("visible", True),
                    "field_type": str(field_obj.type),
                }
            )
        return schema

    @classmethod
    def from_data(cls, shape: tuple[int, ...], ndim: int) -> AcqImgHeader:
        """Create header from image data shape and ndim.
        
        Initializes default values for voxels, voxels_units, and labels.
        
        Args:
            shape: Image shape tuple.
            ndim: Number of dimensions.
            
        Returns:
            AcqImgHeader instance with shape and ndim set, and default values
            for other fields.
        """
        header = cls()
        header.shape = shape
        header.ndim = ndim
        header.voxels = [1.0] * ndim
        header.voxels_units = ["px"] * ndim
        header.labels = [""] * ndim
        header.physical_size = header.compute_physical_size()
        return header

