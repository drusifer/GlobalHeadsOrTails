import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

try:
    print("Importing ProvisioningService...")
    from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService
    print("OK")

    print("Importing SeritagCardSimulator...")
    from ntag424_sdm_provisioner.seritag_simulator import SeritagCardSimulator, SeritagCardConnection
    print("OK")

    print("Importing CsvKeyManager...")
    from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
    print("OK")

    print("Importing constants...")
    from ntag424_sdm_provisioner.constants import GAME_COIN_BASE_URL
    print("OK")
    
    print("All imports successful!")

except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
