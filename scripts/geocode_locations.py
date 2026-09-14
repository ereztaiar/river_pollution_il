"""Add Latitude/Longitude columns to locations.csv using headless Claude Code (Haiku + WebSearch).

Requires the `claude` CLI on PATH. Resumable: a `Tries` column in the output
records how many times each location has been attempted, so re-running skips
locations that already have coordinates, and separately skips locations that
were tried but came up empty (unless --retry-unfound is passed, which retries
those and bumps their Tries count again). Delete the output file to force a
full re-run from scratch.
"""

import argparse
import csv
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_PATH = PROJECT_ROOT / "data" / "locations.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "locations_with_coordinates.csv"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / f"geocode_locations_{datetime.datetime.now():%Y%m%d_%H%M%S}.jsonl"

NAME_COLUMN = "שם נקודה"
SITE_COLUMN = "אתר"
MODEL = "claude-haiku-4-5-20251001"

CLAUDE_BIN = shutil.which("claude")
if CLAUDE_BIN is None:
    sys.exit(
        "claude CLI not found on PATH.\n"
        "Install it with: npm install -g @anthropic-ai/claude-code\n"
        "then open a new terminal so PATH picks it up."
    )

PROMPT_TEMPLATE = (
    "This is a water-quality monitoring point on a river/stream in Israel. "
    'Point name: "{name}". General site/area: "{site}". '
    "Search the web to find accurate WGS84 decimal-degree coordinates for this "
    "exact point (fall back to the general site's coordinates if the specific "
    "point can't be pinned down). Respond with ONLY a JSON object, no other "
    'text: {{"latitude": <number or null>, "longitude": <number or null>}}'
)


def log_call(name: str, site: str, response: dict | None, error: str | None = None) -> dict:
    usage = (response or {}).get("usage", {})
    entry = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "name": name,
        "site": site,
        "model": MODEL,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "total_cost_usd": (response or {}).get("total_cost_usd"),
        "duration_ms": (response or {}).get("duration_ms"),
        "num_turns": (response or {}).get("num_turns"),
        "error": error,
    }
    LOG_DIR.mkdir(exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def geocode(name: str, site: str) -> tuple[float | None, float | None, dict]:
    prompt = PROMPT_TEMPLATE.format(name=name, site=site)
    try:
        result = subprocess.run(
            [
                CLAUDE_BIN,
                "-p",
                prompt,
                "--model",
                MODEL,
                "--output-format",
                "json",
                "--allowedTools",
                "WebSearch,WebFetch",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=240,
        )
    except subprocess.TimeoutExpired:
        log_call(name, site, None, error="timeout")
        print("  timed out waiting for claude CLI")
        return None, None, {}

    if result.returncode != 0:
        error = result.stderr.strip()
        log_call(name, site, None, error=error)
        print(f"  claude CLI error: {error}")
        return None, None, {}

    try:
        response = json.loads(result.stdout)
        text = response["result"]
    except (json.JSONDecodeError, KeyError):
        log_call(name, site, None, error="unparseable claude output")
        print(f"  unexpected claude output: {result.stdout[:200]!r}")
        return None, None, {}

    entry = log_call(name, site, response)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        print(f"  no JSON found in response: {text[:200]!r}")
        return None, None, entry

    try:
        coords = json.loads(match.group(0))
    except json.JSONDecodeError:
        print(f"  malformed JSON in response: {match.group(0)[:200]!r}")
        return None, None, entry

    return coords.get("latitude"), coords.get("longitude"), entry


def is_found(row: dict) -> bool:
    return bool(row.get("Latitude")) and bool(row.get("Longitude"))


def load_existing() -> dict[tuple[str, str], dict]:
    if not OUTPUT_PATH.exists():
        return {}
    with open(OUTPUT_PATH, encoding="utf-8-sig", newline="") as f:
        return {(r[NAME_COLUMN], r[SITE_COLUMN]): r for r in csv.DictReader(f)}


def save(fieldnames: list[str], results: dict[tuple[str, str], dict], order: list[tuple[str, str]]) -> None:
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key in order:
            writer.writerow(results[key])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="only process the first N pending rows (for testing)"
    )
    parser.add_argument(
        "--retry-unfound",
        action="store_true",
        help="also re-attempt rows that were already tried but had no coordinates found",
    )
    args = parser.parse_args()

    with open(INPUT_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys()) + ["Latitude", "Longitude", "Tries"]
    order = [(row[NAME_COLUMN], row[SITE_COLUMN]) for row in rows]

    existing = load_existing()
    results = {
        key: existing.get(key, {**rows[i], "Latitude": "", "Longitude": "", "Tries": 0})
        for i, key in enumerate(order)
    }

    def tries_of(key: tuple[str, str]) -> int:
        return int(results[key].get("Tries") or 0)

    pending = [
        key
        for key in order
        if not is_found(results[key]) and (tries_of(key) == 0 or args.retry_unfound)
    ]
    # Least-tried locations first, so a --limit run spreads attempts across
    # every unfound location instead of hammering the same one repeatedly.
    pending.sort(key=tries_of)
    if args.limit is not None:
        pending = pending[: args.limit]

    processed = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost_usd = 0.0
    for key in pending:
        tries = tries_of(key)
        name, site = key
        print(f"[{processed + 1}/{len(pending)}] {name} ({site})... (try {tries + 1})")
        lat, lon, usage = geocode(name, site)
        total_input_tokens += usage.get("input_tokens") or 0
        total_output_tokens += usage.get("output_tokens") or 0
        total_cost_usd += usage.get("total_cost_usd") or 0.0
        results[key] = {**results[key], "Latitude": lat, "Longitude": lon, "Tries": tries + 1}
        processed += 1
        save(fieldnames, results, order)

    print(f"Processed {processed} location(s) this run. Results in {OUTPUT_PATH}")
    print(
        f"Tokens used: {total_input_tokens} in / {total_output_tokens} out "
        f"(${total_cost_usd:.4f}). Per-call log: {LOG_PATH}"
    )


if __name__ == "__main__":
    main()
