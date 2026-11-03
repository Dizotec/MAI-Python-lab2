import json
import logging
import sys
from pathlib import Path

from streamstats import analysis, models, parsers, report
from streamstats.errors import CLIConfigurationError, StreamStatsError


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    for f in (sys.stdout, sys.stderr):
        if hasattr(f, "reconfigure"):
            f.reconfigure(encoding="utf-8")

    args = sys.argv[1:]

    if args == ["--help"]:
        print(
            "Usage: python -m streamstats analyze INPUT... --format csv|jsonl|binary [--output REPORT.json|REPORT.csv] [--skip-invalid]"
        )
        print("Filters: --start ISO --end ISO --level LEVEL --source SOURCE")
        print("Follow: --follow (one JSONL file, Ctrl+C saves report)")
        return

    try:
        if not args or args[0] != "analyze":
            raise CLIConfigurationError("Expected command: analyze (or --help)")

        skip_invalid_flag = args[-1] == "--skip-invalid"

        if skip_invalid_flag:
            args.pop()

        follow_flag = args[-1] == "--follow"

        if follow_flag:
            args.pop()

        try:
            format_index = args.index("--format")
            files = args[1:format_index]
            format_files = args[format_index + 1]
        except (ValueError, IndexError) as e:
            raise CLIConfigurationError("Expected --format with a value") from e

        if not files or any(file.startswith("--") for file in files):
            raise CLIConfigurationError("Expected input files before --format")

        parsers.get_parser(format_files)
        tail = args[format_index + 2 :]
        opts: dict[str, str] = {}
        # Флаги только в этом порядке.
        for arg in ("--output", "--start", "--end", "--level", "--source"):
            if not tail or tail[0] != arg:
                continue

            if len(tail) < 2 or tail[1].startswith("--"):
                raise CLIConfigurationError(f"Missing value after {arg}")

            opts[arg] = tail[1]
            tail = tail[2:]

        if tail:
            raise CLIConfigurationError(f"Unknown or misplaced argument: {tail[0]}")

        output_file = opts.get("--output")
        time_from = (
            models.parse_timestamp(opts["--start"]) if "--start" in opts else None
        )
        time_to = models.parse_timestamp(opts["--end"]) if "--end" in opts else None
        level = opts.get("--level")
        source = opts.get("--source")

        if time_from is not None and time_to is not None and time_from > time_to:
            raise CLIConfigurationError("--start must not be later than --end")

        if level is not None and level not in models.LEVELS:
            raise CLIConfigurationError(f"Invalid log level: {level}")

        if source is not None and not source.strip():
            raise CLIConfigurationError("Source filter cannot be empty")

        if output_file:
            for file in files:
                if Path(output_file).resolve() == Path(file).resolve() or (
                    Path(output_file).exists()
                    and Path(file).exists()
                    and Path(output_file).samefile(file)
                ):
                    raise CLIConfigurationError(
                        "Output must not overwrite an input file"
                    )

        if follow_flag:
            if len(files) != 1 or format_files != "jsonl":
                raise CLIConfigurationError("--follow requires one JSONL file")

            lines = parsers.follow_lines(files[0])
            events_stream = parsers.parse_text_lines(
                lines, files[0], json.loads, skip_invalid_flag
            )
        else:
            events_stream = parsers.stream_events(
                files, skip_invalid_flag, format_files
            )

        events_stream = analysis.filter_events(
            events_stream, time_from, time_to, level, source.strip() if source else None
        )
        stats = analysis.statistics(
            events_stream, skip_invalid_flag, follow_flag=follow_flag
        )
        report.create_report(stats, output_file)

    except (StreamStatsError, OSError, UnicodeError) as e:
        file = getattr(e, "file", "") or ""
        line = getattr(e, "line", None)

        if not file:
            print(f"Error: {e}", file=sys.stderr)
        else:
            print(f"Error in {file} line {line}: {e}", file=sys.stderr)

        sys.exit(2)

    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
