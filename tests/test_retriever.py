"""Tests for rag/retriever.py — patches chromadb client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from housing_policy_advisor.models.locality_input import FullLocalityInput


def _make_query_result(ids, docs, metas, dists):
    return {
        "ids": [ids],
        "documents": [docs],
        "metadatas": [metas],
        "distances": [dists],
    }


def _named(name: str):
    """Return a simple object with .name attribute (avoids MagicMock name= conflict)."""
    obj = MagicMock()
    obj.name = name
    return obj


def _locality(**overrides):
    values = {
        "locality_name": "Test County",
        "state_name": "Virginia",
        "state_fips": "51",
        "county_fips": "001",
        "governance_form": "county",
        "population_estimate": 80_000,
        "median_household_income": 60_000,
        "cost_burden_rate": 0.30,
        "homeownership_rate": 0.60,
        "vacancy_rate": 0.05,
        "pct_built_pre_1980": 0.30,
        "building_permits_annual": 250,
    }
    values.update(overrides)
    return FullLocalityInput(**values)


@patch("housing_policy_advisor.rag.retriever._persistent_client")
@patch("housing_policy_advisor.rag.retriever._embedding_function")
def test_retrieve_chunks_returns_flat_list(mock_ef, mock_client):
    collection = MagicMock()
    collection.query.return_value = _make_query_result(
        ids=["id1", "id2"],
        docs=["text one", "text two"],
        metas=[{"source": "a.pdf"}, {"source": "b.pdf"}],
        dists=[0.1, 0.3],
    )
    mock_client.return_value.list_collections.return_value = [_named("housing_policy_chunks")]
    mock_client.return_value.get_collection.return_value = collection
    mock_ef.return_value = MagicMock()

    from housing_policy_advisor.rag.retriever import retrieve_chunks
    results = retrieve_chunks("affordable housing zoning")

    assert len(results) == 2
    assert results[0]["id"] == "id1"
    assert results[0]["text"] == "text one"
    assert results[0]["distance"] == pytest.approx(0.1)


@patch("housing_policy_advisor.rag.retriever._persistent_client")
@patch("housing_policy_advisor.rag.retriever._embedding_function")
def test_retrieve_chunks_missing_collection_raises(mock_ef, mock_client):
    mock_client.return_value.list_collections.return_value = []  # no collections
    mock_ef.return_value = MagicMock()

    from housing_policy_advisor.rag.retriever import retrieve_chunks
    with pytest.raises(RuntimeError, match="not found"):
        retrieve_chunks("some query")


@patch("housing_policy_advisor.rag.retriever._persistent_client")
@patch("housing_policy_advisor.rag.retriever._embedding_function")
def test_retrieve_empty_query_returns_empty(mock_ef, mock_client):
    from housing_policy_advisor.rag.retriever import retrieve_chunks
    results = retrieve_chunks("   ")
    assert results == []
    mock_client.assert_not_called()


@patch("housing_policy_advisor.rag.retriever._persistent_client")
@patch("housing_policy_advisor.rag.retriever._embedding_function")
def test_retrieve_texts_only(mock_ef, mock_client):
    collection = MagicMock()
    collection.query.return_value = _make_query_result(
        ids=["id1"],
        docs=["policy text"],
        metas=[{}],
        dists=[0.2],
    )
    mock_client.return_value.list_collections.return_value = [_named("housing_policy_chunks")]
    mock_client.return_value.get_collection.return_value = collection

    from housing_policy_advisor.rag.retriever import retrieve
    texts = retrieve("housing policy")
    assert texts == ["policy text"]


def test_compute_locality_tags_strict_thresholds():
    from housing_policy_advisor.rag.retriever import _compute_locality_tags

    boundary = _locality(cost_burden_rate=0.42, building_permits_annual=None)
    tags = _compute_locality_tags(boundary, "COLLEGE_TOWN")
    assert "high_burden" not in tags
    assert "low_supply" in tags

    above = _locality(cost_burden_rate=0.43, building_permits_annual=501)
    tags = _compute_locality_tags(above, "COLLEGE_TOWN")
    assert "high_burden" in tags
    assert "rapid_growth" in tags
    assert "low_supply" not in tags


def test_select_queries_differentiates_college_towns_by_metrics():
    from housing_policy_advisor.rag.retriever import _select_queries

    high_burden = _locality(
        cost_burden_rate=0.48,
        homeownership_rate=0.40,
        building_permits_annual=75,
    )
    moderate_burden = _locality(
        cost_burden_rate=0.30,
        homeownership_rate=0.55,
        building_permits_annual=400,
    )

    assert _select_queries("COLLEGE_TOWN", high_burden) != _select_queries("COLLEGE_TOWN", moderate_burden)


def test_select_queries_differentiates_rural_low_income_by_supply():
    from housing_policy_advisor.rag.retriever import _select_queries

    supply_constrained = _locality(
        population_estimate=30_000,
        median_household_income=40_000,
        building_permits_annual=None,
    )
    steady_supply = _locality(
        population_estimate=30_000,
        median_household_income=40_000,
        building_permits_annual=400,
    )

    assert _select_queries("RURAL_LOW_INCOME", supply_constrained) != _select_queries("RURAL_LOW_INCOME", steady_supply)


def test_queries_for_profile_keeps_universal_queries_and_removes_numeric_suffix():
    from housing_policy_advisor.rag.retriever import UNIVERSAL_POLICY_QUERIES, _queries_for_profile

    queries = _queries_for_profile(
        "COLLEGE_TOWN",
        _locality(cost_burden_rate=0.48, homeownership_rate=0.40, building_permits_annual=75),
    )

    assert queries[: len(UNIVERSAL_POLICY_QUERIES)] == UNIVERSAL_POLICY_QUERIES
    assert len(queries) == len(UNIVERSAL_POLICY_QUERIES) + 7
    assert not any("median income" in query or "cost burden 48" in query for query in queries)
