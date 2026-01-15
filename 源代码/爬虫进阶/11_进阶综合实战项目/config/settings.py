# -*- coding: utf-8 -*-
# @Desc: 项目配置

from typing import Optional
from enum import Enum

# 尝试导入 pydantic-settings，如果不存在则使用简单的配置类
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False


class StorageType(str, Enum):
    """存储类型"""
    JSON = "json"
    CSV = "csv"
    DB = "db"


class LoginType(str, Enum):
    """登录类型"""
    COOKIE = "cookie"
    QRCODE = "qrcode"


if HAS_PYDANTIC_SETTINGS:
    class Settings(BaseSettings):
        """项目配置（使用 pydantic-settings）"""

        # 基础配置
        app_name: str = "SocialCrawler"
        debug: bool = False

        # 浏览器配置
        browser_headless: bool = True
        browser_timeout: int = 30000
        browser_user_data_dir: Optional[str] = None

        # 登录配置
        login_type: LoginType = LoginType.COOKIE
        cookie_file: str = "cookies.json"

        # 代理配置
        proxy_enabled: bool = False
        proxy_api_url: Optional[str] = None

        # 爬虫配置
        crawl_max_pages: int = 10
        crawl_delay_min: float = 1.0
        crawl_delay_max: float = 3.0

        # 存储配置
        storage_type: StorageType = StorageType.JSON
        storage_output_dir: str = "./output"

        # 数据库配置（可选）
        db_host: str = "localhost"
        db_port: int = 3306
        db_user: str = "root"
        db_password: str = ""
        db_name: str = "crawler"

        class Config:
            env_file = ".env"
            env_prefix = "CRAWLER_"

else:
    class Settings:
        """项目配置（简单实现）"""

        def __init__(self):
            # 基础配置
            self.app_name = "SocialCrawler"
            self.debug = False

            # 浏览器配置
            self.browser_headless = True
            self.browser_timeout = 30000
            self.browser_user_data_dir = None

            # 登录配置
            self.login_type = LoginType.COOKIE
            self.cookie_file = "cookies.json"

            # 代理配置
            self.proxy_enabled = False
            self.proxy_api_url = None

            # 爬虫配置
            self.crawl_max_pages = 10
            self.crawl_delay_min = 1.0
            self.crawl_delay_max = 3.0

            # 存储配置
            self.storage_type = StorageType.JSON
            self.storage_output_dir = "./output"

            # 数据库配置
            self.db_host = "localhost"
            self.db_port = 3306
            self.db_user = "root"
            self.db_password = ""
            self.db_name = "crawler"


# 全局配置实例
settings = Settings()
