# -*- coding: utf-8 -*-
# @Desc: 异常处理与重试机制演示
# 演示自定义异常类、tenacity 重试库的使用

import asyncio
import random
from typing import Optional

from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)


# ==================== 自定义异常类 ====================

class CrawlerException(Exception):
    """爬虫基础异常类"""

    def __init__(self, message: str, url: Optional[str] = None):
        self.message = message
        self.url = url
        super().__init__(self.message)

    def __str__(self):
        if self.url:
            return f"{self.message} (URL: {self.url})"
        return self.message


class RequestException(CrawlerException):
    """HTTP 请求异常"""
    pass


class TimeoutException(RequestException):
    """请求超时异常"""
    pass


class HTTPStatusException(RequestException):
    """HTTP 状态码异常"""

    def __init__(self, message: str, status_code: int, url: Optional[str] = None):
        self.status_code = status_code
        super().__init__(message, url)

    def __str__(self):
        return f"HTTP {self.status_code}: {self.message}"


class RateLimitException(RequestException):
    """触发速率限制异常"""
    pass


class IPBlockedException(RequestException):
    """IP 被封禁异常"""
    pass


class ParseException(CrawlerException):
    """数据解析异常"""
    pass


class StorageException(CrawlerException):
    """数据存储异常"""
    pass


class LoginRequiredException(CrawlerException):
    """需要登录异常"""
    pass


# ==================== 重试装饰器示例 ====================

@retry(
    stop=stop_after_attempt(3),                    # 最多重试 3 次
    wait=wait_exponential(multiplier=1, max=10),   # 指数退避: 1s, 2s, 4s...最长10s
    retry=retry_if_exception_type(TimeoutException),  # 只对超时异常重试
    before_sleep=before_sleep_log(logger, "WARNING")  # 重试前记录日志
)
async def fetch_with_basic_retry(url: str) -> str:
    """基础重试示例"""
    # 模拟随机超时
    if random.random() < 0.7:  # 70% 概率超时
        logger.debug(f"模拟请求超时: {url}")
        raise TimeoutException("请求超时", url)

    logger.info(f"请求成功: {url}")
    return f"Response from {url}"


@retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(multiplier=1, min=1, max=30),  # 随机指数退避
    retry=retry_if_exception_type((TimeoutException, RateLimitException)),
    reraise=True  # 重试用尽后重新抛出原始异常
)
async def fetch_with_advanced_retry(url: str) -> str:
    """高级重试示例 - 更多配置项"""
    dice = random.random()

    if dice < 0.4:
        raise TimeoutException("连接超时", url)
    elif dice < 0.6:
        raise RateLimitException("触发速率限制", url)

    return f"Success: {url}"


def create_retry_decorator(
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
):
    """
    工厂函数：创建可配置的重试装饰器

    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_delay, max=max_delay),
        retry=retry_if_exception_type((
            TimeoutException,
            RateLimitException
        )),
        reraise=True
    )


# 使用工厂函数创建装饰器
@create_retry_decorator(max_attempts=4, base_delay=2.0)
async def fetch_important_data(url: str) -> dict:
    """重要数据获取 - 使用更多重试次数"""
    if random.random() < 0.6:
        raise TimeoutException("超时", url)
    return {"data": "important", "url": url}


# ==================== 异常处理最佳实践 ====================

async def crawl_page(url: str) -> Optional[dict]:
    """
    爬取单个页面的示例 - 展示异常处理最佳实践
    """
    try:
        # 模拟请求
        result = await fetch_with_basic_retry(url)
        return {"url": url, "content": result}

    except TimeoutException as e:
        # 可恢复的异常 - 记录警告并返回 None
        logger.warning(f"页面爬取超时，跳过: {e}")
        return None

    except RateLimitException as e:
        # 需要特殊处理的异常
        logger.warning(f"触发速率限制: {e}")
        # 这里可以切换代理或增加延迟
        return None

    except IPBlockedException as e:
        # 严重异常 - 向上抛出
        logger.error(f"IP被封禁: {e}")
        raise

    except CrawlerException as e:
        # 其他爬虫异常
        logger.error(f"爬虫异常: {e}")
        return None

    except Exception as e:
        # 未预期的异常 - 记录完整堆栈
        logger.exception(f"未知异常: {e}")
        raise


async def run_crawler(urls: list):
    """
    爬虫主程序 - 展示全局异常处理
    """
    results = []

    try:
        for url in urls:
            logger.info(f"开始爬取: {url}")
            result = await crawl_page(url)
            if result:
                results.append(result)
            # 请求间隔
            await asyncio.sleep(0.5)

        logger.info(f"爬取完成，成功: {len(results)}/{len(urls)}")
        return results

    except IPBlockedException:
        logger.critical("IP被封禁，终止爬虫")
        raise

    except asyncio.CancelledError:
        logger.warning("任务被取消")
        raise

    except Exception as e:
        logger.exception(f"爬虫运行异常: {e}")
        raise

    finally:
        # 清理工作
        logger.info("执行清理工作...")


# ==================== 演示函数 ====================

async def demo_basic_retry():
    """演示基础重试"""
    print("\n" + "=" * 50)
    print("演示 1: 基础重试机制")
    print("=" * 50)

    url = "https://example.com/data"
    try:
        result = await fetch_with_basic_retry(url)
        print(f"结果: {result}")
    except TimeoutException as e:
        print(f"重试用尽后仍然失败: {e}")


async def demo_advanced_retry():
    """演示高级重试"""
    print("\n" + "=" * 50)
    print("演示 2: 高级重试机制")
    print("=" * 50)

    url = "https://example.com/important"
    try:
        result = await fetch_with_advanced_retry(url)
        print(f"结果: {result}")
    except (TimeoutException, RateLimitException) as e:
        print(f"重试用尽: {e}")


async def demo_exception_handling():
    """演示异常处理"""
    print("\n" + "=" * 50)
    print("演示 3: 异常处理最佳实践")
    print("=" * 50)

    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
    ]

    try:
        results = await run_crawler(urls)
        print(f"成功获取 {len(results)} 个页面")
    except Exception as e:
        print(f"爬虫异常终止: {e}")


async def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"
    )

    print("=" * 50)
    print("异常处理与重试机制演示")
    print("=" * 50)

    # 运行演示
    await demo_basic_retry()
    await demo_advanced_retry()
    await demo_exception_handling()

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
