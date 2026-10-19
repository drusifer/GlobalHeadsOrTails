"""Outcome enumeration for coin sides."""

from __future__ import annotations

from enum import StrEnum


class Outcome(StrEnum):
    """Represents coin side outcome."""

    HEADS = "heads"
    TAILS = "tails"
    INVALID = "invalid"

    @classmethod
    def _missing_(cls, _value: object) -> Outcome:
        return Outcome.INVALID
