import json


def create_report(stats, output_file):
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
        "sources": stats["source_counts"]
    }

    if stats["skipped_count"] > 0:
        report_data["skipped_lines"] = stats["skipped_count"]

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
    else:
        # Если --output не передали, просто выводим отчет в консоль
        print(json.dumps(report_data, ensure_ascii=False, indent=4))
