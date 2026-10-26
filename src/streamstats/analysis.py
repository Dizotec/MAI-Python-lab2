def statistics(events, skip_invalid_flag):
    event_count = 0
    level_count = {}
    errors_source_count = {}
    f_timestamp = None
    l_timestamp = None
    skipped_count = 0

    for i in events:
        if i == 'SKIP':
            skipped_count += 1
            continue


        event_count += 1

        if i.level in level_count:
            level_count[i.level] += 1
        else:
            level_count[i.level] = 1


        if i.level in ("ERROR", "CRITICAL"):
            if i.source in errors_source_count:
                errors_source_count[i.source] += 1
            else:
                errors_source_count[i.source] = 1


        if f_timestamp is None:
            f_timestamp = i.timestamp
        l_timestamp = i.timestamp

    error_items = list(errors_source_count.items())

    # Сортировка: сначала по числу ошибок в порядке убывания, потом по алфавиту
    sorted_errors = sorted(error_items, key=lambda x: (-x[1], x[0]))

    top_5_errors = sorted_errors[:5]

    return {
        "total_count": event_count,
        "level_counts": level_count,
        "top_5_sources": top_5_errors,
        "first_timestamp": f_timestamp,
        "last_timestamp": l_timestamp,
        "skipped_count": skipped_count
    }
