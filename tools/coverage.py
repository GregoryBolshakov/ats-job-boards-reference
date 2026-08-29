#!/usr/bin/env python3
"""
Recomputes the coverage tables in README.md from the snapshot.

Nothing in the README is typed by hand, because a hand-typed percentage goes stale the
first time the data is refreshed and nobody notices. Run this after replacing the
snapshot, paste the output between the marker comments.

    python3 tools/coverage.py data/jobs-2026-08-29.json
"""
import collections
import json
import sys

FIELDS = [
    "company", "title", "location", "department", "employmentType",
    "postedAt", "updatedAt", "applyUrl", "salaryMin", "salaryRaw",
]
PLATFORMS = ["greenhouse", "lever", "ashby", "smartrecruiters"]


def pct(n, d):
    return f"{100.0 * n / d:.0f}%" if d else "n/a"


def main(path):
    rows = json.load(open(path))
    by_platform = collections.defaultdict(list)
    for r in rows:
        by_platform[r["platform"]].append(r)

    print(f"Total adverts: {len(rows):,}\n")
    print("## Which fields each board actually fills in\n")
    header = " | ".join(f"{p} ({len(by_platform[p]):,})" for p in PLATFORMS)
    print(f"| field | {header} |")
    print("|---|" + "---|" * len(PLATFORMS))
    for f in FIELDS:
        cells = []
        for p in PLATFORMS:
            group = by_platform[p]
            filled = sum(1 for r in group if r.get(f) not in (None, ""))
            cells.append(pct(filled, len(group)))
        print(f"| `{f}` | " + " | ".join(cells) + " |")

    print("\n## Declared pay, per company\n")
    print("| board | company | adverts | with pay |")
    print("|---|---|---|---|")
    counts = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        key = (r["platform"], r["companySlug"])
        counts[key][1] += 1
        if r.get("salaryMin") is not None:
            counts[key][0] += 1
    for (plat, slug), (with_pay, total) in sorted(counts.items(), key=lambda x: -x[1][1]):
        print(f"| {plat} | {slug} | {total:,} | {pct(with_pay, total)} |")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/jobs-2026-08-29.json")
