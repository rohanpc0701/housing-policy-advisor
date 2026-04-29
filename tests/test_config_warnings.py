from __future__ import annotations

import importlib
import logging

from housing_policy_advisor import config


def test_validate_optional_api_keys_warns_when_both_missing(caplog):
    with caplog.at_level(logging.WARNING, logger="housing_policy_advisor.config"):
        config.validate_optional_api_keys(hud_api_key="", bls_api_key="")

    messages = [r.message for r in caplog.records]
    assert any("Missing HUD API key" in m for m in messages)
    assert any("Missing BLS API key" in m for m in messages)


def test_validate_optional_api_keys_warns_for_individual_missing(caplog):
    with caplog.at_level(logging.WARNING, logger="housing_policy_advisor.config"):
        config.validate_optional_api_keys(hud_api_key="hud-ok", bls_api_key="")

    messages = [r.message for r in caplog.records]
    assert not any("Missing HUD API key" in m for m in messages)
    assert any("Missing BLS API key" in m for m in messages)


def test_importing_config_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING, logger="housing_policy_advisor.config"):
        importlib.reload(config)

    messages = [r.message for r in caplog.records]
    assert not any("Missing HUD API key" in m for m in messages)
    assert not any("Missing BLS API key" in m for m in messages)
