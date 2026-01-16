# -*- coding: utf-8 -*-
"""
项目配置模块

本模块定义了 B站爬虫项目的所有配置项，包括：
- 基础配置（应用名称、调试模式）
- 浏览器配置（无头模式、超时时间）
- 登录配置（登录方式、Cookie文件）
- 代理配置（是否启用、API地址）
- 爬虫配置（最大页数、延迟时间）
- 存储配置（存储类型、输出目录）
"""

from typing import Optional, List
from enum import Enum

# 尝试导入 pydantic-settings，如果不存在则使用简单的配置类
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False


class StorageType(str, Enum):
    """存储类型枚举"""
    JSON = "json"
    CSV = "csv"


class LoginType(str, Enum):
    """登录类型枚举"""
    COOKIE = "cookie"
    QRCODE = "qrcode"


class CrawlerType(str, Enum):
    """爬虫类型枚举"""
    SEARCH = "search"    # 关键词搜索
    DETAIL = "detail"    # 指定视频详情


if HAS_PYDANTIC_SETTINGS:
    class Settings(BaseSettings):
        """项目配置（使用 pydantic-settings）"""

        # 基础配置
        app_name: str = "BilibiliCrawler"
        debug: bool = False

        # 浏览器配置
        browser_headless: bool = False  # B站扫码登录需要显示浏览器
        browser_timeout: int = 30000
        browser_user_data_dir: Optional[str] = "browser_data/bili_user_data"

        # 登录配置
        login_type: LoginType = LoginType.QRCODE
        cookie_str: str = ""  # Cookie 字符串，当 login_type=cookie 时使用
        save_login_state: bool = True  # 是否保存登录状态

        # 代理配置
        proxy_enabled: bool = False
        proxy_api_url: Optional[str] = None

        # B站爬虫配置
        crawler_type: CrawlerType = CrawlerType.SEARCH
        keywords: str = "Python教程"  # 搜索关键词，多个用逗号分隔
        specified_id_list: List[str] = []  # 指定视频列表（BV号）
        max_video_count: int = 20  # 最大爬取视频数量
        crawl_delay_min: float = 1.0
        crawl_delay_max: float = 3.0
        max_concurrency: int = 3  # 最大并发数

        # 存储配置
        storage_type: StorageType = StorageType.JSON
        storage_output_dir: str = "./output"

        class Config:
            env_file = ".env"
            env_prefix = "BILI_"

else:
    class Settings:
        """项目配置（简单实现，无 pydantic-settings 依赖）"""

        def __init__(self):
            # 基础配置
            self.app_name = "BilibiliCrawler"
            self.debug = False

            # 浏览器配置
            self.browser_headless = False  # B站扫码登录需要显示浏览器
            self.browser_timeout = 30000
            self.browser_user_data_dir = "browser_data/bili_user_data"

            # 登录配置
            self.login_type = LoginType.QRCODE
            self.cookie_str = ""  # Cookie 字符串
            self.save_login_state = True

            # 代理配置
            self.proxy_enabled = False
            self.proxy_api_url = None

            # B站爬虫配置
            self.crawler_type = CrawlerType.SEARCH
            self.keywords = "Python教程"
            self.specified_id_list = []
            self.max_video_count = 20
            self.crawl_delay_min = 1.0
            self.crawl_delay_max = 3.0
            self.max_concurrency = 3

            # 存储配置
            self.storage_type = StorageType.JSON
            self.storage_output_dir = "./output"


# 全局配置实例
settings = Settings()
