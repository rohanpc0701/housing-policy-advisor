"""CLI for Housing Policy Advisor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from housing_policy_advisor.pipeline import run_full


def _bool_arg(s: str) -> bool:
    return s.lower() in ("1", "true", "yes", "y", "t")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Housing Policy Advisor")
    p.add_argument("--locality", required=True, help='e.g. "Montgomery County"')
    p.add_argument("--state", required=True, help='e.g. "Virginia"')
    p.add_argument("--state-fips", required=True, help="2-digit state FIPS")
    p.add_argument("--county-fips", required=True, help="3-digit county FIPS")
    p.add_argument("--hud-fips", default=None, help="10-digit HUD FIPS override, e.g. 5112199999")
    p.add_argument("--governance-form", required=True, help='e.g. "County"')
    p.add_argument("--state-abbr", default="va")
    p.add_argument("--housing-dept-present", default=None, help="true/false")
    p.add_argument("--building-permits-annual", type=int, default=None)
    p.add_argument("--retrieval-k", type=int, default=8)
    p.add_argument("--format", choices=("json", "pdf", "docx", "all"), default="json")
    p.add_argument("--out-dir", type=Path, default=Path("."))
    args = p.parse_args(argv)

    dept_present = _bool_arg(args.housing_dept_present) if args.housing_dept_present is not None else None
    paths = run_full(
        locality_name=args.locality,
        state_name=args.state,
        state_fips=args.state_fips,
        county_fips=args.county_fips,
        governance_form=args.governance_form,
        state_abbr=args.state_abbr,
        hud_fips=args.hud_fips,
        housing_dept_present=dept_present,
        building_permits_annual=args.building_permits_annual,
        retrieval_k=args.retrieval_k,
        out_dir=args.out_dir,
        output_format=args.format,
    )
    for path in paths:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
