import pandas as pd
import numpy as np
from datetime import datetime
from src.utils.db import get_engine

TICKERS = ['000002.SZ', '600048.SS', '0688.HK']

def fetch_simulated_fpi():
    """Simulated FPI data (Net Financing Cash Flow) if yfinance is unreliable or slow."""
    dates = pd.date_range(start="2012-01-01", end=datetime.now().strftime("%Y-%m-%d"), freq='YE')
    n = len(dates)
    t = np.arange(n)
    
    # Net financing: high positive in the past, dropping to negative recently
    net_financing = 80000 - 8000 * t + np.random.normal(0, 5000, n)
    
    df = pd.DataFrame({
        'date': dates,
        'net_financing_cash_flow': net_financing,
        'ticker': 'SIMULATED_SECTOR'
    })
    return df

def fetch_fpi_data():
    """
    Fetches Financial Pressure Index (FPI) related data.
    We use simulated data for a stable baseline demonstration.
    """
    try:
        print("Using simulated data for FPI to ensure stable baseline.")
        return fetch_simulated_fpi()
    except Exception as e:
        print(f"Error fetching: {e}")
        return fetch_simulated_fpi()

def save_fpi_to_db():
    df = fetch_fpi_data()
    engine = get_engine()
    df.to_sql('financial_fpi_data', con=engine, if_exists='replace', index=False)
    print("FPI Data saved to database.")

if __name__ == "__main__":
    save_fpi_to_db()
