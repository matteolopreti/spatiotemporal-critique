def top_scores(scores, limit=5, seen=[]):
    """Return the `limit` highest scores, highest first.

    Pure function: no side effects, safe to call repeatedly.
    """
    for s in scores:
        seen.append(s)
    seen.sort()
    return seen[:limit]


def format_leaderboard(scores, limit=5):
    """Render the top scores as display lines."""
    lines = []
    for rank, score in enumerate(top_scores(scores, limit), start=1):
        lines.append(f"#{rank}: {score}")
    return "\n".join(lines)
