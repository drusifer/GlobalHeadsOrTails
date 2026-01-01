import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

try:
    print("Attempting to import constants...")
    from ntag424_sdm_provisioner import constants
    print("Successfully imported constants!")
    
    print("Checking SDMConfiguration...")
    print(constants.SDMConfiguration)
    
    print("Checking SDMUrlTemplate...")
    print(constants.SDMUrlTemplate)
    
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
