"""Structured locality input for policy recommendations."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class FullLocalityInput:
    locality_name: str
    state_name: str
    state_fips: str
    county_fips: str
    governance_form: str
    hud_fips: Optional[str] = None

    population_estimate: Optional[int] = None
    household_estimate: Optional[int] = None
    avg_annual_population_rate_of_change: Optional[float] = None
    avg_annual_household_rate_of_change: Optional[float] = None
    median_household_income: Optional[int] = None
    total_housing_units: Optional[int] = None
    vacancy_rate: Optional[float] = None
    homeownership_rate: Optional[float] = None
    pct_single_family_detached: Optional[float] = None
    pct_single_family_attached: Optional[float] = None
    pct_multifamily_2_4: Optional[float] = None
    pct_multifamily_5plus: Optional[float] = None
    pct_mobile_home: Optional[float] = None
    pct_built_post_2000: Optional[float] = None
    pct_built_1980_1999: Optional[float] = None
    pct_built_pre_1980: Optional[float] = None
    pct_built_pre_1940: Optional[float] = None
    pct_built_1940_1959: Optional[float] = None
    pct_built_1960_1979: Optional[float] = None
    pct_built_since_1980: Optional[float] = None
    median_gross_rent: Optional[int] = None
    cost_burden_rate: Optional[float] = None

    fmr_0br: Optional[int] = None
    fmr_1br: Optional[int] = None
    fmr_2br: Optional[int] = None
    fmr_3br: Optional[int] = None
    fmr_4br: Optional[int] = None
    ami_30pct: Optional[int] = None
    ami_50pct: Optional[int] = None
    ami_80pct: Optional[int] = None
    ami_100pct: Optional[int] = None

    unemployment_rate: Optional[float] = None
    employment_level: Optional[int] = None
    labor_force: Optional[int] = None
    workers_per_household: Optional[float] = None
    population_density: Optional[float] = None

    # Mel-style 4-bucket summary from ACS year-built shares (see locality_profile)
    building_age_profile: Optional[Dict[str, Any]] = field(default=None)

    wage_median: Optional[float] = None
    wage_pct25: Optional[float] = None
    wage_pct75: Optional[float] = None

    housing_dept_present: Optional[bool] = None
    building_permits_annual: Optional[int] = None
