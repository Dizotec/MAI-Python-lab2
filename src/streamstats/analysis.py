def statistics(events, skip_invalid_flag):
    event_count = 0
    level_count = {}
    errors_source_count = {}
    f_timestamp = None
    l_timestamp = None
    skipped_count = 0
    source_count = {}
    for i in events:
        if i == 'SKIP':
            skipped_count += 1
            continue

        if i.source not in source_count:
            source_count[i.source] = 1
        else:
            source_count[i.source] +=1

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


        if f_timestamp is None or f_timestamp > i.timestamp:
            f_timestamp = i.timestamp
        if l_timestamp is None or l_timestamp < i.timestamp:
            l_timestamp= i.timestamp



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
        "skipped_count": skipped_count,
        "source_counts":source_count
    }
