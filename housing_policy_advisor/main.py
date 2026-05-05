"""CLI for Housing Policy Advisor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from housing_policy_advisor import config
from housing_policy_advisor.classifier import classify_policy_query
from housing_policy_advisor.formatting import format_classifier_narrative, format_classifier_table
from housing_policy_advisor.pipeline import run_full


def _bool_arg(s: str) -> bool:
    return s.lower() in ("1", "true", "yes", "y", "t")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Housing Policy Advisor")
    p.add_argument("--locality", help='Required for recommendation mode. e.g. "Montgomery County"')
    p.add_argument("--state", help='Required for recommendation mode. e.g. "Virginia"')
    p.add_argument("--state-fips", help="Required for recommendation mode. 2-digit state FIPS")
    p.add_argument("--county-fips", help="Required for recommendation mode. 3-digit county FIPS")
    p.add_argument(
        "--hud-fips",
        default=None,
        help="Optional for recommendation mode. 10-digit HUD FIPS override, e.g. 5112199999",
    )
    p.add_argument("--governance-form", help='Required for recommendation mode. e.g. "County"')
    p.add_argument("--state-abbr", default="va")
    p.add_argument("--housing-dept-present", default=None, help="true/false")
    p.add_argument("--building-permits-annual", type=int, default=None)
    p.add_argument("--retrieval-k", type=int, default=15)
    p.add_argument("--format", choices=("json", "table", "narrative"), default="json")
    p.add_argument("--classify-query", default=None, help="Run the 3-class classifier prototype on this query")
    p.add_argument(
        "--policy-class",
        choices=("density_bonus", "adu", "affordable_dwelling_unit"),
        default=None,
        help="Optional classifier metadata filter",
    )
    p.add_argument("--out-dir", type=Path, default=Path("."))
    args = p.parse_args(argv)

    if args.classify_query:
        result = classify_policy_query(
            args.classify_query,
            policy_class=args.policy_class,
            k=args.retrieval_k,
        )
        if args.format == "table":
            print(format_classifier_table(result))
        elif args.format == "narrative":
            print(format_classifier_narrative(result))
        else:
            print(json.dumps(result, default=lambda obj: obj.__dict__, indent=2))
        return 0

    config.validate_optional_api_keys()

    required = {
        "--locality": args.locality,
        "--state": args.state,
        "--state-fips": args.state_fips,
        "--county-fips": args.county_fips,
        "--governance-form": args.governance_form,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        p.error(f"recommendation mode requires: {', '.join(missing)}")

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
        output_format=args.format,
        out_dir=args.out_dir,
    )
    for path in paths:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
