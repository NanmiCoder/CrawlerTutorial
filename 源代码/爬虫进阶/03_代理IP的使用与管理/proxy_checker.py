# -*- coding: utf-8 -*-
# @Desc: 独立的代理检测脚本
# 用于快速检测代理可用性

import asyncio
import sys
from typing import List
from loguru import logger

# 添加模块路径
sys.path.insert(0, ".")

from proxy_pool.base import ProxyInfo, ProxyProtocol
from proxy_pool.checker import ProxyChecker


async def check_single_proxy(proxy_str: str) -> bool:
    """
    检测单个代理

    Args:
        proxy_str: 代理字符串，格式为 host:port 或 protocol://host:port

    Returns:
        代理是否可用
    """
    # 解析代理字符串
    if "://" in proxy_str:
        protocol, rest = proxy_str.split("://")
        host, port = rest.split(":")
        protocol = ProxyProtocol(protocol)
    else:
        host, port = proxy_str.split(":")
        protocol = ProxyProtocol.HTTP

    proxy = ProxyInfo(
        host=host,
        port=int(port),
        protocol=protocol
    )

    checker = ProxyChecker(timeout=10)
    is_valid = await checker.check(proxy)

    if is_valid:
        print(f"✓ 代理可用: {proxy.url}")
        print(f"  响应时间: {proxy.avg_response_time:.2f}s")
    else:
        print(f"✗ 代理不可用: {proxy.url}")

    return is_valid


async def check_proxy_list(proxy_list: List[str]) -> List[ProxyInfo]:
    """
    批量检测代理列表

    Args:
        proxy_list: 代理字符串列表

    Returns:
        可用的代理列表
    """
    proxies = []

    for proxy_str in proxy_list:
        try:
            if "://" in proxy_str:
                protocol, rest = proxy_str.split("://")
                host, port = rest.split(":")
                protocol = ProxyProtocol(protocol)
            else:
                host, port = proxy_str.split(":")
                protocol = ProxyProtocol.HTTP

            proxies.append(ProxyInfo(
                host=host,
                port=int(port),
                protocol=protocol
            ))
        except Exception as e:
            logger.warning(f"解析代理失败: {proxy_str} - {e}")

    if not proxies:
        print("没有有效的代理可检测")
        return []

    print(f"开始检测 {len(proxies)} 个代理...")

    checker = ProxyChecker(timeout=10)
    valid_proxies = await checker.check_batch(proxies, concurrency=20)

    print(f"\n检测结果: {len(valid_proxies)}/{len(proxies)} 可用")

    for proxy in valid_proxies:
        print(f"  ✓ {proxy.host}:{proxy.port} (响应: {proxy.avg_response_time:.2f}s)")

    return valid_proxies


async def check_from_file(filepath: str) -> List[ProxyInfo]:
    """
    从文件读取代理并检测

    Args:
        filepath: 代理列表文件路径（每行一个代理）

    Returns:
        可用的代理列表
    """
    try:
        with open(filepath, "r") as f:
            proxy_list = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"文件不存在: {filepath}")
        return []

    return await check_proxy_list(proxy_list)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="代理检测工具")
    parser.add_argument(
        "proxy",
        nargs="?",
        help="要检测的代理 (host:port)"
    )
    parser.add_argument(
        "-f", "--file",
        help="从文件读取代理列表"
    )
    parser.add_argument(
        "-l", "--list",
        nargs="+",
        help="检测多个代理"
    )

    args = parser.parse_args()

    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        level="INFO"
    )

    if args.file:
        # 从文件读取
        asyncio.run(check_from_file(args.file))
    elif args.list:
        # 检测多个代理
        asyncio.run(check_proxy_list(args.list))
    elif args.proxy:
        # 检测单个代理
        asyncio.run(check_single_proxy(args.proxy))
    else:
        # 演示模式
        print("代理检测工具使用示例:")
        print("  检测单个代理: python proxy_checker.py 127.0.0.1:8080")
        print("  检测多个代理: python proxy_checker.py -l 1.1.1.1:8080 2.2.2.2:8080")
        print("  从文件读取:   python proxy_checker.py -f proxies.txt")


if __name__ == "__main__":
    main()
