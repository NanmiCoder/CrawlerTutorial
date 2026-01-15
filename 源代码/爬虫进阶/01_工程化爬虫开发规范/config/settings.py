# -*- coding: utf-8 -*-
# @Desc: 爬虫配置管理模块
# 使用 pydantic-settings 进行配置管理，支持环境变量和 .env 文件

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class CrawlerSettings(BaseSettings):
    """
    爬虫项目配置类

    配置优先级（从高到低）：
    1. 环境变量 (CRAWLER_XXX)
    2. .env 文件
    3. 默认值
    """

    # 运行环境配置
    env: str = Field(default="development", description="运行环境: development/production")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别: DEBUG/INFO/WARNING/ERROR")

    # HTTP 请求配置
    request_timeout: int = Field(default=30, description="请求超时时间(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试基础延迟(秒)")
    retry_max_delay: float = Field(default=60.0, description="重试最大延迟(秒)")

    # 并发控制配置
    max_concurrent: int = Field(default=10, description="最大并发请求数")
    request_delay: float = Field(default=0.5, description="请求间隔(秒)")

    # 数据库配置
    db_host: str = Field(default="localhost", description="数据库主机")
    db_port: int = Field(default=3306, description="数据库端口")
    db_user: str = Field(default="root", description="数据库用户名")
    db_password: str = Field(default="", description="数据库密码")
    db_name: str = Field(default="crawler_db", description="数据库名称")

    # 代理配置
    proxy_url: Optional[str] = Field(default=None, description="HTTP代理地址")

    # 存储配置
    output_dir: str = Field(default="./data", description="数据输出目录")
    log_dir: str = Field(default="./logs", description="日志输出目录")

    class Config:
        # .env 文件路径
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 环境变量前缀
        env_prefix = "CRAWLER_"
        # 额外字段处理
        extra = "ignore"

    @property
    def db_url(self) -> str:
        """构建数据库连接URL"""
        return f"mysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def ensure_dirs(self):
        """确保必要的目录存在"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)


# 全局配置实例（单例模式）
settings = CrawlerSettings()


# 开发环境配置
class DevelopmentSettings(CrawlerSettings):
    """开发环境配置"""
    env: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"
    max_concurrent: int = 5


# 生产环境配置
class ProductionSettings(CrawlerSettings):
    """生产环境配置"""
    env: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    max_concurrent: int = 20


def get_settings() -> CrawlerSettings:
    """
    根据环境变量返回对应的配置实例

    设置环境变量 CRAWLER_ENV=production 可切换到生产配置
    """
    env = os.getenv("CRAWLER_ENV", "development")
    settings_map = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,
    }
    settings_class = settings_map.get(env, DevelopmentSettings)
    return settings_class()


if __name__ == "__main__":
    # 测试配置
    config = get_settings()
    print(f"当前环境: {config.env}")
    print(f"调试模式: {config.debug}")
    print(f"日志级别: {config.log_level}")
    print(f"请求超时: {config.request_timeout}秒")
    print(f"最大并发: {config.max_concurrent}")
    print(f"数据库URL: {config.db_url}")
