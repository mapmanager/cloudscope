import csv
import json
from collections import defaultdict
from pathlib import Path


FOLDER_3_OUTPUT = "/Users/cudmore/Sites/cloudscope-data/data/manning_velocity_oir_20260625"
MASTER_CSV = "/Users/cudmore/Sites/cloudscope-data/data/Baseline_Bloodflow_Master.csv"

DRY_RUN: bool = False

CSV_TO_METADATA = {
    "Genotype": "genotype",
    "Sex": "sex",
    "Age": "age",
    "Order": "branch_order",
    "Direction": "direction",
    "Depth": "depth",
    "Quality": "note",
}


def _read_master_csv(master_csv: Path) -> list[dict[str, str]]:
    with master_csv.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


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
    print(f"DRY_RUN:    {DRY_RUN}\n")

    skip_messages: list[str] = []
    warning_messages: list[str] = []
    updated_messages: list[str] = []

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

    for oir_path in oir_paths:
        expected_tif_name = f"{oir_path.stem}.tif"
        matching_rows = master_index.get(expected_tif_name, [])

        if not matching_rows:
            skip_messages.append(
                f"SKIP no master CSV row for OIR: {oir_path} "
                f"(expected file={expected_tif_name})"
            )
            continue

        if len(matching_rows) > 1:
            skip_messages.append(
                f"SKIP duplicate master CSV rows for OIR: {oir_path} "
                f"(expected file={expected_tif_name})"
            )
            for row in matching_rows:
                skip_messages.append(
                    f"    parentFolder={row.get('parentFolder', '')}, "
                    f"file={row.get('file', '')}"
                )
            continue

        row = matching_rows[0]
        expected_parent_folder = row.get("parentFolder", "").strip()
        actual_parent_folder = oir_path.parent.name

        if actual_parent_folder != expected_parent_folder:
            skip_messages.append(
                f"SKIP parentFolder mismatch for OIR: {oir_path} "
                f"(folder={actual_parent_folder}, csv={expected_parent_folder})"
            )
            continue

        json_path = oir_path.with_name(f"{oir_path.name}.json")

        if not json_path.exists():
            skip_messages.append(f"SKIP missing CloudScope JSON: {json_path}")
            continue

        with json_path.open("r", encoding="utf-8") as f:
            json_data = json.load(f)

        experiment_metadata = json_data.setdefault("experiment_metadata", {})

        changes: list[str] = []

        for csv_column, metadata_key in CSV_TO_METADATA.items():
            new_value = row.get(csv_column, "").strip()
            old_value = experiment_metadata.get(metadata_key)

            if old_value != new_value:
                changes.append(f"{metadata_key}: {old_value!r} -> {new_value!r}")
                experiment_metadata[metadata_key] = new_value

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

    print("Task complete.")
    print(f"OIR files scanned: {len(oir_paths)}")
    print(f"JSON files updated: {sum(1 for msg in updated_messages if msg.startswith('UPDATE '))}")

    _print_messages("Planned/Completed updates:", updated_messages)
    _print_messages("Warnings:", warning_messages)
    _print_messages("Skipped messages:", skip_messages)


if __name__ == "__main__":
    update_cloudscope_json_from_master_csv(
        FOLDER_3_OUTPUT,
        MASTER_CSV,
    )