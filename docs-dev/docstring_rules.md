# Docstring Rules for CloudScope

CloudScope uses MkDocs and mkdocstrings to generate API documentation from source code. This means source docstrings are not optional comments; they are part of the public documentation surface for scientific users, data scientists, developers, and AI coding assistants.

## General rule

Write module and class docstrings when new code is created, then maintain those docstrings as the code evolves. Do not wait until the end of a feature to document the public API.

## Module docstrings

Every public module should start with a module docstring that explains why the module exists and how it fits into the package.

A good module docstring should answer:

- What responsibility does this module own?
- Which package layer does it belong to (`acqstore`, `nicewidgets`, or `cloudscope`)?
- Is the module intended for public scripting use, GUI/internal use, or both?
- What are the main classes or functions users should start with?

Avoid module docstrings that only repeat the filename.

## Class docstrings

Every public class should have a class docstring that explains what the object represents and how it is normally used.

For `acqstore` classes, class docstrings should usually include:

- the scientific or data-model concept represented by the class,
- ownership relationships, such as image data, metadata, ROIs, or analysis results,
- whether the class is a preferred scripting entry point,
- whether the class is also used by the GUI,
- important side effects, such as loading sidecar files or writing results.

## Function and method docstrings

Use Google-style docstrings for public functions and methods.

Include sections as appropriate:

```python
def get_roi_image(self, channel: int, roi_id: str) -> np.ndarray:
    """Return image data cropped to an ROI.

    Args:
        channel: Zero-based channel index.
        roi_id: ROI identifier.

    Returns:
        Image data for the selected channel and ROI.

    Raises:
        KeyError: If `roi_id` is not present.
    """
```

## Scientific details that must be documented

For analysis and data-access APIs, document the scientific contract explicitly:

- array shape,
- axis order,
- channel indexing convention,
- ROI coordinate system,
- pixel units,
- time units,
- physical units,
- result units,
- whether analysis runs on full-resolution data or display pyramids,
- whether multiprocessing or multithreading may be used.

## Public vs internal status

Docstrings should help readers understand API stability.

Use wording such as:

- "This is the preferred scripting entry point."
- "This method is primarily used by the CloudScope GUI."
- "This helper is internal and may change."

Do not expose convenience wrappers as stable public APIs unless they are intended to be maintained.

## Examples

Use short examples in docstrings only when they clarify the immediate API. Long workflows belong in `docs/` pages or notebooks.

Good docstring examples:

- create an `AcqImageList`,
- load a file,
- access image data,
- run one analysis,
- inspect one result table.

Bad docstring examples:

- full tutorials,
- multi-page workflows,
- GUI instructions,
- explanations better suited for notebooks.

## MkDocs API rendering target

The first API documentation pass should focus on:

- `AcqImage`,
- `AcqImageList`,
- velocity analysis,
- diameter analysis,
- batch analysis.

These docstrings should be written so generated API pages are useful even when the surrounding Markdown page is only a short introduction.
