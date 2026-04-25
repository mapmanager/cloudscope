
from pathlib import Path
import os

from acqstore.acq_image import ALLOWED_IMPORT_EXTENSIONS
from acqstore.acq_image import AcqImage

def _build_file_list(path: str | Path, file_types: list[str]) -> list[str]:
    """Build a list of files in the given path.

    Recursively traverse into path and build a list of files with the given types.

    Args:
        path: The path to traverse.
        file_types: The types of files to include in the list (no dot extension)

    Returns:
        A list of absolute file paths.
    """
    allowed_exts = {f".{ext.lower().lstrip('.')}" for ext in file_types}
    result: list[str] = []

    for root, _dirs, filenames in os.walk(str(path)):
        for filename in filenames:
            file_path = Path(root) / filename
            if file_path.suffix.lower() in allowed_exts:
                result.append(str(file_path.resolve()))
    return result

class AcqImageList:
    """Given path or file, make list of AcqImage instances."""
    def __init__(self, path: str):
        self.path = path
        
        if os.path.isdir(path):
            self.file_list = _build_file_list(path, ALLOWED_IMPORT_EXTENSIONS)
        else:
            self.file_list = [path]

        self.acq_images = [AcqImage(file_path) for file_path in self.file_list]

    def get_acq_images(self) -> list[AcqImage]:
        return self.acq_images