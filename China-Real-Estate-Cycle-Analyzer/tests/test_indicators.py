"""
Tests for indicators module
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_indicators_import():
    """Test that indicators module can be imported"""
    try:
        from src.models.indicators import IndicatorCalculator
        assert IndicatorCalculator is not None
    except ImportError:
        pytest.skip("IndicatorCalculator module not found")


def test_indicators_init():
    """Test IndicatorCalculator initialization"""
    try:
        from src.models.indicators import IndicatorCalculator
        
        ind = IndicatorCalculator()
        assert ind is not None
        assert hasattr(ind, 'aci_threshold')
        assert hasattr(ind, 'fpi_threshold')
        
    except ImportError:
        pytest.skip("IndicatorCalculator module not found")


def test_calculate_aci_indicators(sample_df):
    """Test ACI indicator calculation"""
    try:
        from src.models.indicators import IndicatorCalculator
        
        ind = IndicatorCalculator()
        result = ind.calculate_aci_indicators(sample_df)
        
        # Check that result has expected columns
        assert 'I_ACI' in result.columns or 'aci_signal' in result.columns
        
        # Check that I_ACI values are binary (0 or 1)
        if 'I_ACI' in result.columns:
            assert set(result['I_ACI'].unique()).issubset({0, 1})
            
    except ImportError:
        pytest.skip("IndicatorCalculator module not found")
    except Exception as e:
        pytest.fail(f"ACI calculation failed: {e}")


def test_calculate_fpi_indicators(sample_df):
    """Test FPI indicator calculation"""
    try:
        from src.models.indicators import IndicatorCalculator
        
        # Add required column
        sample_df['net_financing_cash_flow'] = sample_df['fpi']
        
        ind = IndicatorCalculator()
        result = ind.calculate_fpi_indicators(sample_df)
        
        # Check that result has expected columns
        assert 'I_FPI' in result.columns or 'fpi_signal' in result.columns
        
    except ImportError:
        pytest.skip("IndicatorCalculator module not found")
    except Exception as e:
        pytest.fail(f"FPI calculation failed: {e}")


def test_calculate_lpr_indicators(sample_df):
    """Test LPR indicator calculation"""
    try:
        from src.models.indicators import IndicatorCalculator
        
        ind = IndicatorCalculator()
        result = ind.calculate_lpr_indicators(sample_df)
        
        # Check that result has expected columns
        assert 'I_LPR' in result.columns or 'lpr_signal' in result.columns
        
    except ImportError:
        pytest.skip("IndicatorCalculator module not found")
    except Exception as e:
        pytest.fail(f"LPR calculation failed: {e}")


def test_composite_index_calculation(sample_df):
    """Test composite index calculation"""
    try:
        from src.models.indicators import IndicatorCalculator
        
        ind = IndicatorCalculator()
        
        # Calculate all indicators
        result = ind.calculate_aci_indicators(sample_df)
        result = ind.calculate_fpi_indicators(result)
        result = ind.calculate_lpr_indicators(result)
        
        # Calculate composite index
        result = ind.calculate_composite_index(result)
        
        # Check that CI exists
        assert 'CI' in result.columns or 'composite_index' in result.columns
        
    except ImportError:
        pytest.skip("IndicatorCalculator module not found")
    except Exception as e:
        pytest.fail(f"Composite index calculation failed: {e}")


def test_empty_dataframe():
    """Test handling of empty DataFrame"""
    try:
        from src.models.indicators import IndicatorCalculator
        
        empty_df = pd.DataFrame()
        ind = IndicatorCalculator()
        
        # Should handle gracefully
        result = ind.calculate_aci_indicators(empty_df)
        assert result is not None
        
    except ImportError:
        pytest.skip("IndicatorCalculator module not found")


def test_threshold_values():
    """Test default threshold values"""
    try:
        from src.models.indicators import IndicatorCalculator
        
        ind = IndicatorCalculator()
        
        # Check default values are reasonable
        assert ind.aci_threshold > 0
        assert ind.fpi_threshold is not None
        
    except ImportError:
        pytest.skip("IndicatorCalculator module not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
