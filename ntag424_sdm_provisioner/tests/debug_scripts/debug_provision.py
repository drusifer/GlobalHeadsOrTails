import logging
import os
import sys


# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from ntag424_sdm_provisioner.constants import GAME_COIN_BASE_URL
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.seritag_simulator import SeritagCardConnection, SeritagSimulator
from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService


# Configure logging
logging.basicConfig(level=logging.DEBUG)

def main():
    print("Setting up simulator...")
    sim = SeritagSimulator()
    sim.connect()
    conn = SeritagCardConnection(sim)
    
    # Create temp key manager
    with open("debug_keys.csv", "w") as f:
        f.write("uid,picc_master_key,app_read_key,sdm_mac_key\n")
    
    key_mgr = CsvKeyManager("debug_keys.csv")
    
    service = ProvisioningService(conn, key_mgr)
    
    print("Running provision()...")
    try:
        result = service.provision(base_url=GAME_COIN_BASE_URL)
        print(f"Provision result: {result}")
    except Exception as e:
        print(f"Provision crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
