import os
import shutil
from pathlib import Path


def copy_selected_files(source_dir: str, destination_base: str):
    """Recursively walks through source_dir and copies .

    tif and .txt files to destination_base while preserving the subfolder
    hierarchy.
    """
    source_path = Path(source_dir).resolve()
    dest_base_path = Path(destination_base).resolve()

    # Safety check to prevent infinite loops if destination is inside source
    if dest_base_path.is_relative_to(source_path):
        print(
            f"Error: Destination folder cannot be inside the source folder."
        )
        return

    print(f"Scanning: {source_path}")
    print(f"Copying to: {dest_base_path}\n")

    # Extensions to look for (case-insensitive handling via .lower())
    target_extensions = {".tif", ".tiff", ".txt"}

    copied_count = 0

    # Recursively traverse the directory
    for file_path in source_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in target_extensions:
            # Calculate the relative path from the source root
            relative_path = file_path.relative_to(source_path)

            # Construct the absolute destination path
            final_dest_path = dest_base_path / relative_path

            # Create the necessary subfolders in the destination
            final_dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file (preserves metadata like timestamps)
            shutil.copy2(file_path, final_dest_path)
            print(f"Copied: {relative_path}")
            copied_count += 1

    print(f"\nTask complete. Total files copied: {copied_count}")


if __name__ == "__main__":
    # --- CONFIGURATION ---
    # Define your source and destination paths here
    INPUT_PATH = (
        "/Users/cudmore/Desktop/old_20260412/kymflow-stall/declan-stall-v1"
    )
    DESTINATION_PATH = "/Users/cudmore/Desktop/copied_results"
    # ---------------------

    # Execute the copy operation
    copy_selected_files(INPUT_PATH, DESTINATION_PATH)