"""HUD income limits parsing (documented nested shape)."""

from housing_policy_advisor.data.clients.hud_client import parse_income_limits_payload


def test_parse_il_nested_extremely_very_low_low():
    payload = {
        "median_income": 65900,
        "extremely_low": {"il30_p4": 31000},
        "very_low": {"il50_p4": 33000},
        "low": {"il80_p4": 52000},
    }
    out = parse_income_limits_payload(payload)
    assert out["ami_100pct"] == 65900
    assert out["ami_30pct"] == 31000
    assert out["ami_50pct"] == 33000
    assert out["ami_80pct"] == 52000


def test_parse_il_flat_fallback():
    payload = {
        "median_income": "70000",
        "il30_p4": 21000,
        "il50_p4": 35000,
        "il80_p4": 56000,
    }
    out = parse_income_limits_payload(payload)
    assert out["ami_100pct"] == 70000
    assert out["ami_30pct"] == 21000
