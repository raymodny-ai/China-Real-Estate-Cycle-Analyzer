import pandas as pd
import numpy as np
import warnings
from src.utils.db import get_engine

warnings.filterwarnings('ignore')

def calculate_ci_index():
    """
    Reads ACI, FPI, and LPR data from the database, evaluates the conditions,
    and calculates the Composite Index (CI).
    CI = w1*I(ACI < 24) + w2*I(FPI > 0) + w3*I(LPR improving)
    """
    engine = get_engine()
    
    try:
        aci_df = pd.read_sql('macro_aci_data', con=engine)
        fpi_df = pd.read_sql('financial_fpi_data', con=engine)
        lpr_df = pd.read_sql('land_lpr_data', con=engine)
    except Exception as e:
        print(f"Error reading from DB: {e}. Please ensure data is fetched.")
        return None
        
    aci_df['date'] = pd.to_datetime(aci_df['date'])
    fpi_df['date'] = pd.to_datetime(fpi_df['date'])
    lpr_df['date'] = pd.to_datetime(lpr_df['date'])
    
    aci_df['year_month'] = aci_df['date'].dt.to_period('M')
    fpi_df['year_month'] = fpi_df['date'].dt.to_period('M') 
    lpr_df['year_month'] = lpr_df['date'].dt.to_period('M')
    
    all_months = pd.date_range(start='2012-01-01', end=pd.Timestamp.today().normalize(), freq='M').to_period('M')
    master_df = pd.DataFrame({'year_month': all_months})
    
    # FPI needs forward fill because it was generated Yearly
    fpi_monthly = fpi_df.set_index('year_month').resample('M').ffill().reset_index()
    fpi_monthly = fpi_monthly.drop_duplicates('year_month', keep='last')
    
    master_df = master_df.merge(aci_df[['year_month', 'aci']], on='year_month', how='left')
    master_df = master_df.merge(fpi_monthly[['year_month', 'net_financing_cash_flow']], on='year_month', how='left')
    master_df = master_df.merge(lpr_df[['year_month', 'premium_rate']], on='year_month', how='left')
    
    # Forward/Back fill remaining NAs for safety
    master_df = master_df.ffill().bfill()
    
    # Condition 1: ACI (Inventory < 2 years, i.e., 24 months)
    master_df['I_ACI'] = (master_df['aci'] < 24).astype(int)
    
    # Condition 2: FPI (Net Financing > 0)
    master_df['I_FPI'] = (master_df['net_financing_cash_flow'] > 0).astype(int)
    
    # Condition 3: LPR (Land premium止跌 or recovering)
    ma3 = master_df['premium_rate'].rolling(3).mean()
    master_df['I_LPR'] = (ma3 > ma3.shift(1)).astype(int)
    master_df['I_LPR'] = master_df['I_LPR'].fillna(0)
    
    # Weights based on model components (assigned default weights)
    w1, w2, w3 = 0.4, 0.3, 0.3
    master_df['CI'] = w1 * master_df['I_ACI'] + w2 * master_df['I_FPI'] + w3 * master_df['I_LPR']
    
    # Convert period back to timestamp for saving
    master_df['date'] = master_df['year_month'].dt.to_timestamp()
    master_df = master_df.drop(columns=['year_month'])
    
    master_df.to_sql('model_ci_index', con=engine, if_exists='replace', index=False)
    print("CI Index calculated and saved.")
    return master_df

if __name__ == "__main__":
    calculate_ci_index()
