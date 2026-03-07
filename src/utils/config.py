"""
配置加载器 — Config Loader
读取 config/settings.yaml，提供全项目统一的配置入口。

支持多环境配置:
    - settings.yaml: 默认配置
    - settings.dev.yaml: 开发环境覆盖
    - settings.prod.yaml: 生产环境覆盖
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional
from functools import lru_cache

import yaml
from dotenv import load_dotenv

# 项目根目录
_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = _ROOT / "config" / "settings.yaml"

_cache: Optional[dict[str, Any]] = None


def _load_yaml(file_path: Path) -> dict[str, Any]:
    """加载 YAML 配置文件"""
    if not file_path.exists():
        return {}
    
    with open(file_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(force_reload: bool = False) -> dict[str, Any]:
    """
    加载并缓存 settings.yaml 配置。

    支持环境变量覆盖:
        - ENV: 设置运行环境 (dev/staging/prod)，默认为 dev
        
    环境特定配置:
        - config/settings.yaml: 默认配置
        - config/settings.{ENV}.yaml: 环境特定覆盖

    Args:
        force_reload: 为 True 时强制重新从磁盘读取，忽略缓存。

    Returns:
        配置字典
    """
    global _cache
    
    if _cache is not None and not force_reload:
        return _cache
    
    # 加载 .env 文件
    env_file = _ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    # 获取当前环境
    env = os.getenv("ENV", "dev").lower()
    
    # 加载默认配置
    config = _load_yaml(CONFIG_PATH)
    
    # 加载环境特定覆盖
    env_config_path = _ROOT / "config" / f"settings.{env}.yaml"
    if env_config_path.exists():
        env_config = _load_yaml(env_config_path)
        config = _deep_merge(config, env_config)
    
    # 从环境变量加载敏感配置
    _load_env_overrides(config)
    
    _cache = config
    return config


def _load_env_overrides(config: dict[str, Any]) -> None:
    """从环境变量加载配置覆盖"""
    
    # API Keys
    if "api" not in config:
        config["api"] = {}
    
    for key in ["NBS_API_KEY", "CHOICE_API_KEY", "CRIC_API_KEY"]:
        env_key = key.lower()
        value = os.getenv(key)
        if value:
            config["api"][env_key] = value
    
    # 日志级别
    log_level = os.getenv("LOG_LEVEL")
    if log_level:
        if "logging" not in config:
            config["logging"] = {}
        config["logging"]["level"] = log_level.upper()


def get(key_path: str, default: Any = None) -> Any:
    """
    通过点分路径获取配置项，例如 get('model.weights.aci')。

    Args:
        key_path: 点分字符串路径
        default:  键不存在时的默认值

    Returns:
        对应的配置值，或 default
    """
    cfg = load_config()
    keys = key_path.split(".")
    val = cfg
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


@lru_cache()
def get_cached(key_path: str, default: Any = None) -> Any:
    """
    带缓存的配置获取（适用于频繁访问的配置项）
    """
    return get(key_path, default)


def reset_cache() -> None:
    """重置配置缓存"""
    global _cache
    _cache = None
    get_cached.cache_clear()


# ---------------------------------------------------------------------------
# 环境检测工具
# ---------------------------------------------------------------------------

def is_production() -> bool:
    """是否生产环境"""
    return os.getenv("ENV", "dev").lower() == "prod"


def is_development() -> bool:
    """是否开发环境"""
    return os.getenv("ENV", "dev").lower() == "dev"


def is_staging() -> bool:
    """是否预发布环境"""
    return os.getenv("ENV", "dev").lower() == "staging"
