import os
import shutil
from collections import defaultdict
from pathlib import Path


COPY_OIR_FILES: bool = False
COPY_CLOUDSCOPE_ANALYSIS: bool = True
DRY_RUN: bool = True
OVERWRITE: bool = False


def _copy_file(src: Path, dst: Path) -> bool:
    if dst.exists() and not OVERWRITE:
        print(f"SKIP exists: {dst}")
        return False

    print(f"{'DRY RUN copy' if DRY_RUN else 'Copy'}:")
    print(f"    From: {src}")
    print(f"    To:   {dst}")

    if not DRY_RUN:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return True


def _index_by_stem(root: Path, pattern: str) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    for path in root.rglob(pattern):
        index[path.stem].append(path)
    return dict(index)


def sync_oir_and_analysis_to_tif_structure(
    tif_dir: str,
    oir_dir: str,
    output_dir: str,
) -> None:
    folder1 = Path(tif_dir).resolve()
    folder2 = Path(oir_dir).resolve()
    folder3 = Path(output_dir).resolve()

    print(f"Folder 1 (TIF Source): {folder1}")
    print(f"Folder 2 (OIR Search): {folder2}")
    print(f"Folder 3 (Output):     {folder3}\n")

    if folder3.is_relative_to(folder1) or folder3.is_relative_to(folder2):
        print("Error: Output directory cannot be inside Folder 1 or Folder 2.")
        return

    tif_index = _index_by_stem(folder1, "*.tif")
    oir_index = _index_by_stem(folder2, "*.oir")

    if not tif_index:
        print("No .tif files found in Folder 1.")
        return

    duplicate_tif_stems = {
        stem: paths for stem, paths in tif_index.items() if len(paths) > 1
    }

    if duplicate_tif_stems:
        print("WARNING: Duplicate TIF stems found in Folder 1.")
        print("These stems are unsafe and will not be copied.\n")

        for stem, tif_paths in sorted(duplicate_tif_stems.items()):
            print(f"Duplicate stem: {stem}")
            print("  Folder 1 TIF files:")
            for tif_path in sorted(tif_paths):
                print(f"    {tif_path}")

            print("  Folder 2 matching OIR files:")
            for oir_path in sorted(oir_index.get(stem, [])):
                print(f"    {oir_path}")
            if stem not in oir_index:
                print("    No matching OIR files found.")
            print()

    safe_tif_items = {
        stem: paths[0]
        for stem, paths in tif_index.items()
        if stem not in duplicate_tif_stems
    }

    print(f"Indexed {len(tif_index)} unique TIF stems from Folder 1.")
    print(f"Safe TIF stems: {len(safe_tif_items)}")
    print(f"Unsafe duplicate TIF stems: {len(duplicate_tif_stems)}\n")

    copied_oir_count = 0
    copied_analysis_count = 0

    if COPY_OIR_FILES:
        print("Copying OIR files...\n")

        for stem, tif_path in sorted(safe_tif_items.items()):
            matching_oir_paths = oir_index.get(stem, [])

            if not matching_oir_paths:
                print(f"Missing OIR for TIF stem: {stem}")
                continue

            if len(matching_oir_paths) > 1:
                print(f"SKIP ambiguous OIR matches for stem: {stem}")
                for oir_path in sorted(matching_oir_paths):
                    print(f"    {oir_path}")
                continue

            oir_path = matching_oir_paths[0]
            relative_parent = tif_path.relative_to(folder1).parent
            destination_path = folder3 / relative_parent / oir_path.name

            if _copy_file(oir_path, destination_path):
                copied_oir_count += 1

        print()

    if COPY_CLOUDSCOPE_ANALYSIS:
        print("Copying CloudScope analysis files...\n")

        for stem, tif_path in sorted(safe_tif_items.items()):
            relative_parent = tif_path.relative_to(folder1).parent
            destination_dir = folder3 / relative_parent
            destination_oir_path = destination_dir / f"{stem}.oir"

            if not destination_oir_path.exists():
                print(f"SKIP analysis; destination OIR does not exist: {destination_oir_path}")
                continue

            source_parent = tif_path.parent
            analysis_candidates = sorted(
                list(source_parent.glob(f"{stem}.tif*.json"))
                + list(source_parent.glob(f"{stem}.tif*.csv"))
            )

            if not analysis_candidates:
                print(f"No analysis files found for TIF: {tif_path}")
                continue

            for analysis_path in analysis_candidates:
                if ".tif." not in analysis_path.name:
                    print(f"SKIP analysis filename without '.tif.': {analysis_path}")
                    continue

                destination_name = analysis_path.name.replace(".tif.", ".oir.")
                destination_path = destination_dir / destination_name

                if _copy_file(analysis_path, destination_path):
                    copied_analysis_count += 1

        print()

    print("Task complete.")
    print(f"Copied OIR files: {copied_oir_count}")
    print(f"Copied CloudScope analysis files: {copied_analysis_count}")


if __name__ == "__main__":
    FOLDER_1_TIF = "/Users/cudmore/Sites/cloudscope-data/data/manning_velocity_20260625"
    FOLDER_2_OIR = "/Users/cudmore/Library/CloudStorage/Box-Box/Two-photon"
    FOLDER_3_OUTPUT = "/Users/cudmore/Desktop/found_oir_files"

    if os.path.exists(FOLDER_1_TIF) and os.path.exists(FOLDER_2_OIR):
        sync_oir_and_analysis_to_tif_structure(
            FOLDER_1_TIF,
            FOLDER_2_OIR,
            FOLDER_3_OUTPUT,
        )
    else:
        print("Error: Folder 1 or Folder 2 path does not exist.")