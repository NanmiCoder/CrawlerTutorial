"""
B站请求头配置与反爬虫实战

本模块展示如何针对 B站 API 进行请求伪装，包括：
- 完整的请求头配置
- 动态 Referer 设置
- API 错误码处理
- 随机延迟策略

这是第02章"反爬虫对抗基础"的B站实战示例。

与第11章综合实战项目的关联：
- config/bilibili_config.py: DEFAULT_HEADERS 配置
- client/bilibili_client.py: API 错误处理逻辑
"""

import asyncio
import random
from typing import List, Dict, Optional
from dataclasses import dataclass

import httpx
from loguru import logger


# ============== B站请求头配置 ==============

BILIBILI_HEADERS = {
    # User-Agent - 必须是真实浏览器UA
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",

    # Referer - B站API必须，否则返回-403
    "Referer": "https://www.bilibili.com",

    # Origin - 跨域请求时必须
    "Origin": "https://www.bilibili.com",

    # Accept 头
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",

    # 连接设置
    "Connection": "keep-alive",

    # Sec-Fetch 系列头 - 现代浏览器标准
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",

    # Sec-CH-UA 系列头 - Chrome 特有
    "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"macOS"',
}


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


# ============== 请求头构建器 ==============

class BilibiliHeadersBuilder:
    """B站请求头构建器"""

    def __init__(self):
        self.base_headers = BILIBILI_HEADERS.copy()

    def build_for_api(self, cookie: str = "") -> dict:
        """
        构建 API 请求头

        Args:
            cookie: Cookie 字符串

        Returns:
            完整的请求头字典
        """
        headers = self.base_headers.copy()
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def build_for_search(self, keyword: str, cookie: str = "") -> dict:
        """构建搜索 API 请求头"""
        headers = self.build_for_api(cookie)
        # 搜索时 Referer 应该指向搜索页
        headers["Referer"] = f"https://search.bilibili.com/all?keyword={keyword}"
        return headers

    def build_for_video(self, bvid: str, cookie: str = "") -> dict:
        """构建视频详情 API 请求头"""
        headers = self.build_for_api(cookie)
        # 视频详情时 Referer 应该指向视频页
        headers["Referer"] = f"https://www.bilibili.com/video/{bvid}"
        return headers


# ============== API 响应处理 ==============

async def handle_bilibili_response(response_data: dict, url: str) -> Optional[dict]:
    """
    处理 B站 API 响应

    B站 API 返回格式: {"code": 0, "message": "...", "data": {...}}

    Args:
        response_data: API 响应数据
        url: 请求 URL（用于日志）

    Returns:
        成功时返回 data 字段，失败时返回 None 或抛出异常
    """
    code = response_data.get("code", -1)
    message = response_data.get("message", "")

    if code == 0:
        # 成功
        return response_data.get("data", {})

    elif code == -101:
        # 账号未登录
        logger.warning(f"[Bilibili] 账号未登录: {url}")
        raise Exception("Cookie已过期，需要重新登录")

    elif code == -412:
        # 请求被拦截（风控）
        logger.warning(f"[Bilibili] 触发风控 -412: {url}")
        raise Exception("触发B站风控，请降低请求频率或更换IP")

    elif code == -403:
        # 访问权限不足
        logger.error(f"[Bilibili] 无权限访问 -403: {url}")
        raise Exception("无权限访问，请检查请求头配置")

    elif code == -404:
        # 资源不存在
        logger.warning(f"[Bilibili] 资源不存在 -404: {url}")
        return None

    else:
        # 其他错误
        error_desc = BILIBILI_ERROR_CODES.get(code, "未知错误")
        logger.error(f"[Bilibili] API错误 code={code} ({error_desc}): {message}")
        raise Exception(f"B站API错误: {message}")


# ============== B站视频搜索爬虫 ==============

@dataclass
class BilibiliVideoInfo:
    """B站视频信息"""
    bvid: str
    title: str
    author: str
    play: int
    description: str


class BilibiliSearchCrawler:
    """
    B站视频搜索爬虫

    演示完整的请求伪装技术：
    - 正确的请求头配置
    - Cookie 管理
    - 随机延迟
    - 错误处理
    """

    # B站搜索 API
    SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"

    def __init__(
        self,
        cookie: str = "",
        min_delay: float = 1.0,
        max_delay: float = 3.0
    ):
        """
        初始化爬虫

        Args:
            cookie: B站Cookie（包含SESSDATA）
            min_delay: 最小请求间隔
            max_delay: 最大请求间隔
        """
        self.cookie = cookie
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._client: Optional[httpx.AsyncClient] = None
        self._headers_builder = BilibiliHeadersBuilder()

    async def __aenter__(self):
        headers = self._headers_builder.build_for_api(self.cookie)
        self._client = httpx.AsyncClient(headers=headers, timeout=30)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def _random_delay(self):
        """随机延迟"""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug(f"[BilibiliSearch] 等待 {delay:.2f} 秒")
        await asyncio.sleep(delay)

    async def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict]:
        """
        搜索视频

        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            视频列表
        """
        params = {
            "keyword": keyword,
            "search_type": "video",
            "page": page,
            "page_size": page_size,
            # 注意：实际使用时需要添加 WBI 签名参数
            # "wts": timestamp,
            # "w_rid": signature,
        }

        # 动态设置 Referer
        self._client.headers["Referer"] = (
            f"https://search.bilibili.com/all?keyword={keyword}"
        )

        logger.info(f"[BilibiliSearch] 搜索: {keyword}, 第 {page} 页")

        try:
            response = await self._client.get(self.SEARCH_URL, params=params)
            data = response.json()

            code = data.get("code", -1)
            if code != 0:
                error_desc = BILIBILI_ERROR_CODES.get(code, "未知错误")
                logger.warning(f"[BilibiliSearch] API返回错误: code={code} ({error_desc})")
                return []

            result = data.get("data", {}).get("result", [])
            logger.info(f"[BilibiliSearch] 获取 {len(result)} 条结果")

            # 随机延迟
            await self._random_delay()

            return result

        except Exception as e:
            logger.error(f"[BilibiliSearch] 搜索失败: {e}")
            return []

    async def search_all(
        self,
        keyword: str,
        max_count: int = 100
    ) -> List[Dict]:
        """
        搜索全部视频（翻页）

        Args:
            keyword: 搜索关键词
            max_count: 最大获取数量

        Returns:
            视频列表
        """
        all_results = []
        page = 1

        while len(all_results) < max_count:
            results = await self.search(keyword, page)
            if not results:
                break

            all_results.extend(results)
            page += 1

            # 避免翻页过深
            if page > 50:
                break

        return all_results[:max_count]


# ============== 演示入口 ==============

async def demo():
    """演示B站请求头配置"""
    logger.info("=" * 50)
    logger.info("B站反爬虫对抗示例")
    logger.info("=" * 50)

    # 1. 展示请求头
    builder = BilibiliHeadersBuilder()
    logger.info("默认 API 请求头:")
    headers = builder.build_for_api()
    for key, value in headers.items():
        if len(str(value)) > 50:
            value = str(value)[:50] + "..."
        logger.info(f"  {key}: {value}")

    logger.info("-" * 50)

    # 2. 展示搜索请求头
    logger.info("搜索 API 请求头（关键词: Python）:")
    search_headers = builder.build_for_search("Python")
    logger.info(f"  Referer: {search_headers['Referer']}")

    logger.info("-" * 50)

    # 3. 展示视频详情请求头
    logger.info("视频详情 API 请求头（BV1234567890）:")
    video_headers = builder.build_for_video("BV1234567890")
    logger.info(f"  Referer: {video_headers['Referer']}")

    logger.info("-" * 50)

    # 4. 展示错误码
    logger.info("B站常见 API 错误码:")
    important_codes = [-101, -412, -403, -404, -509]
    for code in important_codes:
        desc = BILIBILI_ERROR_CODES.get(code, "未知")
        logger.info(f"  {code}: {desc}")


if __name__ == "__main__":
    asyncio.run(demo())
