#!/usr/bin/env python3
"""
Test that SDMUrlTemplate.generate_url() works correctly.

This test verifies the fix for the bug where tools were calling
template.generate_url() but the method didn't exist, and were passing
'ctr_placeholder' instead of 'read_ctr_placeholder'.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ntag424_sdm_provisioner.constants import SDMUrlTemplate


def test_build_url_basic():
    """Test basic URL building with all placeholders."""
    template = SDMUrlTemplate(
        base_url="https://example.com/api",
        uid_placeholder="00000000000000",
        read_ctr_placeholder="000000",
        cmac_placeholder="0000000000000000"
    )
    
    url = template.generate_url()
    print(f"Built URL: {url}")
    
    # Verify structure
    assert "https://example.com/api?" in url
    assert "uid=00000000000000" in url
    assert "ctr=000000" in url
    assert "cmac=0000000000000000" in url
    
    # Verify order (uid, ctr, cmac)
    uid_pos = url.find("uid=")
    ctr_pos = url.find("ctr=")
    cmac_pos = url.find("cmac=")
    
    assert uid_pos < ctr_pos < cmac_pos, "Parameters should be in order: uid, ctr, cmac"
    
    print("✅ Basic URL building works")


def test_build_url_with_existing_params():
    """Test URL building when base_url already has query params."""
    template = SDMUrlTemplate(
        base_url="https://example.com/api?existing=param",
        uid_placeholder="00000000000000",
        read_ctr_placeholder="000000",
        cmac_placeholder="0000000000000000"
    )
    
    url = template.generate_url()
    print(f"Built URL with existing params: {url}")
    
    # Should use & not ? as separator
    assert "?existing=param&uid=" in url
    assert "ctr=000000" in url
    
    print("✅ URL building with existing params works")


def test_build_url_minimal():
    """Test URL building with only required params (no counter)."""
    template = SDMUrlTemplate(
        base_url="https://example.com/api",
        uid_placeholder="00000000000000",
        cmac_placeholder="0000000000000000",
        read_ctr_placeholder=None,  # Explicitly no counter
    )
    
    url = template.generate_url()
    print(f"Built minimal URL: {url}")
    
    # Should have uid and cmac but not ctr
    assert "uid=00000000000000" in url
    assert "cmac=0000000000000000" in url
    assert "ctr=" not in url
    
    print("✅ Minimal URL building works")


def test_parameter_name_fix():
    """Test that 'read_ctr_placeholder' parameter works (was 'ctr_placeholder')."""
    # This should work now (was causing TypeError before fix)
    try:
        template = SDMUrlTemplate(
            base_url="https://example.com/api",
            uid_placeholder="00000000000000",
            read_ctr_placeholder="000000",  # Correct parameter name
            cmac_placeholder="0000000000000000"
        )
        print("✅ 'read_ctr_placeholder' parameter accepted")
    except TypeError as e:
        print(f"❌ FAILED: {e}")
        raise
    
    # Verify it builds correctly
    url = template.generate_url()
    assert "ctr=000000" in url
    print("✅ Parameter name fix verified")


if __name__ == '__main__':
    print("="*70)
    print("Testing SDMUrlTemplate fixes")
    print("="*70)
    
    try:
        test_build_url_basic()
        print()
        test_build_url_with_existing_params()
        print()
        test_build_url_minimal()
        print()
        test_parameter_name_fix()
        
        print()
        print("="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        sys.exit(0)
        
    except Exception as e:
        print()
        print("="*70)
        print(f"❌ TEST FAILED: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        sys.exit(1)

