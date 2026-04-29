# Profile Routing: Threshold-Based Query Selection

**Date:** 2026-04-28
**Status:** Approved
**File:** `housing_policy_advisor/rag/retriever.py`

---

## Problem

Two-pass retrieval currently emits all profile queries to every locality in that profile. Two COLLEGE_TOWN localities with different cost-burden rates get identical pass-2 query sets (modulo a numeric suffix the embedding model ignores). Result: same-profile localities converge on the same recommendations.

---

## Solution

Expand each profile's query pool to 12-15 entries. Annotate each query with boolean tags (conditions that make it relevant). Compute locality tags from real metrics. Select the top-N queries by tag-match score.

---

## Tag Definitions

`_compute_locality_tags(locality, profile) -> frozenset[str]`

| Tag | Condition | Field |
|-----|-----------|-------|
| `high_burden` | `cost_burden_rate > 0.42` | `FullLocalityInput.cost_burden_rate` |
| `low_supply` | `building_permits_annual < 100` OR `None` | `FullLocalityInput.building_permits_annual` |
| `rapid_growth` | `building_permits_annual > 500` | `FullLocalityInput.building_permits_annual` |
| `high_vacancy` | `vacancy_rate > 0.08` | `FullLocalityInput.vacancy_rate` |
| `low_homeownership` | `homeownership_rate < 0.45` | `FullLocalityInput.homeownership_rate` |
| `low_income` | `median_household_income < 45_000` | `FullLocalityInput.median_household_income` |
| `high_income` | `median_household_income > 80_000` | `FullLocalityInput.median_household_income` |
| `aging_housing` | `pct_built_pre_1980 > 0.55` | `FullLocalityInput.pct_built_pre_1980` (confirmed non-null in live data) |

Rules:
- All thresholds strictly greater-than / less-than (no `>=` / `<=`)
- Null field → tag silently absent (no exception, no default)
- `low_supply` and `rapid_growth` are mutually exclusive (can't both fire)

---

## Annotated Query Pool Structure

Each profile's query list changes from `List[str]` to `List[tuple[str, frozenset[str]]]`:

```python
# (query_text, tags_that_boost_this_query)
("eviction prevention rental assistance rural", frozenset(["high_burden", "low_income"]))
```

Pool ordering within each profile: multi-tag queries first, single-tag next, zero-tag last. This ensures tie-breaking favors specificity when scores are equal.

Each profile expands from 6-7 to 12-15 annotated entries covering:
- High/low burden variants
- Supply-constrained vs. growth-pressured variants
- Income-stratified program queries
- Aging housing stock vs. new construction contexts

---

## Selector Function

`_select_queries(profile, locality, n=7) -> list[str]`

```
score(query) = sum(1 for tag in query.tags if tag in locality_tags)
```

- Sort descending by score
- Break ties by original pool order (preserves specificity ordering)
- Return top-n query strings (stripped of tag metadata)
- `n=7` matches current effective pool size; callers may override

---

## Integration

`_queries_for_profile(profile, locality)`:
- Replaces: `profile_queries = PROFILE_POLICY_QUERIES.get(profile, ...)` + numeric suffix logic
- With: `profile_queries = _select_queries(profile, locality)`
- Universal 3 queries unchanged and always prepended
- Caller interface (returns `List[str]`) unchanged
- Numeric suffix (`_profile_query_suffix`) removed

`retrieve_chunks()` call path unchanged. `pass_2_k = max(2, k // 4)` unchanged.

---

## What Changes

| | Before | After |
|---|---|---|
| Pool size per profile | 6-7 queries | 12-15 queries |
| Selection logic | return all | top-7 by tag-match score |
| Numeric suffix | appended to all queries | removed |
| Same-profile differentiation | near-zero (numbers ignored) | meaningful (different query mixes) |

---

## Tests

**New unit tests (retriever):**
1. Two COLLEGE_TOWN localities — one `cost_burden_rate=0.48`, one `cost_burden_rate=0.30` — must return different query subsets from `_select_queries`
2. Two RURAL_LOW_INCOME localities — one `building_permits_annual=None`, one `building_permits_annual=400` — must return different query subsets

**Tag computation tests:**
- `cost_burden_rate=None` → `high_burden` not in tags
- `building_permits_annual=None` → `low_supply` in tags
- `cost_burden_rate=0.42` → `high_burden` NOT in tags (strictly `>`)
- `cost_burden_rate=0.43` → `high_burden` in tags

**Regression:**
- All 4 existing validation localities must still pass with `grounding=1.0`
- `pytest` suite must stay at ≥ 85 passed

---

## Constraints

- Profile taxonomy (6 profiles) unchanged
- ChromaDB schema unchanged
- `k=20` pipeline default unchanged
- `pass_2_k = max(2, k // 4)` formula unchanged
- No new external dependencies
