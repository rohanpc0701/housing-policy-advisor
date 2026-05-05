"""Policy class constants for the classifier prototype."""

from __future__ import annotations

from typing import Literal

PolicyClass = Literal["density_bonus", "adu", "affordable_dwelling_unit"]

DENSITY_BONUS: PolicyClass = "density_bonus"
ADU: PolicyClass = "adu"
AFFORDABLE_DWELLING_UNIT: PolicyClass = "affordable_dwelling_unit"

SUPPORTED_POLICY_CLASSES: tuple[PolicyClass, ...] = (
    DENSITY_BONUS,
    ADU,
    AFFORDABLE_DWELLING_UNIT,
)

CLASSIFIER_INGEST_VERSION = "classifier_v1"


def validate_policy_class(policy_class: str) -> PolicyClass:
    """Return a supported policy class or raise a clear validation error."""
    if policy_class not in SUPPORTED_POLICY_CLASSES:
        allowed = ", ".join(SUPPORTED_POLICY_CLASSES)
        raise ValueError(f"Unsupported policy_class {policy_class!r}. Expected one of: {allowed}")
    return policy_class  # type: ignore[return-value]
