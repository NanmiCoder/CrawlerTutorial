# -*- coding: utf-8 -*-
"""
B站视频数据采集工具 - 主程序入口

综合实战项目：B站视频数据采集与分析工具

功能特点：
- 多种登录方式（扫码登录 / Cookie 登录）
- 反检测浏览器自动化（Playwright + stealth.js）
- WBI 签名算法支持（B站 API 签名）
- 视频搜索和详情获取
- 多格式数据存储（JSON / CSV）
- 词云和统计报告自动生成

参考 MediaCrawler 项目的实现：
- https://github.com/NanmiCoder/MediaCrawler

使用方法：
    python main.py

配置说明：
    修改 config/settings.py 中的配置项：
    - crawler_type: 爬取类型（search=搜索, detail=指定视频）
    - keywords: 搜索关键词（逗号分隔）
    - max_video_count: 最大爬取数量
    - login_type: 登录方式（qrcode=扫码, cookie=Cookie）
"""

import asyncio
import sys
from pathlib import Path
from typing import List
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入各模块
from config import settings, CrawlerType
from crawler.spider import BilibiliCrawler
from store.backend import StorageManager
from analysis.report import ReportGenerator, generate_report
from models.bilibili import BilibiliVideo


# 配置日志
def setup_logger():
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{message}</cyan>",
        level="INFO"
    )
    logger.add(
        "logs/bilibili_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8"
    )


async def run_crawler() -> List[BilibiliVideo]:
    """
    运行爬虫

    完整流程：
    1. 启动浏览器
    2. 执行登录（扫码或Cookie）
    3. 初始化 API 客户端（获取 WBI 密钥）
    4. 根据配置执行爬取（搜索或指定视频）
    5. 返回爬取结果

    Returns:
        List[BilibiliVideo]: 爬取的视频列表
    """
    crawler = BilibiliCrawler()
    return await crawler.start()


async def save_data(videos: List[BilibiliVideo]) -> str:
    """
    保存数据

    Args:
        videos: 视频列表

    Returns:
        str: 保存的文件路径
    """
    if not videos:
        logger.warning("没有数据需要保存")
        return ""

    # 转换为字典列表
    data = [video.to_dict() for video in videos]

    # 创建存储管理器
    storage = StorageManager(
        storage_type=settings.storage_type.value,
        output_dir=settings.storage_output_dir
    )

    # 保存数据
    success = await storage.save(data)

    if success:
        return str(storage.filepath)
    return ""


def generate_analysis_report(videos: List[BilibiliVideo]) -> str:
    """
    生成分析报告

    Args:
        videos: 视频列表

    Returns:
        str: 报告文件路径
    """
    if not videos:
        logger.warning("没有数据，跳过报告生成")
        return ""

    report_path = generate_report(
        videos=videos,
        output_dir=settings.storage_output_dir
    )

    return report_path


async def main():
    """主函数"""

    # 打印欢迎信息
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║           B站视频数据采集与分析工具 v2.0                 ║
    ║                                                          ║
    ║  功能：                                                  ║
    ║  - 视频搜索与详情获取                                    ║
    ║  - 扫码登录 / Cookie 登录                                ║
    ║  - JSON / CSV 数据存储                                   ║
    ║  - 词云和统计分析报告                                    ║
    ║                                                          ║
    ║  参考项目：MediaCrawler                                  ║
    ║  注意：请遵守 B站的使用条款和法律法规                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # 显示当前配置
    logger.info(f"启动 {settings.app_name}")
    logger.info(f"爬取类型: {settings.crawler_type.value}")
    logger.info(f"登录方式: {settings.login_type.value}")
    logger.info(f"最大数量: {settings.max_video_count}")
    logger.info(f"存储类型: {settings.storage_type.value}")

    if settings.crawler_type == CrawlerType.SEARCH:
        logger.info(f"搜索关键词: {settings.keywords}")
    else:
        logger.info(f"指定视频: {len(settings.specified_id_list)} 个")

    logger.info("=" * 50)

    try:
        # 1. 运行爬虫
        logger.info("开始爬取数据...")
        videos = await run_crawler()
        logger.info(f"爬取完成: {len(videos)} 条视频")

        if not videos:
            logger.warning("没有爬取到数据，退出")
            return

        # 2. 保存数据
        logger.info("保存数据...")
        data_path = await save_data(videos)
        if data_path:
            logger.info(f"数据已保存: {data_path}")

        # 3. 生成分析报告
        logger.info("生成分析报告...")
        report_path = generate_analysis_report(videos)
        if report_path:
            logger.info(f"报告已生成: {report_path}")

        # 4. 打印结果摘要
        logger.info("=" * 50)
        logger.info("任务完成！")
        logger.info(f"爬取视频: {len(videos)} 个")
        if data_path:
            logger.info(f"数据文件: {data_path}")
        if report_path:
            logger.info(f"分析报告: {report_path}")
        logger.info("=" * 50)

        # 打印部分结果预览
        print("\n视频预览（前 5 条）:")
        print("-" * 60)
        for i, video in enumerate(videos[:5], 1):
            print(f"{i}. {video.title[:40]}...")
            print(f"   UP主: {video.nickname}")
            print(f"   播放: {video.play_count:,}  点赞: {video.liked_count:,}")
            print()

    except KeyboardInterrupt:
        logger.warning("用户中断执行")
    except Exception as e:
        logger.exception(f"执行出错: {e}")
        raise


def cli():
    """命令行入口"""
    # 设置日志
    setup_logger()

    # 创建必要的目录
    Path("logs").mkdir(exist_ok=True)
    Path(settings.storage_output_dir).mkdir(parents=True, exist_ok=True)

    # 运行主程序
    asyncio.run(main())


if __name__ == "__main__":
    cli()
