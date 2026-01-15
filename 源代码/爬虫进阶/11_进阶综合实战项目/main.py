# -*- coding: utf-8 -*-
# @Desc: 社交媒体数据采集工具 - 主程序入口
"""
综合实战项目：社交媒体数据采集与分析工具

功能特点：
- 多种登录方式（Cookie 注入 / 扫码登录）
- 反检测浏览器自动化（Playwright + stealth.js）
- 代理 IP 轮换支持
- 多格式数据存储（JSON / CSV）
- 词云和统计报告自动生成

使用方法：
    python main.py
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入各模块
from config.settings import settings, LoginType
from core.browser import BrowserManager
from login.auth import AuthManager
from crawler.spider import ContentCrawler, ScrollCrawler
from store.backend import StorageManager
from analysis.report import ReportGenerator


# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)
logger.add(
    "logs/crawler_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


async def demo_crawl():
    """
    演示爬取流程

    注意：这是一个演示函数，实际使用时需要：
    1. 修改目标 URL 和选择器
    2. 配置正确的登录认证
    3. 遵守目标网站的 robots.txt 和服务条款
    """
    logger.info(f"启动 {settings.app_name}")
    logger.info(f"配置: headless={settings.browser_headless}, 存储类型={settings.storage_type}")

    # 初始化浏览器
    browser = BrowserManager(
        headless=settings.browser_headless,
        timeout=settings.browser_timeout
    )

    try:
        async with browser:
            context = await browser.start()

            # 配置登录认证（示例）
            auth = AuthManager()
            if settings.login_type == LoginType.COOKIE:
                # Cookie 登录
                auth.set_cookie_auth(
                    cookie_file=settings.cookie_file,
                    domain="example.com"
                )
            else:
                # 扫码登录
                auth.set_qrcode_auth(
                    login_url="https://example.com/login",
                    qrcode_selector=".qrcode-img",
                    success_selector=".user-avatar",
                    save_cookie_file=settings.cookie_file
                )

            # 执行登录（如果配置了 Cookie 文件）
            cookie_path = Path(settings.cookie_file)
            if cookie_path.exists():
                login_success = await auth.login(context)
                if login_success:
                    logger.info("登录认证成功")
                else:
                    logger.warning("登录认证失败，将以未登录状态继续")
            else:
                logger.info("未找到 Cookie 文件，跳过登录认证")

            # 创建爬虫实例
            page = await browser.new_page()

            # 示例：使用内容爬虫爬取分页列表
            # 实际使用时需要修改为目标网站的选择器
            crawler = ContentCrawler(
                start_url="https://example.com/articles",
                item_selector=".article-item",
                fields={
                    "title": ".article-title",
                    "content": ".article-summary",
                    "author": ".author-name",
                    "time": ".publish-time",
                    "link": ".article-title|href",
                },
                next_page_selector=".pagination .next",
                max_pages=settings.crawl_max_pages,
                delay_min=settings.crawl_delay_min,
                delay_max=settings.crawl_delay_max
            )

            # 执行爬取
            logger.info("开始爬取数据...")
            results = await crawler.crawl(page)
            logger.info(f"爬取完成: {len(results)} 条数据")

            if not results:
                logger.warning("没有爬取到数据")
                return

            # 保存数据
            storage = StorageManager(
                storage_type=settings.storage_type.value,
                output_dir=settings.storage_output_dir
            )
            await storage.save(results)

            # 生成分析报告
            report = ReportGenerator(results, settings.storage_output_dir)
            report_path = report.generate(text_field='content')
            logger.info(f"分析报告已生成: {report_path}")

            logger.info("=" * 50)
            logger.info("任务完成！")
            logger.info(f"数据文件: {storage.filepath}")
            logger.info(f"分析报告: {report_path}")
            logger.info("=" * 50)

    except Exception as e:
        logger.exception(f"执行出错: {e}")
        raise


async def main():
    """主函数"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║       社交媒体数据采集与分析工具 v1.0                    ║
    ║                                                          ║
    ║  功能：                                                  ║
    ║  - 自动化数据采集                                        ║
    ║  - 多格式数据存储                                        ║
    ║  - 词云和统计分析                                        ║
    ║                                                          ║
    ║  注意：请遵守目标网站的使用条款和法律法规                ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    await demo_crawl()


if __name__ == "__main__":
    # 创建必要的目录
    Path("logs").mkdir(exist_ok=True)
    Path(settings.storage_output_dir).mkdir(parents=True, exist_ok=True)

    # 运行主程序
    asyncio.run(main())
