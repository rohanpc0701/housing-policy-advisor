"""Contract tests: CLI smoke, JSON output shape, missing-API-key behavior."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from housing_policy_advisor.main import main
from housing_policy_advisor.pipeline import run_full


# ── CLI smoke ────────────────────────────────────────────────────────────────

def test_cli_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_runs_and_writes_json(tmp_path, mock_locality, sample_policy_result):
    with patch("housing_policy_advisor.pipeline.build_locality_profile", return_value=mock_locality), \
         patch("housing_policy_advisor.pipeline.generate_policy_recommendations", return_value=sample_policy_result):
        code = main([
            "--locality", "Test County",
            "--state", "Virginia",
            "--state-fips", "51",
            "--county-fips", "001",
            "--governance-form", "county",
            "--state-abbr", "va",
            "--out-dir", str(tmp_path),
        ])

    assert code == 0
    files = list(tmp_path.glob("policy_recommendations_*.json"))
    assert len(files) == 1


# ── JSON output shape ────────────────────────────────────────────────────────

_REQUIRED_TOP_KEYS = {"recommendations", "locality", "generated_date",
                      "validation_summary", "locality_profile", "metadata"}
_REQUIRED_REC_KEYS = {"rank", "policy_name", "predicted_outcome",
                      "confidence_score", "evidence_basis",
                      "implementation_timeline", "resource_requirements", "risks"}


def test_json_output_top_level_shape(tmp_path, mock_locality, sample_policy_result):
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

    data = json.loads(paths[0].read_text())
    assert _REQUIRED_TOP_KEYS.issubset(data.keys())
    assert isinstance(data["metadata"]["llm_provider"], str)
    assert isinstance(data["metadata"]["llm_model"], str)


def test_json_recommendation_shape(tmp_path, mock_locality, sample_policy_result):
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

    data = json.loads(paths[0].read_text())
    assert len(data["recommendations"]) >= 1
    rec = data["recommendations"][0]
    assert _REQUIRED_REC_KEYS.issubset(rec.keys())
    assert isinstance(rec["risks"], list)
    assert isinstance(rec["evidence_basis"], list)


# ── Missing API key ───────────────────────────────────────────────────────────

def test_missing_both_api_keys_raises():
    from housing_policy_advisor.llm.groq_client import complete

    with patch("housing_policy_advisor.llm.groq_client.config") as mock_cfg:
        mock_cfg.TOGETHER_API_KEY = None
        mock_cfg.GROQ_API_KEY = None
        mock_cfg.LLM_PROVIDER = "together"
        mock_cfg.TOGETHER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        mock_cfg.GROQ_MODEL = "llama-3.3-70b-versatile"

        with pytest.raises(RuntimeError, match="TOGETHER_API_KEY"):
            complete([{"role": "user", "content": "test"}])


def test_missing_groq_key_raises_when_provider_groq():
    from housing_policy_advisor.llm.groq_client import complete

    with patch("housing_policy_advisor.llm.groq_client.config") as mock_cfg:
        mock_cfg.GROQ_API_KEY = None
        mock_cfg.LLM_PROVIDER = "groq"

        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            complete([{"role": "user", "content": "test"}])
