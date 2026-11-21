#!/usr/bin/env python3
"""Generate a tooling timeline from public repo metadata.

Groups every non-fork public repo by the quarter it was created, so the
README can show "what was I building, in what language, when" without
depending on memory.

Usage:
    python3 scripts/tooling_timeline.py            # markdown table
    python3 scripts/tooling_timeline.py --json     # raw rows
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict

FIELDS = (
    "name,createdAt,pushedAt,primaryLanguage,isFork,description,"
    "stargazerCount,visibility"
)


def fetch_repos(user: str) -> list[dict]:
    try:
        proc = subprocess.run(
            ["gh", "repo", "list", user, "--limit", "200", "--json", FIELDS],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise SystemExit("error: gh CLI not found on PATH")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or f"exit {exc.returncode}"
        raise SystemExit(f"error: gh repo list failed: {detail}")

    try:
        repos = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: could not parse gh output: {exc}")
    if not isinstance(repos, list):
        raise SystemExit("error: unexpected gh payload (not a list)")
    return repos


def quarter(iso: str) -> str:
    """Map an ISO timestamp to its quarter label, e.g. 2025-06-01T... -> 2025Q2."""
    try:
        year, month = int(iso[:4]), int(iso[5:7])
    except (TypeError, ValueError):
        raise ValueError(f"not an ISO timestamp: {iso!r}")
    if not 1 <= month <= 12:
        raise ValueError(f"month out of range in {iso!r}")
    return f"{year}Q{(month - 1) // 3 + 1}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="VasantLong")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    # A public README must never name a private repo, and an authenticated
    # gh call sees them too -- so filter on visibility, not on "gh worked".
    repos = [
        r
        for r in fetch_repos(args.user)
        if not r["isFork"] and r.get("visibility") == "PUBLIC"
    ]

    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in repos:
        created = r.get("createdAt")
        if not created:
            continue
        try:
            buckets[quarter(created)].append(r)
        except ValueError as exc:
            print(f"warning: skipping {r.get('name')}: {exc}", file=sys.stderr)

    rows = []
    for q in sorted(buckets):
        items = buckets[q]
        langs: dict[str, int] = defaultdict(int)
        for it in items:
            lang = (it.get("primaryLanguage") or {}).get("name") or "docs/other"
            langs[lang] += 1
        rows.append(
            {
                "quarter": q,
                "count": len(items),
                "languages": ", ".join(
                    f"{k} x{v}" if v > 1 else k
                    for k, v in sorted(langs.items(), key=lambda kv: (-kv[1], kv[0]))
                ),
                "repos": [
                    {
                        "name": it["name"],
                        "language": (it.get("primaryLanguage") or {}).get("name"),
                        "description": it.get("description"),
                        "stars": it.get("stargazerCount", 0),
                    }
                    for it in sorted(items, key=lambda x: x["name"])
                ],
            }
        )

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0

    print("| Quarter | New repos | Languages | Repositories |")
    print("| :---: | :---: | :--- | :--- |")
    for row in rows:
        names = ", ".join(
            f"[{r['name']}](https://github.com/{args.user}/{r['name']})"
            for r in row["repos"]
        )
        print(f"| {row['quarter']} | {row['count']} | {row['languages']} | {names} |")

    print()
    print(f"<!-- {len(repos)} public non-fork repos, generated from gh repo list -->")
    return 0


if __name__ == "__main__":
    sys.exit(main())
