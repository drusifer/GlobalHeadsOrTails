import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

try:
    print("Attempting to import ProvisioningService...")
    from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService
    print("Successfully imported ProvisioningService!")
    
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
