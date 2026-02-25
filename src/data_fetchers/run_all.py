import sys
import os

# Ensure src can be imported
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.data_fetchers.macro_data import save_aci_to_db
from src.data_fetchers.financial_data import save_fpi_to_db
from src.data_fetchers.land_data import save_lpr_to_db

if __name__ == "__main__":
    print("Starting data fetching pipeline...")
    save_aci_to_db()
    save_fpi_to_db()
    save_lpr_to_db()
    print("Data fetching pipeline completed.")
