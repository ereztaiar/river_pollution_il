"""Collect unique (שם נקודה, אתר) pairs from all raw CSV extracts."""

import csv
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_DIR = PROJECT_ROOT / "data" / "csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "locations.csv"

NAME_COLUMN = "שם נקודה"
SITE_COLUMN = "אתר"


def read_pairs(csv_path: Path) -> list[tuple[str, str]] | None:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    header_idx = next(
        (i for i, row in enumerate(rows) if NAME_COLUMN in row and SITE_COLUMN in row),
        None,
    )
    if header_idx is None:
        return None

    header = rows[header_idx]
    name_idx, site_idx = header.index(NAME_COLUMN), header.index(SITE_COLUMN)

    pairs = []
    for row in rows[header_idx + 1 :]:
        if len(row) <= max(name_idx, site_idx):
            continue
        name, site = row[name_idx].strip(), row[site_idx].strip()
        if name:
            pairs.append((name, site))
    return pairs


def main() -> None:
    seen: dict[tuple[str, str], None] = {}

    for csv_path in sorted(INPUT_DIR.glob("*.csv")):
        pairs = read_pairs(csv_path)
        if pairs is None:
            print(f"Skipping {csv_path.name}: header row not found")
            continue
        for pair in pairs:
            seen.setdefault(pair, None)

    locations = sorted(seen.keys(), key=lambda pair: (pair[1], pair[0]))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([NAME_COLUMN, SITE_COLUMN])
        writer.writerows(locations)

    print(f"Wrote {len(locations)} unique locations to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
