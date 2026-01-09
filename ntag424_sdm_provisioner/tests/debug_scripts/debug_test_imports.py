import os
import sys


# Add src to path
sys.path.insert(0, os.path.abspath("src"))

try:
    print("Importing ProvisioningService...")
    print("OK")

    print("Importing SeritagCardSimulator...")
    print("OK")

    print("Importing CsvKeyManager...")
    print("OK")

    print("Importing constants...")
    print("OK")
    
    print("All imports successful!")

except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
