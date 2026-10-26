import json
import csv
from streamstats import models
from streamstats.errors import InvalidEventError

def stream_events(files, skip_invalid_flag):
    for file in files:
        with open(file, 'r', encoding='utf-8', newline='') as f:

            # JSONL
            if file.endswith('.jsonl'):
                for line_number, line in enumerate(f, start=1):
                    clean_line = line.strip()
                    if not clean_line:
                        continue
                    try:
                        event = json.loads(clean_line)
                        yield models.validation(event)
                    except Exception as e:
                        if skip_invalid_flag:
                            print(f"Warning in {file} line {line_number}")
                            yield "SKIP"
                        else:
                            raise InvalidEventError("Bad event", file=file, line=line_number) from e


            # CSV
            elif file.endswith('.csv'):
                reader = csv.DictReader(f)
                for line_number, row in enumerate(reader, start=2):
                    if not row or not any(row.values()):
                        continue
                    try:
                        yield models.validation(row)
                    except Exception as e:
                        if skip_invalid_flag:
                            print(f"Warning in {file} line {line_number}")
                            yield "SKIP"
                        else:
                            raise InvalidEventError("Bad event", file=file, line=line_number) from e
