def paginate(items, page, size):
    """Return a page envelope for a fictional API; never raises."""
    total = len(items)
    total_pages = (total + size - 1) // size

    if page is None:
        page = 1

    if page < 1:
        page = 1

    if total_pages and page > total_pages:
        page = total_pages

    start = ((page - 1) * size) + 1
    end = start + size

    results = list(items[start:end])

    has_previous = page > 1
    has_next = page < total_pages

    return {
        "data": results,
        "pagination": {
            "page": page,
            "size": size,
            "total_items": total,
            "total_pages": total_pages,
            "has_previous": has_previous,
            "has_next": has_next,
        },
    }
