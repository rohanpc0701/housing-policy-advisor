# Candidate Validation Sources

Purpose: staging area for clean candidate documents for the next classifier validation round.

Status: downloaded/review-staged only. These files have not been ingested into ChromaDB.

Do not run ingestion from this folder until sources are reviewed and explicitly selected. Copy approved files into `classifier_docs/<policy_class>/` before targeted ingestion.

## Summary

| File | Proposed class | Fit | Approved for ingest? | Notes |
|---|---|---|---|---|
| `affordable_dwelling_unit/city_fairfax_adu_admin_regulations.pdf` | `affordable_dwelling_unit` | Very high | Pending | Clean City of Fairfax Affordable Dwelling Unit administrative regulations. “ADU” here means Affordable Dwelling Unit, not Accessory Dwelling Unit. |
| `affordable_dwelling_unit/fairfax_county_wdu_admin_guidelines_2025.pdf` | `affordable_dwelling_unit` | High | Pending | Clean Fairfax County Workforce Dwelling Unit policy guidelines. Strong affordability-program evidence, though WDU is not exactly the same label as Affordable Dwelling Unit. |
| `density_bonus/arlington_zoning_ordinance_section_15_5.pdf` | `density_bonus` | Very high | Pending | Arlington zoning ordinance section on affordable dwelling units and increased density/height. Multi-class candidate; should be manually reviewed before ingestion. |
| `density_bonus/local_housing_solutions_density_bonuses.html` | `density_bonus` | Very high | Pending | Local Housing Solutions density bonuses policy page saved as HTML. Good policy definition source, but not currently a PDF. |

## Source URLs

### Affordable Dwelling Unit Candidates

City of Fairfax ADU Administrative Regulations PDF:

https://www.fairfaxva.gov/files/assets/city/v/1/development/documents/zoning/final-administrative-regulations-for-fairfax-city.pdf

Fairfax County 2025 WDU Administrative Policy Guidelines PDF:

https://www.fairfaxcounty.gov/housing/sites/housing/files/Assets/Documents/adu%20resources%20for%20developers/2025/2025%200318%20Final%20Signed%20WDU%20admin%20guidelines.pdf

### Density Bonus Candidates

Arlington Zoning Ordinance Section 15.5 PDF:

https://www.arlingtonva.us/files/sharedassets/public/v/1/commissions/documents/housing-commission/aczo-15.5.pdf

Local Housing Solutions Density Bonuses page:

https://www.localhousingsolutions.org/housing-policy-library/density-bonuses/

## Review Notes

- The City of Fairfax PDF is the cleanest immediate source for the `affordable_dwelling_unit` class.
- The Fairfax County WDU PDF is a strong local affordability-program source, but should be labeled carefully because WDU means Workforce Dwelling Unit.
- The Arlington Section 15.5 PDF is useful for `density_bonus`, but it also contains affordable dwelling unit material. If used, it may require section-level review or explicit multi-class handling.
- The Local Housing Solutions source is likely the cleanest density bonus definition source, but it was saved as HTML. If the ingestion workflow remains PDF-focused, export this page to PDF before ingestion.

## Recommended Advisor Ask

Ask Dr. Zhang to confirm whether these four sources are acceptable for the next validation round:

1. City of Fairfax ADU Administrative Regulations for `affordable_dwelling_unit`.
2. Fairfax County WDU Guidelines for `affordable_dwelling_unit`.
3. Local Housing Solutions Density Bonuses for `density_bonus`.
4. Arlington Zoning Ordinance Section 15.5 for `density_bonus`, with a multi-class caveat.

