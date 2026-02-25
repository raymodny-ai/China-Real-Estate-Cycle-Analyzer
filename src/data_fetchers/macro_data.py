import pandas as pd
import numpy as np
from datetime import datetime
from src.utils.db import get_engine

def fetch_aci_data(start_date="2012-01-01", end_date=None):
    """
    Fetches Area Clearance Index (ACI) related data.
    Simulated dataset to demonstrate: Inventory / Sales Area.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
        
    dates = pd.date_range(start=start_date, end=end_date, freq='ME') # 'ME' for month-end
    n = len(dates)
    
    t = np.arange(n)
    trend_sales = 12000 + 100 * t - 0.8 * t**2
    seasonality = 1500 * np.sin(2 * np.pi * t / 12)
    sales_area = trend_sales + seasonality + np.random.normal(0, 800, n)
    sales_area = np.maximum(sales_area, 2000)
    
    inventory_area = np.zeros(n)
    inventory_area[0] = 60000
    for i in range(1, n):
        completions = 11000 + 30 * t[i] + np.random.normal(0, 500)
        inventory_area[i] = inventory_area[i-1] + completions - sales_area[i]
        inventory_area[i] = max(inventory_area[i], 10000)
        
    df = pd.DataFrame({
        'date': dates,
        'sales_area': sales_area,
        'inventory_area': inventory_area
    })
    
    df['aci'] = df['inventory_area'] / df['sales_area']
    return df

def save_aci_to_db():
    df = fetch_aci_data()
    engine = get_engine()
    df.to_sql('macro_aci_data', con=engine, if_exists='replace', index=False)
    print("ACI Data saved to database.")

if __name__ == "__main__":
    save_aci_to_db()
