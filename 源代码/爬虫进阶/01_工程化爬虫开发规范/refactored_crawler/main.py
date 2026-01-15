# -*- coding: utf-8 -*-
# @Desc: 爬虫主程序入口

import asyncio
import json
import os
from loguru import logger

from .logger import setup_logger
from .config import settings
from .crawler import BBSCrawler
from .exceptions import CrawlerException


async def main():
    """主程序"""
    # 初始化日志
    setup_logger()

    logger.info("=" * 50)
    logger.info("工程化爬虫示例")
    logger.info("=" * 50)
    logger.info(f"运行环境: {settings.env}")
    logger.info(f"调试模式: {settings.debug}")
    logger.info(f"目标页数: {settings.first_n_page}")

    # 创建输出目录
    os.makedirs(settings.output_dir, exist_ok=True)

    # 创建爬虫实例
    crawler = BBSCrawler()

    try:
        # 运行爬虫
        result = await crawler.run()

        # 保存结果
        output_file = f"{settings.output_dir}/crawl_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

        logger.info(f"结果已保存到: {output_file}")

        # 输出统计
        logger.info("=" * 50)
        logger.info("爬取统计")
        logger.info("=" * 50)
        logger.info(f"总页数: {result.total_pages}")
        logger.info(f"总帖子: {result.total_notes}")
        logger.info(f"成功数: {result.success_count}")
        logger.info(f"失败数: {result.fail_count}")

    except CrawlerException as e:
        logger.error(f"爬虫异常: {e}")
        raise

    except Exception as e:
        logger.exception(f"未预期的异常: {e}")
        raise

    finally:
        await crawler.cleanup()
        logger.info("程序结束")


def run():
    """运行入口"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.critical(f"程序异常退出: {e}")
        exit(1)


if __name__ == "__main__":
    run()
