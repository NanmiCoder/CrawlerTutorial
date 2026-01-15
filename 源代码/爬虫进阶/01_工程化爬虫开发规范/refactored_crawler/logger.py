# -*- coding: utf-8 -*-
# @Desc: 日志配置

import sys
import os
from loguru import logger
from config import settings


def setup_logger():
    """配置日志系统"""
    # 确保日志目录存在
    os.makedirs(settings.log_dir, exist_ok=True)

    # 移除默认处理器
    logger.remove()

    # 控制台输出 - 彩色格式
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )

    # 文件输出 - 所有日志
    logger.add(
        f"{settings.log_dir}/crawler_{settings.env}.log",
        rotation="00:00",       # 每天午夜轮转
        retention="7 days",     # 保留7天
        compression="zip",      # 压缩旧日志
        level="DEBUG",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
    )

    # 错误日志单独文件
    logger.add(
        f"{settings.log_dir}/error_{settings.env}.log",
        rotation="00:00",
        retention="30 days",
        level="ERROR",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
    )

    logger.info(f"日志系统初始化完成 - 级别: {settings.log_level}")
    return logger
