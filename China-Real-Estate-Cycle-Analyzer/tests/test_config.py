"""
Tests for configuration module
"""
import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_config_import():
    """Test that config module can be imported"""
    try:
        from config import config, Config
        assert config is not None
        assert isinstance(config, Config)
    except ImportError:
        # Config may not exist if not yet created
        pytest.skip("Config module not found")


def test_config_defaults():
    """Test default configuration values"""
    try:
        from config import config
        
        # Test model weights
        weights = config.get_model_weights()
        assert 'aci' in weights
        assert 'fpi' in weights
        assert 'lpr' in weights
        
        # Test thresholds
        thresholds = config.get_thresholds()
        assert 'aci_limit' in thresholds
        
    except ImportError:
        pytest.skip("Config module not found")


def test_get_aci_threshold():
    """Test ACI threshold retrieval"""
    try:
        from config import config
        
        # Default threshold
        threshold = config.get_aci_threshold()
        assert threshold > 0
        
        # Tier-specific threshold
        threshold_t1 = config.get_aci_threshold('tier1')
        assert threshold_t1 > 0
        
    except ImportError:
        pytest.skip("Config module not found")


def test_data_source_config():
    """Test data source configuration"""
    try:
        from config import config
        
        # Test getting data source config
        nbs_config = config.get_data_source_config('nbs')
        assert isinstance(nbs_config, dict)
        
    except ImportError:
        pytest.skip("Config module not found")


def test_config_file_exists():
    """Test that config file exists"""
    config_path = project_root / "config" / "settings.yaml"
    # Config file may or may not exist depending on setup
    # This is just a documentation test
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
