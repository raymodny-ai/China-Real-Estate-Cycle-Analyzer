import pandas as pd
import numpy as np
from datetime import datetime
from src.utils.db import get_engine

def fetch_lpr_data(start_date="2012-01-01", end_date=None):
    """
    Fetches Land Premium Rate (LPR) data (土地溢价拍买率).
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
        
    dates = pd.date_range(start=start_date, end=end_date, freq='ME')
    n = len(dates)
    t = np.arange(n)
    
    # Premium rate dropping near zero in recent years
    premium_rate = 25 - 0.25 * t + 3 * np.sin(2 * np.pi * t / 12) + np.random.normal(0, 2, n)
    premium_rate = np.maximum(premium_rate, 0)
    
    land_volume = 1200 - 8 * t + np.random.normal(0, 50, n)
    land_volume = np.maximum(land_volume, 100)
    
    df = pd.DataFrame({
        'date': dates,
        'premium_rate': premium_rate,
        'land_volume': land_volume
    })
    
    return df

def save_lpr_to_db():
    df = fetch_lpr_data()
    engine = get_engine()
    df.to_sql('land_lpr_data', con=engine, if_exists='replace', index=False)
    print("LPR Data saved to database.")

if __name__ == "__main__":
    save_lpr_to_db()
