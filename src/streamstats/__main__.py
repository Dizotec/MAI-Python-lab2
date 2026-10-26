import sys
from streamstats import analysis, parsers,report
from streamstats.errors import StreamStatsError

def main():
    args = sys.argv[1:]

    if not args:
        print('Error: commands were expected: [ --help | analyze ]')
        sys.exit(0)
    if args[0] == '--help':
        print("Usage: python -m streamstats analyze INPUT... --format csv|jsonl [--output REPORT.json] [--skip-invalid]")
        sys.exit(0)
    if args[0] != "analyze" and args[0] != "--help":
        print("Error: commands were expected: [ analyze | --help ]")
        sys.exit(2)

    skip_invalid_flag = False
    if args[-1] == '--skip-invalid':
        skip_invalid_flag = True
        args.pop()

    try:
        format_index = args.index('--format')
        files = args[1:format_index]
        format_files = args[format_index+1]
    except ValueError:
        print("Error: missing a required flag: --format")
        sys.exit(2)


    if format_files not in ("csv", "jsonl"):
        print(f"Error: unsupported format: {format_files}")
        sys.exit(2)


    output_file = None
    if '--output' in args:
        try:
            output_index = args.index('--output')
            output_file = args[output_index+1]
        except IndexError:
            print("Erorr: no file specified after the flag: --output")
            sys.exit(2)
    try:
        events_stream = parsers.stream_events(files, skip_invalid_flag)

        stats = analysis.statistics(events_stream, skip_invalid_flag)


        report.create_report(stats, output_file)

    except StreamStatsError as e:
        file = getattr(e, 'file', 'unknown')
        line = getattr(e, 'line', 'unknown')
        print(f"Error in {file} line {line}")
        sys.exit(2)

if __name__ == "__main__":
    main()
