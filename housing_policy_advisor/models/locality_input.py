"""Structured locality input for policy modeling."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FullLocalityInput:
    # Identity (manual)
    locality_name: str
    state_name: str
    state_fips: str
    county_fips: str
    governance_form: str  # "county" | "city" | "town" | "independent city"

    # Population — Census ACS B01003
    population_estimate: Optional[int] = None
    avg_annual_population_rate_of_change: Optional[float] = None

    # Households — Census ACS B11001
    household_estimate: Optional[int] = None
    avg_annual_household_rate_of_change: Optional[float] = None

    # Employment — BLS LAUS
    regional_employment_estimate: Optional[int] = None
    unemployment_rate: Optional[float] = None

    # Housing stock — Census ACS B25002, B25003, B25024, B25034
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

    # Building permits (manual + Census BPS)
    building_permits_trend: Optional[str] = None  # "increasing"|"decreasing"|"stable"
    building_permits_annual: Optional[int] = None

    # Affordability — Census ACS B19013, B25064, B25070
    median_household_income: Optional[int] = None
    median_gross_rent: Optional[int] = None
    cost_burden_rate: Optional[float] = None  # % paying >30% income on rent

    # HUD data
    area_median_income: Optional[int] = None
    fmr_1br: Optional[int] = None
    fmr_2br: Optional[int] = None
    fmr_3br: Optional[int] = None
    il_30pct_ami_4person: Optional[int] = None
    il_50pct_ami_4person: Optional[int] = None
    il_80pct_ami_4person: Optional[int] = None

    # Local capacity (manual)
    has_housing_dept: Optional[bool] = None
    housing_dept_name: Optional[str] = None
