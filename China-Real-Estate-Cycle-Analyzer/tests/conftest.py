"""
Test configuration module
"""
import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def project_root_path():
    """Project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_df():
    """Sample DataFrame for testing"""
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(start='2020-01', end='2024-12', freq='M')
    return pd.DataFrame({
        'date': dates,
        'sales_area': np.random.randint(5000, 15000, len(dates)),
        'inventory': np.random.randint(20000, 50000, len(dates)),
        'aci': np.random.uniform(10, 30, len(dates)),
        'fpi': np.random.uniform(-10000, 10000, len(dates)),
        'lpr_5y': np.random.uniform(4.0, 5.5, len(dates))
    })
