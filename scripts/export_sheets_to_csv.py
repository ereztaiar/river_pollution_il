"""Export each sheet of the river pollution workbook to its own CSV file."""

import csv
from pathlib import Path

import openpyxl

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SOURCE_XLSX = PROJECT_ROOT / "data" / "units_environmental_health_streams.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "data" / "csv"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.load_workbook(SOURCE_XLSX, data_only=True)
    for ws in wb.worksheets:
        out_path = OUTPUT_DIR / f"{ws.title}.csv"
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                writer.writerow(row)
        print(f"Wrote {out_path} ({ws.dimensions})")


if __name__ == "__main__":
    main()
