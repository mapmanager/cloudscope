import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


FOLDER_3_OUTPUT = "/Users/cudmore/Sites/cloudscope-data/data/manning_velocity_oir_20260625"
MASTER_CSV = "/Users/cudmore/Sites/cloudscope-data/data/Baseline_Bloodflow_Master.csv"

DRY_RUN: bool = False
NORMALIZE_EXISTING_TYPES: bool = True

CSV_TO_METADATA = {
    "Genotype": "genotype",
    "Sex": "sex",
    "Age": "age",
    "Order": "branch_order",
    "Direction": "direction",
    "Depth": "depth",
    "Quality": "note",
}


def _to_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_float_or_none(value: Any) -> float | None:
    value_str = _to_string(value)

    if value_str == "":
        return None

    return float(value_str)


def _to_int_or_none(value: Any) -> int | None:
    value_str = _to_string(value)

    if value_str == "":
        return None

    value_float = float(value_str)
    value_int = int(value_float)

    if value_float != value_int:
        raise ValueError(f"Expected integer-compatible value, got {value!r}")

    return value_int


def _coerce_metadata_value(metadata_key: str, value: Any) -> str | int | float | None:
    if metadata_key == "depth":
        return _to_float_or_none(value)

    if metadata_key == "branch_order":
        return _to_int_or_none(value)

    return _to_string(value)


def _read_master_csv(master_csv: Path) -> list[dict[str, str]]:
    with master_csv.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [{key: _to_string(value) for key, value in row.items()} for row in reader]


def _index_master_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        filename = row.get("file", "").strip()
        if filename:
            index[filename].append(row)

    return dict(index)


def _validate_master_columns(rows: list[dict[str, str]]) -> list[str]:
    required_columns = {"file", "parentFolder", *CSV_TO_METADATA.keys()}

    if not rows:
        return ["Master CSV has no rows."]

    available_columns = set(rows[0].keys())
    missing_columns = sorted(required_columns - available_columns)

    return [f"Missing required master CSV column: {column}" for column in missing_columns]


def _print_messages(title: str, messages: list[str]) -> None:
    if not messages:
        return

    print()
    print(title)
    for message in messages:
        print(message)


def update_cloudscope_json_from_master_csv(
    folder_3_output: str,
    master_csv: str,
) -> None:
    folder3 = Path(folder_3_output).resolve()
    master_csv_path = Path(master_csv).resolve()

    print(f"Folder 3:   {folder3}")
    print(f"Master CSV: {master_csv_path}")
    print(f"DRY_RUN:    {DRY_RUN}")
    print(f"NORMALIZE_EXISTING_TYPES: {NORMALIZE_EXISTING_TYPES}\n")

    updated_messages: list[str] = []
    warning_messages: list[str] = []
    error_messages: list[str] = []
    skip_no_master_row_messages: list[str] = []
    skip_duplicate_master_row_messages: list[str] = []
    skip_parent_mismatch_messages: list[str] = []
    skip_missing_json_messages: list[str] = []

    if not folder3.exists():
        print(f"Error: Folder 3 does not exist: {folder3}")
        return

    if not master_csv_path.exists():
        print(f"Error: Master CSV does not exist: {master_csv_path}")
        return

    master_rows = _read_master_csv(master_csv_path)
    validation_messages = _validate_master_columns(master_rows)

    if validation_messages:
        _print_messages("Errors:", validation_messages)
        return

    master_index = _index_master_rows(master_rows)
    oir_paths = sorted(folder3.rglob("*.oir"))

    if not oir_paths:
        print("No .oir files found in Folder 3.")
        return

    master_csv_match_count = 0
    json_updated_count = 0

    for oir_path in oir_paths:
        expected_tif_name = f"{oir_path.stem}.tif"
        matching_rows = master_index.get(expected_tif_name, [])

        if not matching_rows:
            skip_no_master_row_messages.append(
                "\nSKIP no matching master CSV row\n"
                f"  OIR:\n"
                f"    {oir_path}\n"
                f"  Expected master CSV:\n"
                f"    file = {expected_tif_name}"
            )
            continue

        if len(matching_rows) > 1:
            skip_duplicate_master_row_messages.append(
                "\nSKIP duplicate master CSV rows\n"
                f"  OIR:\n"
                f"    {oir_path}\n"
                f"  Expected master CSV:\n"
                f"    file = {expected_tif_name}"
            )
            for row in matching_rows:
                skip_duplicate_master_row_messages.append(
                    f"    parentFolder={row.get('parentFolder', '')}, "
                    f"file={row.get('file', '')}"
                )
            continue

        master_csv_match_count += 1

        row = matching_rows[0]
        expected_parent_folder = row.get("parentFolder", "").strip()
        actual_parent_folder = oir_path.parent.name

        if actual_parent_folder != expected_parent_folder:
            skip_parent_mismatch_messages.append(
                "\nSKIP parentFolder mismatch\n"
                f"  OIR:\n"
                f"    {oir_path}\n"
                f"  Folder 3 parent folder:\n"
                f"    {actual_parent_folder}\n"
                f"  Master CSV parentFolder:\n"
                f"    {expected_parent_folder}"
            )
            continue

        json_path = oir_path.with_name(f"{oir_path.name}.json")

        if not json_path.exists():
            skip_missing_json_messages.append(
                "\nSKIP missing CloudScope JSON\n"
                f"  OIR:\n"
                f"    {oir_path}\n"
                f"  Expected JSON:\n"
                f"    {json_path}"
            )
            continue

        with json_path.open("r", encoding="utf-8") as f:
            json_data = json.load(f)

        experiment_metadata = json_data.setdefault("experiment_metadata", {})

        changes: list[str] = []
        failed_conversion = False

        for csv_column, metadata_key in CSV_TO_METADATA.items():
            try:
                new_value = _coerce_metadata_value(metadata_key, row.get(csv_column, ""))
            except ValueError as e:
                error_messages.append(
                    "\nSKIP invalid master CSV value\n"
                    f"  JSON:\n"
                    f"    {json_path}\n"
                    f"  Column:\n"
                    f"    {csv_column}\n"
                    f"  Metadata key:\n"
                    f"    {metadata_key}\n"
                    f"  Value:\n"
                    f"    {row.get(csv_column, '')!r}\n"
                    f"  Error:\n"
                    f"    {e}"
                )
                failed_conversion = True
                break

            old_value_raw = experiment_metadata.get(metadata_key)

            try:
                old_value = (
                    _coerce_metadata_value(metadata_key, old_value_raw)
                    if NORMALIZE_EXISTING_TYPES
                    else old_value_raw
                )
            except ValueError as e:
                error_messages.append(
                    "\nSKIP invalid existing JSON metadata value\n"
                    f"  JSON:\n"
                    f"    {json_path}\n"
                    f"  Metadata key:\n"
                    f"    {metadata_key}\n"
                    f"  Existing value:\n"
                    f"    {old_value_raw!r}\n"
                    f"  Error:\n"
                    f"    {e}"
                )
                failed_conversion = True
                break

            if old_value != new_value:
                changes.append(f"{metadata_key}: {old_value_raw!r} -> {new_value!r}")
                experiment_metadata[metadata_key] = new_value

        if failed_conversion:
            continue

        if not changes:
            warning_messages.append(f"No metadata changes needed: {json_path}")
            continue

        updated_messages.append(f"UPDATE {json_path}")
        for change in changes:
            updated_messages.append(f"    {change}")

        if not DRY_RUN:
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
                f.write("\n")

        json_updated_count += 1

    print("Task complete.")
    print()
    print("Summary")
    print(f"OIR files scanned:             {len(oir_paths)}")
    print(f"Master CSV matches:            {master_csv_match_count}")
    print(f"No master CSV row:             {len(skip_no_master_row_messages)}")
    print(f"Duplicate master rows:         {len(skip_duplicate_master_row_messages)}")
    print(f"Parent folder mismatches:      {len(skip_parent_mismatch_messages)}")
    print(f"Missing CloudScope JSON files: {len(skip_missing_json_messages)}")
    print(f"Conversion errors:             {len(error_messages)}")
    print(f"JSON files updated:            {json_updated_count}")

    _print_messages("Planned/Completed updates:", updated_messages)
    _print_messages("Warnings:", warning_messages)
    _print_messages("Errors:", error_messages)
    _print_messages("No master CSV row:", skip_no_master_row_messages)
    _print_messages("Duplicate master rows:", skip_duplicate_master_row_messages)
    _print_messages("Parent folder mismatches:", skip_parent_mismatch_messages)
    _print_messages("Missing CloudScope JSON files:", skip_missing_json_messages)


if __name__ == "__main__":
    update_cloudscope_json_from_master_csv(
        FOLDER_3_OUTPUT,
        MASTER_CSV,
    )