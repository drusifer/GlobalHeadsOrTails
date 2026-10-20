"""Pytest configuration and shared fixtures.

This file is auto-discovered by pytest and runs before any tests.
"""

import sys
from pathlib import Path

# Add tests directory to sys.path so tests can import mock_hal, trace_based_simulator, etc.
_tests_dir = str(Path(__file__).parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

import pytest

from sdm_provisioner.sequence_logger import SequenceLogger, create_sequence_logger


# ============================================================================
# GUARD: Prevent package shadowing
# ============================================================================
# If someone creates tests/sdm_provisioner/, it shadows the real package
# and breaks ALL imports. This guard fails fast with a clear error message.

_bad_path = Path(__file__).parent / "sdm_provisioner"
if _bad_path.is_dir():
    raise ImportError(
        f"\n{'='*70}\n"
        f"FATAL: {_bad_path} exists!\n"
        f"{'='*70}\n"
        f"This directory shadows the real package and breaks all imports.\n\n"
        f"TO FIX:\n"
        f"  1. Move test utilities (mock_hal.py, etc.) to tests/ root\n"
        f"  2. Move test_*.py files to tests/ root\n"
        f"  3. DELETE the tests/sdm_provisioner/ folder\n"
        f"  4. Fix imports to use: from sdm_provisioner.x import Y\n"
        f"{'='*70}\n"
    )


# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def factory_key() -> bytes:
    """Default factory key (all zeros)."""
    return bytes(16)


@pytest.fixture
def test_uid() -> bytes:
    """Standard test UID for simulator."""
    return bytes.fromhex("04234567890ABC0")


@pytest.fixture
def sequence_logger() -> SequenceLogger:
    """Shared sequence logger for tests."""
    return create_sequence_logger("Test")
