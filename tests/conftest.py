"""Shared fixtures for Housing Policy Advisor tests."""

from __future__ import annotations

import io
import pytest

from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.models.policy_output import PolicyRecommendation, PolicyRecommendationsResult


@pytest.fixture()
def mock_locality() -> FullLocalityInput:
    return FullLocalityInput(
        locality_name="Test County",
        state_name="Virginia",
        state_fips="51",
        county_fips="001",
        governance_form="county",
        hud_fips="51001",
        population_estimate=100_000,
        household_estimate=40_000,
        median_household_income=65_000,
        total_housing_units=42_000,
        vacancy_rate=0.06,
        homeownership_rate=0.62,
        median_gross_rent=1_200,
        cost_burden_rate=0.31,
        fmr_2br=1_400,
        ami_80pct=62_000,
        unemployment_rate=0.045,
    )


@pytest.fixture()
def sample_recommendation() -> PolicyRecommendation:
    return PolicyRecommendation(
        rank=1,
        policy_name="Inclusionary Zoning",
        predicted_outcome="Increase affordable unit supply by 5%",
        confidence_score=0.75,
        evidence_basis=["HUD study 2021", "Local pilot data"],
        implementation_timeline="2 years",
        resource_requirements="Moderate staff capacity",
        risks=["Developer pushback"],
    )


@pytest.fixture()
def sample_policy_result(sample_recommendation) -> PolicyRecommendationsResult:
    from housing_policy_advisor.llm.output_validator import compute_validation_summary
    from housing_policy_advisor.models.policy_output import ValidationSummary
    summary = compute_validation_summary([sample_recommendation], grounding_score=0.7)
    return PolicyRecommendationsResult(
        locality="Test County",
        generated_date="2026-01-01",
        recommendations=[sample_recommendation],
        validation_summary=summary,
    )


@pytest.fixture()
def fake_acs_response() -> dict:
    return {
        "B01003_001E": "100000",
        "B11001_001E": "40000",
        "B19013_001E": "65000",
        "B25001_001E": "42000",
        "B25002_001E": "42000",
        "B25002_002E": "39500",
        "B25002_003E": "2500",
        "B25003_001E": "39500",
        "B25003_002E": "24500",
        "B25003_003E": "15000",
        "B25024_001E": "42000",
        "B25024_002E": "20000",
        "B25024_003E": "5000",
        "B25024_004E": "3000",
        "B25024_005E": "2000",
        "B25024_006E": "1500",
        "B25024_007E": "1500",
        "B25024_008E": "1000",
        "B25024_009E": "500",
        "B25024_010E": "200",
        "B25034_001E": "42000",
        "B25034_002E": "5000",
        "B25034_003E": "8000",
        "B25034_004E": "7000",
        "B25034_005E": "6000",
        "B25034_006E": "5000",
        "B25034_007E": "4000",
        "B25034_008E": "3000",
        "B25034_009E": "2000",
        "B25034_010E": "1000",
        "B25034_011E": "1000",
        "B25064_001E": "1200",
        "B25070_001E": "15000",
        "B25070_007E": "1500",
        "B25070_008E": "1000",
        "B25070_009E": "800",
        "B25070_010E": "700",
        "B08202_001E": "40000",
        "B08202_002E": "8000",
        "B08202_003E": "18000",
        "B08202_004E": "12000",
        "B08202_005E": "2000",
        "NAME": "Test County, Virginia",
    }


@pytest.fixture()
def minimal_pdf_bytes() -> bytes:
    """Build a minimal valid PDF in memory (no external deps)."""
    content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length 44>>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000347 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
441
%%EOF"""
    return content
