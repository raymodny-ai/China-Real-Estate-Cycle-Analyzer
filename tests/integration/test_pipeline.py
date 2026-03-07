"""
集成测试 — 全链路数据流水线
tests/integration/test_pipeline.py
"""
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine

from src.data_fetchers.run_all import run_pipeline

@pytest.fixture
def mock_db_engine():
    # 使用内存数据库进行集成测试
    engine = create_engine("sqlite:///:memory:")
    with patch("src.utils.db.get_engine", return_value=engine), \
         patch("src.repository.base.get_engine", return_value=engine, create=True), \
         patch("src.services.cycle_analyzer.get_engine", return_value=engine, create=True), \
         patch("src.services.backtest.get_engine", return_value=engine, create=True):
        yield engine

def test_full_pipeline_execution(mock_db_engine):
    """
    测试全链路数据流是否能顺利执行。
    由于使用的是内存数据库，测试不污染本地已有数据。
    """
    try:
        # 不强制网络更新，允许使用缓存或Fallback mock数据
        run_pipeline(force_update=False)
    except Exception as e:
        pytest.fail(f"全文流水线执行失败并抛出异常: {e}")
