"""
Configuration Loader

Load settings from config/settings.yaml
"""

import yaml
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(__file__).parent / "settings.yaml"


class Config:
    """Configuration manager"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load()
    
    def load(self):
        """Load configuration from YAML file"""
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = self._get_defaults()
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'model': {
                'weights': {
                    'aci': 0.4,
                    'fpi': 0.3,
                    'lpr': 0.3
                },
                'thresholds': {
                    'aci_limit': 24,
                    'fpi_threshold': 0,
                    'lpr_change_threshold': 0.05
                }
            },
            'ui': {
                'default_city': '北京',
                'theme': 'dark'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_model_weights(self) -> Dict[str, float]:
        """Get composite index weights"""
        return self.get('model.weights', {})
    
    def get_thresholds(self) -> Dict[str, Any]:
        """Get threshold settings"""
        return self.get('model.thresholds', {})
    
    def get_aci_threshold(self, city_tier: str = None) -> int:
        """Get ACI threshold, optionally by city tier"""
        if city_tier:
            tier_thresholds = self.get('model.city_tiers', {})
            if city_tier in tier_thresholds:
                return tier_thresholds[city_tier].get('aci_limit', 24)
        return self.get('model.thresholds.aci_limit', 24)
    
    def get_data_source_config(self, source: str) -> Dict[str, Any]:
        """Get data source configuration"""
        return self.get(f'data_sources.{source}', {})


# Global instance
config = Config()


# Convenience functions
def get_config() -> Config:
    """Get config instance"""
    return config


def load_config() -> Dict[str, Any]:
    """Load full configuration"""
    return config._config
