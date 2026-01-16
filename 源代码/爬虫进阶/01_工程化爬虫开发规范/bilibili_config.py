"""
B站爬虫配置示例

本模块展示如何使用 pydantic-settings 进行 B站爬虫的配置管理。
这是第01章"工程化爬虫开发规范"的B站实战示例。

与第11章综合实战项目的关联：
- config/settings.py: 使用相同的配置类设计
- config/bilibili_config.py: 使用相同的API配置常量
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
from enum import Enum


# ============== 枚举类型 ==============

class StorageType(str, Enum):
    """存储类型"""
    JSON = "json"
    CSV = "csv"


class LoginType(str, Enum):
    """登录类型"""
    COOKIE = "cookie"
    QRCODE = "qrcode"


class CrawlerType(str, Enum):
    """爬取类型"""
    SEARCH = "search"    # 关键词搜索
    DETAIL = "detail"    # 指定视频详情


# ============== B站爬虫配置类 ==============

class BilibiliSettings(BaseSettings):
    """
    B站爬虫配置

    支持从环境变量和 .env 文件读取配置
    环境变量前缀为 CRAWLER_，例如 CRAWLER_DEBUG=true
    """

    # 基础配置
    app_name: str = "BilibiliCrawler"
    debug: bool = False

    # 浏览器配置
    browser_headless: bool = False  # B站扫码登录需要显示浏览器
    browser_timeout: int = 30000
    browser_user_data_dir: Optional[str] = "./browser_data"
    save_login_state: bool = True

    # 登录配置
    login_type: LoginType = LoginType.QRCODE
    cookie_str: str = ""

    # 爬虫配置
    crawler_type: CrawlerType = CrawlerType.SEARCH
    keywords: str = "Python教程"  # 搜索关键词，多个用逗号分隔
    specified_id_list: List[str] = []  # 指定视频列表
    max_video_count: int = 20
    max_concurrency: int = 3
    crawl_delay_min: float = 1.0
    crawl_delay_max: float = 3.0

    # 存储配置
    storage_type: StorageType = StorageType.JSON
    storage_output_dir: str = "./output"

    class Config:
        env_file = ".env"
        env_prefix = "CRAWLER_"


# ============== B站 API 配置常量 ==============

# API 地址
SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"
VIDEO_INFO_URL = "https://api.bilibili.com/x/web-interface/view"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"

# 请求配置
SEARCH_PAGE_SIZE = 20
REQUEST_TIMEOUT = 30

# 默认请求头
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
}

# WBI 签名密钥混淆表（用于API签名）
WBI_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

# 登录相关
LOGIN_BUTTON_SELECTOR = "xpath=//div[@class='right-entry__outside go-login-btn']//div"
QRCODE_SELECTOR = "//div[@class='login-scan-box']//img"
LOGIN_COOKIE_KEYS = ["SESSDATA", "DedeUserID", "bili_jct"]

# B站 API 错误码
BILIBILI_ERROR_CODES = {
    0: "成功",
    -1: "应用程序不存在或已被封禁",
    -2: "Access Key错误",
    -3: "API校验密匙错误",
    -4: "调用方对该Method没有权限",
    -101: "账号未登录",
    -102: "账号被封停",
    -111: "csrf校验失败",
    -400: "请求错误",
    -403: "访问权限不足",
    -404: "啥都木有",
    -412: "请求被拦截（风控）",
    -509: "请求过于频繁，请稍后再试",
    -799: "请求过于频繁，请稍后再试",
}


# ============== 全局配置实例 ==============

# 创建全局配置实例，可以直接导入使用
settings = BilibiliSettings()


# ============== 演示入口 ==============

if __name__ == "__main__":
    from loguru import logger

    # 打印配置信息
    logger.info("=" * 50)
    logger.info("B站爬虫配置示例")
    logger.info("=" * 50)

    logger.info(f"应用名称: {settings.app_name}")
    logger.info(f"调试模式: {settings.debug}")
    logger.info(f"登录方式: {settings.login_type.value}")
    logger.info(f"爬取类型: {settings.crawler_type.value}")
    logger.info(f"搜索关键词: {settings.keywords}")
    logger.info(f"最大视频数: {settings.max_video_count}")
    logger.info(f"存储类型: {settings.storage_type.value}")
    logger.info(f"输出目录: {settings.storage_output_dir}")

    logger.info("-" * 50)
    logger.info("API配置:")
    logger.info(f"搜索API: {SEARCH_URL}")
    logger.info(f"视频详情API: {VIDEO_INFO_URL}")
    logger.info(f"用户信息API: {NAV_URL}")

    logger.info("-" * 50)
    logger.info("默认请求头:")
    for key, value in DEFAULT_HEADERS.items():
        logger.info(f"  {key}: {value[:50]}...")
