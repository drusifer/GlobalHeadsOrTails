"""
Pytest configuration and shared fixtures.

This file is auto-discovered by pytest and runs before any tests.
"""
import os
import sys

# ============================================================================
# GUARD: Prevent package shadowing
# ============================================================================
# If someone creates tests/ntag424_sdm_provisioner/, it shadows the real package
# and breaks ALL imports. This guard fails fast with a clear error message.

_bad_path = os.path.join(os.path.dirname(__file__), "ntag424_sdm_provisioner")
if os.path.isdir(_bad_path):
    raise ImportError(
        f"\n{'='*70}\n"
        f"FATAL: {_bad_path} exists!\n"
        f"{'='*70}\n"
        f"This directory shadows the real package and breaks all imports.\n\n"
        f"TO FIX:\n"
        f"  1. Move test utilities (mock_hal.py, etc.) to tests/ root\n"
        f"  2. Move test_*.py files to tests/ root\n"
        f"  3. DELETE the tests/ntag424_sdm_provisioner/ folder\n"
        f"  4. Fix imports to use: from ntag424_sdm_provisioner.x import Y\n"
        f"{'='*70}\n"
    )


# ============================================================================
# Shared Fixtures
# ============================================================================
import pytest

from ntag424_sdm_provisioner.sequence_logger import SequenceLogger, create_sequence_logger


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

