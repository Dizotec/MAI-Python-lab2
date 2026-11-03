import csv
import json
import sys
from pathlib import Path

from streamstats.errors import UnsupportedFormatError


def create_report(
    stats: dict, output_file: str | Path | None, format_name: str | None = None
) -> None:
    first_timestamp = stats["first_timestamp"]
    last_timestamp = stats["last_timestamp"]

    if first_timestamp is not None:
        first_timestamp = first_timestamp.isoformat()

    if last_timestamp is not None:
        last_timestamp = last_timestamp.isoformat()

    report_data = {
        "total_events": stats["total_count"],
        "levels": stats["level_counts"],
        "top_5_error_sources": dict(stats["top_5_sources"]),
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "sources": stats["source_counts"],
    }

    if stats["skipped_count"] > 0 or stats.get("skip_invalid_flag", False):
        report_data["skipped_lines"] = stats["skipped_count"]

    if format_name is None:
        format_name = (
            "csv"
            if output_file and str(output_file).lower().endswith(".csv")
            else "json"
        )

    if format_name not in ("json", "csv"):
        raise UnsupportedFormatError(f"Unsupported report format: {format_name}")

    if format_name == "csv":
        csv_rows: list[list[object]] = [["section", "name", "value"]]

        for part, val in report_data.items():
            if isinstance(val, dict):
                for item, n in val.items():
                    csv_rows.append([part, item, n])
            else:
                csv_rows.append(["summary", part, val])

        if output_file:
            with open(output_file, "w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerows(csv_rows)
        else:
            csv.writer(sys.stdout).writerows(csv_rows)

    elif output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
    else:
        print(json.dumps(report_data, ensure_ascii=False, indent=4))
