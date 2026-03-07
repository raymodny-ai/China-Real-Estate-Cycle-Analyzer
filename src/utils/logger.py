"""
日志工具 — Logger Utility
输出到 logs/app.log 文件 + 控制台，供全项目使用。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path


def get_logger(name: str = "china_re_analyzer") -> logging.Logger:
    """
    获取（或创建）命名日志器。

    Args:
        name: 日志器名称，默认 'china_re_analyzer'

    Returns:
        已配置好 Handler 的 Logger 实例
    """
    logger = logging.getLogger(name)

    # 防止重复添加 Handler
    if logger.handlers:
        return logger

    # 尝试从配置读取日志级别，失败时默认 INFO
    try:
        from src.utils.config import get as cfg_get
        level_str: str = cfg_get("logging.level", "INFO").upper()
        log_dir: str = cfg_get("logging.log_dir", "logs")
        log_file: str = cfg_get("logging.log_file", "app.log")
    except Exception:
        level_str = "INFO"
        log_dir = "logs"
        log_file = "app.log"

    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 Handler（自动创建 logs 目录）
    try:
        # 解析 logs 目录的绝对路径
        root = Path(__file__).resolve().parent.parent.parent
        log_path = root / log_dir
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path / log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"无法创建日志文件 Handler: {e}")

    return logger

def setup_global_exceptions():
    """
    配置全局未捕获异常处理，将异常记录到日志中，防止程序静默崩溃。
    """
    import sys
    import threading

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger = get_logger("uncaught_exception")
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    def handle_thread_exception(args):
        logger = get_logger("uncaught_thread_exception")
        logger.error(
            f"Uncaught thread exception in {args.thread.name}",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception
