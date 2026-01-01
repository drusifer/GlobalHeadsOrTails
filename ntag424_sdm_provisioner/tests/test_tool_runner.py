#!/usr/bin/env python3
"""
Test ToolRunner with trace-based simulator.

Verifies:
- ToolRunner can be instantiated with tools
- Tools list is accessible
"""

import logging
import sys
from pathlib import Path

# Add src and tests to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.tools.diagnostics_tool import DiagnosticsTool
from ntag424_sdm_provisioner.tools.runner import ToolRunner

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_tool_runner_with_simulator():
    """Test tool runner instantiation."""
    print("="*70)
    print("Testing Tool Runner Instantiation")
    print("="*70)
    
    # Setup key manager
    csv_path = Path(__file__).parent.parent / "examples" / "tag_keys.csv"
    backup_path = Path(__file__).parent.parent / "examples" / "tag_keys_backup.csv"
    key_mgr = CsvKeyManager(csv_path, backup_path)
    
    # Create tools list
    tools = [DiagnosticsTool()]
    
    # Create runner
    print("\n1. Creating ToolRunner...")
    runner = ToolRunner(key_mgr, tools)
    
    print(f"   Registered tools: {len(runner.tools)}")
    for tool in runner.tools:
        print(f"     - {tool.name}")
    
    assert len(runner.tools) == 1
    assert runner.tools[0].name == "Show Diagnostics"
    
    print("\n" + "="*70)
    print("✅ Tool Runner Test PASSED")
    print("="*70)
    
    return True


if __name__ == '__main__':
    success = test_tool_runner_with_simulator()
    sys.exit(0 if success else 1)

