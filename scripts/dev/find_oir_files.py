import os
import shutil
from pathlib import Path


def sync_oir_to_tif_structure(tif_dir: str, oir_dir: str, output_dir: str):
    """Scans tif_dir for .tif files, finds matching .

    oir files in oir_dir, and copies them to output_dir mirroring the original
    .tif subfolder structure.
    """
    folder1 = Path(tif_dir).resolve()
    folder2 = Path(oir_dir).resolve()
    folder3 = Path(output_dir).resolve()

    print(f"Folder 1 (TIF Source): {folder1}")
    print(f"Folder 2 (OIR Search): {folder2}")
    print(f"Folder 3 (OIR Output): {folder3}\n")

    # Prevent infinite loops if output directory is placed inside input directories
    if folder3.is_relative_to(folder1) or folder3.is_relative_to(folder2):
        print("Error: Output directory cannot be inside Folder 1 or Folder 2.")
        return

    # Step 1: Map .tif filenames to their relative subfolder structures in Folder 1
    # Key: base filename (e.g., "file_1") -> Value: relative parent directory (e.g., RelativePath("condition1/date1"))
    tif_structure_map = {}

    for tif_file in folder1.rglob("*.tif"):
        base_name = tif_file.stem
        # Get the subfolder hierarchy relative to Folder 1 root
        relative_parent = tif_file.relative_to(folder1).parent
        tif_structure_map[base_name] = relative_parent

    if not tif_structure_map:
        print("No .tif files found in Folder 1.")
        return

    print(f"Indexed {len(tif_structure_map)} .tif files from Folder 1.")
    print("Searching Folder 2 and copying matches...\n")

    copied_count = 0

    # Step 2: Traverse Folder 2 and look up matches in our map
    for oir_file in folder2.rglob("*.oir"):
        base_name = oir_file.stem

        if base_name in tif_structure_map:
            # Retrieve the mapped relative subfolder structure from Folder 1
            target_relative_dir = tif_structure_map[base_name]

            # Construct the absolute destination path in Folder 3
            destination_dir = folder3 / target_relative_dir
            destination_file_path = destination_dir / oir_file.name

            # Ensure the nested directory structure exists in Folder 3
            destination_dir.mkdir(parents=True, exist_ok=True)

            # Copy the file while preserving metadata
            shutil.copy2(oir_file, destination_file_path)

            print(f"Copied: {oir_file.name}")
            print(f"    From: {oir_file.parent}")
            print(f"    To:   {destination_dir}\n")
            copied_count += 1

    print(f"Task complete. Successfully copied {copied_count} .oir files.")


if __name__ == "__main__":
    # --- CONFIGURATION ---
    FOLDER_1_TIF = "/Users/cudmore/Sites/cloudscope-data/data/manning_velocity_20260625"
    FOLDER_2_OIR = "/Users/cudmore/Library/CloudStorage/Box-Box/Two-photon"
    FOLDER_3_OIR_OUTPUT_DIR = "/Users/cudmore/Desktop/found_oir_files"
    # ---------------------

    # Check that input folders exist before running
    if os.path.exists(FOLDER_1_TIF) and os.path.exists(FOLDER_2_OIR):
        sync_oir_to_tif_structure(
            FOLDER_1_TIF, FOLDER_2_OIR, FOLDER_3_OIR_OUTPUT_DIR
        )
    else:
        print("Error: Folder 1 or Folder 2 path does not exist.")