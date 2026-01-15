# -*- coding: utf-8 -*-
# @Desc: loguru 日志库使用演示
# 演示 loguru 的各种功能：日志级别、文件输出、日志轮转等

import sys
from loguru import logger


def basic_usage():
    """基础用法演示"""
    print("=" * 50)
    print("1. 基础日志输出")
    print("=" * 50)

    # loguru 默认配置下的日志输出
    logger.debug("这是 DEBUG 级别 - 用于详细的调试信息")
    logger.info("这是 INFO 级别 - 用于正常的运行信息")
    logger.warning("这是 WARNING 级别 - 用于警告信息")
    logger.error("这是 ERROR 级别 - 用于错误信息")
    logger.critical("这是 CRITICAL 级别 - 用于严重错误")


def custom_format():
    """自定义日志格式"""
    print("\n" + "=" * 50)
    print("2. 自定义日志格式")
    print("=" * 50)

    # 移除默认处理器
    logger.remove()

    # 添加自定义格式的处理器
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level="DEBUG",
        colorize=True
    )

    logger.info("使用自定义格式的日志输出")
    logger.debug("包含时间、级别、文件名、函数名、行号等信息")


def file_logging():
    """文件日志演示"""
    print("\n" + "=" * 50)
    print("3. 文件日志输出")
    print("=" * 50)

    # 添加文件日志
    # rotation: 日志轮转策略
    # retention: 日志保留策略
    # compression: 旧日志压缩
    logger.add(
        "logs/demo_{time:YYYY-MM-DD}.log",
        rotation="100 MB",     # 文件达到 100MB 时轮转
        retention="7 days",    # 保留 7 天的日志
        compression="zip",     # 压缩旧日志
        encoding="utf-8",
        level="DEBUG"
    )

    logger.info("这条日志会同时输出到控制台和文件")
    logger.debug("文件日志支持自动轮转和压缩")


def error_logging():
    """错误日志处理"""
    print("\n" + "=" * 50)
    print("4. 异常日志记录")
    print("=" * 50)

    # 单独的错误日志文件
    logger.add(
        "logs/error_{time:YYYY-MM-DD}.log",
        rotation="00:00",      # 每天午夜轮转
        retention="30 days",   # 保留 30 天
        level="ERROR",         # 只记录 ERROR 及以上级别
        encoding="utf-8"
    )

    try:
        result = 1 / 0
    except ZeroDivisionError:
        # 使用 exception() 方法会自动记录完整的堆栈信息
        logger.exception("捕获到除零错误")

    logger.error("这是一条普通的错误日志")


def context_logging():
    """上下文日志"""
    print("\n" + "=" * 50)
    print("5. 带上下文的日志")
    print("=" * 50)

    # 使用 bind() 添加上下文信息
    context_logger = logger.bind(user_id="12345", request_id="abc-xyz")
    context_logger.info("处理用户请求")
    context_logger.info("请求处理完成")

    # 使用 opt() 添加额外信息
    logger.opt(colors=True).info("支持 <red>彩色</red> <green>文本</green>")


def structured_logging():
    """结构化日志"""
    print("\n" + "=" * 50)
    print("6. 结构化日志（JSON格式）")
    print("=" * 50)

    # 移除之前的处理器
    logger.remove()

    # 添加 JSON 格式的日志输出（适合日志分析系统）
    logger.add(
        "logs/structured.json",
        serialize=True,        # 输出 JSON 格式
        rotation="10 MB",
        level="DEBUG"
    )

    # 同时保留控制台输出
    logger.add(sys.stderr, level="INFO")

    # 记录结构化数据
    logger.info("用户登录", user_id=12345, ip="192.168.1.1")
    logger.info("请求完成", url="/api/data", status=200, duration_ms=150)


def crawler_logging_example():
    """爬虫场景的日志使用示例"""
    print("\n" + "=" * 50)
    print("7. 爬虫场景日志示例")
    print("=" * 50)

    # 重置日志配置
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # 模拟爬虫运行时的日志
    logger.info("爬虫任务启动")
    logger.debug("配置加载完成: max_concurrent=10, timeout=30s")

    # 模拟爬取过程
    for page in range(1, 4):
        logger.info(f"开始爬取第 {page} 页")
        logger.debug(f"请求URL: https://example.com/page/{page}")

        # 模拟一些情况
        if page == 2:
            logger.warning(f"第 {page} 页请求超时，准备重试")
            logger.info(f"第 {page} 页重试成功")

        logger.info(f"第 {page} 页爬取完成，获取 20 条数据")

    logger.info("爬虫任务完成，共获取 60 条数据")


def main():
    """主函数"""
    # 确保日志目录存在
    import os
    os.makedirs("logs", exist_ok=True)

    # 运行所有演示
    basic_usage()
    custom_format()
    file_logging()
    error_logging()
    context_logging()
    # structured_logging()  # 取消注释以测试 JSON 日志
    crawler_logging_example()


if __name__ == "__main__":
    main()
