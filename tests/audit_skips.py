#!/usr/bin/env python
"""Fail the build when tests skipped for the wrong reasons.

The dashboard tests here talk to a live service and skip themselves when
nothing is listening on port 8001. That is convenient locally and dangerous in
CI: 134 tests once disappeared from a run while the tick stayed green. This
sorts skip reasons into two piles.

Infrastructure skips are always a failure. They mean the harness did not set
something up, so coverage silently went missing.

Data skips are legitimate. A test that needs an article the reader cannot
extract has nothing to assert when every article extracts cleanly. Those are
allowed, capped, and always printed, so the number cannot creep upward without
somebody noticing.

    python tests/audit_skips.py results.xml [--allow-data-skips N]
"""

import argparse
import sys
import xml.etree.ElementTree as ET

# A skip carrying any of these means the environment was not prepared.
INFRASTRUCTURE_MARKERS = (
    "not running",
    "is missing",
    "not installed",
    "run npm run build",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", help="path to a pytest --junitxml report")
    parser.add_argument(
        "--allow-data-skips",
        type=int,
        default=0,
        help="how many data-dependent skips are acceptable (default 0)",
    )
    args = parser.parse_args()

    root = ET.parse(args.report).getroot()
    suites = root.findall("testsuite") or [root]

    total = failures = errors = 0
    infrastructure: list[tuple[str, str]] = []
    data: list[tuple[str, str]] = []

    for suite in suites:
        total += int(suite.get("tests", 0))
        failures += int(suite.get("failures", 0))
        errors += int(suite.get("errors", 0))
        for case in suite.iter("testcase"):
            for skipped in case.findall("skipped"):
                name = f"{case.get('classname', '')}::{case.get('name', '')}"
                reason = (skipped.get("message") or "").strip()
                bucket = (
                    infrastructure
                    if any(m in reason.lower() for m in INFRASTRUCTURE_MARKERS)
                    else data
                )
                bucket.append((name, reason))

    print(
        f"collected {total}, failures {failures}, errors {errors}, "
        f"skipped {len(infrastructure) + len(data)} "
        f"({len(infrastructure)} infrastructure, {len(data)} data)"
    )

    if data:
        print("\ndata-dependent skips, allowed:")
        for name, reason in data:
            print(f"  - {name}: {reason}")

    problems = []

    if not total:
        problems.append("no tests were collected at all")

    if failures or errors:
        problems.append(f"{failures} failure(s) and {errors} error(s) in the report")

    if infrastructure:
        print("\ninfrastructure skips, NOT allowed:")
        for name, reason in infrastructure:
            print(f"  - {name}: {reason}")
        problems.append(
            f"{len(infrastructure)} test(s) skipped because the environment was "
            f"not set up. Start the service and build the frontend before "
            f"running the suite."
        )

    if len(data) > args.allow_data_skips:
        problems.append(
            f"{len(data)} data-dependent skips exceeds the allowance of "
            f"{args.allow_data_skips}. Either the fixtures stopped producing "
            f"the cases these tests need, or the allowance needs raising on "
            f"purpose."
        )

    if problems:
        print()
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1

    print("\nskip audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
