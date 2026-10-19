"""Shared domain types and utilities for GlobalHeadsOrTails."""

from shared.models import TagKeys, mask_key
from shared.outcome import Outcome
from shared.uid import UID

__all__ = [
    "Outcome",
    "TagKeys",
    "UID",
    "mask_key",
]
