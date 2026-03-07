"""
pytest 根目录配置 — conftest.py
自动将项目根目录加入 sys.path，使所有测试可以 `from src.xxx import ...`
"""
import sys
import os

# 项目根目录 = 此文件所在目录
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
