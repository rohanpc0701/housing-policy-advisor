"""CLI for Housing Policy Advisor — locality input and policy recommendation JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from housing_policy_advisor.pipeline import run_full


def _bool_arg(s: str) -> bool:
    return s.lower() in ("1", "true", "yes", "y", "t")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Housing Policy Advisor — fetch data and policy JSON")
    p.add_argument("--locality", required=True, help='e.g. "Montgomery County"')
    p.add_argument("--state", required=True, help='e.g. "Virginia"')
    p.add_argument("--state-fips", required=True, help="2-digit state FIPS")
    p.add_argument("--county-fips", required=True, help="3-digit county FIPS")
    p.add_argument(
        "--governance-form",
        default="county",
        choices=("county", "city", "town", "independent city"),
    )
    p.add_argument("--state-abbr", default="va", help="For output filename slug, e.g. va")
    p.add_argument("--has-housing-dept", default=None, help="true/false")
    p.add_argument("--housing-dept-name", default=None)
    p.add_argument("--building-permits-trend", default=None, choices=("increasing", "decreasing", "stable"))
    p.add_argument("--building-permits-annual", type=int, default=None)
    p.add_argument(
        "--input-only",
        action="store_true",
        help="Only write locality_profile_{slug}.json (no mock recommendations)",
    )
    p.add_argument("--out-dir", type=Path, default=Path("."), help="Output directory")

    args = p.parse_args(argv)

    has_dept: bool | None = None
    if args.has_housing_dept is not None:
        has_dept = _bool_arg(args.has_housing_dept)

    paths = run_full(
        locality_name=args.locality,
        state_name=args.state,
        state_fips=args.state_fips,
        county_fips=args.county_fips,
        governance_form=args.governance_form,
        state_abbr=args.state_abbr,
        has_housing_dept=has_dept,
        housing_dept_name=args.housing_dept_name,
        building_permits_trend=args.building_permits_trend,
        building_permits_annual=args.building_permits_annual,
        input_only=args.input_only,
        out_dir=args.out_dir,
    )
    for path in paths:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
