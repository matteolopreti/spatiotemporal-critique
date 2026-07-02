"""csv_summary — group a CSV by one column and summarize a numeric column.

Input is CSV text already in memory; this module reads no files. Rows are
grouped by `group_field`, `value_field` is summed per group, and the report
carries per-group counts, totals, and each group's percentage of the grand
total.

Explicit edge handling:
- Text with no header row, or with no data rows, yields an empty report.
- A data row whose group value is absent or blank lands in the
  MISSING_GROUP bucket (a literal group equal to MISSING_GROUP shares it).
- A data row whose numeric value is absent, blank, unparseable, non-finite,
  or negative raises ValueError naming the 1-based data row.
- When the grand total is 0 (every value is 0), every percentage is 0.0.
"""
import csv
import io
import math

MISSING_GROUP = "(missing)"


def summarize(csv_text, group_field, value_field):
    """Return {"groups": [...], "grand_total": float, "row_count": int}.

    Each entry of "groups" is {"group", "count", "total", "percent"};
    entries are sorted by total descending, then group name ascending.
    Values must be finite and non-negative so the percentages are
    meaningful; percentages are left unrounded here (format_report rounds).
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        return {"groups": [], "grand_total": 0.0, "row_count": 0}
    for field in (group_field, value_field):
        if field not in reader.fieldnames:
            raise ValueError(f"column {field!r} not in header {reader.fieldnames}")

    totals = {}
    counts = {}
    row_count = 0
    for row_num, row in enumerate(reader, start=1):
        row_count += 1
        group = row.get(group_field)
        if group is None or group.strip() == "":
            group = MISSING_GROUP
        raw = row.get(value_field)
        if raw is None or raw.strip() == "":
            raise ValueError(
                f"data row {row_num}: missing value for {value_field!r}"
            )
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(
                f"data row {row_num}: cannot parse {raw!r} as a number"
            ) from exc
        if not (math.isfinite(value) and value >= 0.0):
            raise ValueError(
                f"data row {row_num}: value must be finite and >= 0, got {raw!r}"
            )
        totals[group] = totals.get(group, 0.0) + value
        counts[group] = counts.get(group, 0) + 1

    grand_total = sum(totals.values(), 0.0)  # 0.0 start: float even when empty
    groups = []
    for group, total in totals.items():
        percent = (total / grand_total * 100.0) if grand_total > 0 else 0.0
        groups.append({"group": group, "count": counts[group],
                       "total": total, "percent": percent})
    groups.sort(key=lambda g: (-g["total"], g["group"]))
    return {"groups": groups, "grand_total": grand_total, "row_count": row_count}


def format_report(report, group_header="group"):
    """Render a summarize() report as CSV-style text lines.

    One header line, one line per group (percent rounded to one decimal),
    and a TOTAL line. The TOTAL percent is 100.0 when the grand total is
    positive, else 0.0. Rounded group percents may not sum to exactly 100.
    """
    lines = [f"{group_header},count,total,percent"]
    for g in report["groups"]:
        lines.append(
            f"{g['group']},{g['count']},{g['total']:g},{g['percent']:.1f}%"
        )
    total_pct = 100.0 if report["grand_total"] > 0 else 0.0
    lines.append(
        f"TOTAL,{report['row_count']},{report['grand_total']:g},{total_pct:.1f}%"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    text = (
        "region,amount\n"
        "east,50\n"
        "west,25\n"
        "east,25\n"
    )
    rep = summarize(text, "region", "amount")
    assert rep["row_count"] == 3
    assert rep["grand_total"] == 100.0
    assert rep["groups"] == [
        {"group": "east", "count": 2, "total": 75.0, "percent": 75.0},
        {"group": "west", "count": 1, "total": 25.0, "percent": 25.0},
    ]
    assert format_report(rep, group_header="region") == (
        "region,count,total,percent\n"
        "east,2,75,75.0%\n"
        "west,1,25,25.0%\n"
        "TOTAL,3,100,100.0%"
    )

    # Ties on total sort alphabetically by group name.
    rep = summarize("k,v\nb,10\na,10\n", "k", "v")
    assert [g["group"] for g in rep["groups"]] == ["a", "b"]

    # Blank group values land in the MISSING_GROUP bucket.
    rep = summarize("k,v\n,4\nx,6\n", "k", "v")
    assert rep["groups"][0] == {"group": "x", "count": 1, "total": 6.0,
                                "percent": 60.0}
    assert rep["groups"][1]["group"] == MISSING_GROUP
    assert rep["groups"][1]["percent"] == 40.0

    # Empty input and header-only input yield empty reports.
    assert summarize("", "k", "v") == {"groups": [], "grand_total": 0.0,
                                       "row_count": 0}
    rep = summarize("k,v\n", "k", "v")
    assert rep["groups"] == [] and rep["row_count"] == 0

    # All-zero values: grand total 0, every percent 0.0.
    rep = summarize("k,v\na,0\nb,0\n", "k", "v")
    assert rep["grand_total"] == 0.0
    assert all(g["percent"] == 0.0 for g in rep["groups"])
    assert format_report(rep).endswith("TOTAL,2,0,0.0%")

    def expect_error(csv_text, group_field="k", value_field="v"):
        try:
            summarize(csv_text, group_field, value_field)
        except ValueError:
            return
        raise AssertionError(f"expected ValueError for {csv_text!r}")

    expect_error("k,v\na,1\n", group_field="nope")  # group column absent
    expect_error("k,v\na,1\n", value_field="nope")  # value column absent
    expect_error("k,v\na\n")                        # short row: value missing
    expect_error("k,v\na,\n")                       # blank value
    expect_error("k,v\na,cheap\n")                  # unparseable value
    expect_error("k,v\na,nan\n")                    # non-finite value
    expect_error("k,v\na,-5\n")                     # negative value

    print("OK")
