"""Tests for pipeline.py — slugify, JSON write, output paths."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from housing_policy_advisor.pipeline import slugify_locality, to_json_tree, run_full


def test_slugify_basic():
    assert slugify_locality("Montgomery County", "va") == "montgomery_county_va"


def test_slugify_special_chars():
    assert slugify_locality("St. Louis", "MO") == "st__louis_mo"


def test_slugify_lowercase():
    result = slugify_locality("FAIRFAX", "VA")
    assert result == result.lower()


def test_to_json_tree_dict():
    assert to_json_tree({"a": 1}) == {"a": 1}


def test_to_json_tree_nested():
    result = to_json_tree({"a": [1, 2], "b": {"c": 3}})
    assert result == {"a": [1, 2], "b": {"c": 3}}


def test_to_json_tree_dataclass(mock_locality):
    tree = to_json_tree(mock_locality)
    assert isinstance(tree, dict)
    assert tree["locality_name"] == "Test County"


def test_run_full_writes_json(tmp_path, mock_locality, sample_policy_result):
    with patch("housing_policy_advisor.pipeline.build_locality_profile", return_value=mock_locality), \
         patch("housing_policy_advisor.pipeline.generate_policy_recommendations", return_value=sample_policy_result):
        paths = run_full(
            locality_name="Test County",
            state_name="Virginia",
            state_fips="51",
            county_fips="001",
            governance_form="county",
            state_abbr="va",
            out_dir=tmp_path,
        )

    assert len(paths) >= 1
    json_path = paths[0]
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert "recommendations" in data
    assert "locality_profile" in data


def test_run_full_slug_in_filename(tmp_path, mock_locality, sample_policy_result):
    with patch("housing_policy_advisor.pipeline.build_locality_profile", return_value=mock_locality), \
         patch("housing_policy_advisor.pipeline.generate_policy_recommendations", return_value=sample_policy_result):
        paths = run_full(
            locality_name="Test County",
            state_name="Virginia",
            state_fips="51",
            county_fips="001",
            governance_form="county",
            state_abbr="va",
            out_dir=tmp_path,
        )

    assert "test_county_va" in paths[0].name


def test_run_full_creates_out_dir(tmp_path, mock_locality, sample_policy_result):
    new_dir = tmp_path / "nested" / "output"
    with patch("housing_policy_advisor.pipeline.build_locality_profile", return_value=mock_locality), \
         patch("housing_policy_advisor.pipeline.generate_policy_recommendations", return_value=sample_policy_result):
        run_full(
            locality_name="Test",
            state_name="Virginia",
            state_fips="51",
            county_fips="001",
            governance_form="county",
            state_abbr="va",
            out_dir=new_dir,
        )
    assert new_dir.exists()
