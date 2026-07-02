def clamp(value, low, high):
    """Return `value` limited to the inclusive range [low, high].

    Raises ValueError if low > high.
    """
    if low > high:
        raise ValueError(f"invalid range: low ({low}) > high ({high})")
    if value < low:
        return low
    if value > high:
        return high
    return value


def clamp_all(values, low, high):
    """Clamp every value in `values` to [low, high], preserving order."""
    return [clamp(v, low, high) for v in values]
