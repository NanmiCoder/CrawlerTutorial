# -*- coding: utf-8 -*-
# @Desc: 配置管理

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """爬虫配置"""

    # 环境配置
    env: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=True, description="调试模式")
    log_level: str = Field(default="DEBUG", description="日志级别")

    # 爬虫配置
    first_n_page: int = Field(default=3, description="爬取前N页")
    base_host: str = Field(default="https://www.ptt.cc", description="目标站点")
    request_timeout: int = Field(default=30, description="请求超时")
    max_retries: int = Field(default=3, description="最大重试次数")
    request_delay: float = Field(default=0.5, description="请求间隔")

    # 输出配置
    output_dir: str = Field(default="./output", description="输出目录")
    log_dir: str = Field(default="./logs", description="日志目录")

    class Config:
        env_file = ".env"
        env_prefix = "CRAWLER_"


settings = Settings()
