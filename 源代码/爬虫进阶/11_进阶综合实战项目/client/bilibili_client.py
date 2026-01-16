# -*- coding: utf-8 -*-
"""
B站 API 客户端

本模块封装了 B站的 API 请求，包括：
- 视频搜索 API
- 视频详情 API
- WBI 签名处理

使用 httpx 作为 HTTP 客户端，支持异步请求。

参考 MediaCrawler 项目的实现：
- https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/client.py
"""

import json
from typing import Dict, Optional, List, Callable, Any
from loguru import logger

# 可选依赖
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from playwright.async_api import BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from tools.sign import BilibiliSign, extract_wbi_keys_from_urls
from models.bilibili import BilibiliVideo, BilibiliSearchResponse
from config import bilibili_config


class BilibiliClient:
    """
    B站 API 客户端

    封装 B站的 API 请求，支持 WBI 签名。

    使用示例：
    ```python
    client = BilibiliClient()
    await client.update_cookies(browser_context)

    # 搜索视频
    videos = await client.search_video_by_keyword("Python教程", page=1)

    # 获取视频详情
    video = await client.get_video_info(bvid="BV1xx411c7mD")
    ```
    """

    def __init__(self):
        """初始化客户端"""
        self.headers = bilibili_config.DEFAULT_HEADERS.copy()
        self.cookie_dict: Dict[str, str] = {}
        self._signer: Optional[BilibiliSign] = None
        self._timeout = bilibili_config.REQUEST_TIMEOUT

    async def update_cookies(self, browser_context: "BrowserContext"):
        """
        从浏览器上下文更新 Cookie

        登录成功后调用此方法，将浏览器的 Cookie 同步到客户端。

        Args:
            browser_context: Playwright 浏览器上下文
        """
        cookies = await browser_context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = {c['name']: c['value'] for c in cookies}
        logger.info(f"[BilibiliClient] 更新了 {len(cookies)} 个 Cookie")

    async def init_wbi_sign(self, page: "Page"):
        """
        初始化 WBI 签名器

        从浏览器的 localStorage 中获取 WBI 密钥。

        Args:
            page: Playwright 页面对象
        """
        try:
            # 从 localStorage 获取 wbi_img_urls
            wbi_img_urls = await page.evaluate("""
                () => {
                    return localStorage.getItem('wbi_img_urls');
                }
            """)

            if not wbi_img_urls:
                logger.warning("[BilibiliClient] 未找到 wbi_img_urls，尝试从 API 获取")
                await self._fetch_wbi_keys()
                return

            # 解析 JSON
            wbi_data = json.loads(wbi_img_urls)
            img_url = wbi_data.get("imgUrl", "")
            sub_url = wbi_data.get("subUrl", "")

            if img_url and sub_url:
                img_key, sub_key = extract_wbi_keys_from_urls(img_url, sub_url)
                self._signer = BilibiliSign(img_key, sub_key)
                logger.info("[BilibiliClient] WBI 签名器初始化成功")
            else:
                logger.warning("[BilibiliClient] wbi_img_urls 数据不完整")
                await self._fetch_wbi_keys()

        except Exception as e:
            logger.error(f"[BilibiliClient] 初始化 WBI 签名器失败: {e}")
            await self._fetch_wbi_keys()

    async def _fetch_wbi_keys(self):
        """
        从 API 获取 WBI 密钥（备用方案）
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    "https://api.bilibili.com/x/web-interface/nav",
                    headers=self.headers
                )
                data = response.json()

                if data.get("code") == 0:
                    wbi_img = data.get("data", {}).get("wbi_img", {})
                    img_url = wbi_img.get("img_url", "")
                    sub_url = wbi_img.get("sub_url", "")

                    if img_url and sub_url:
                        img_key, sub_key = extract_wbi_keys_from_urls(img_url, sub_url)
                        self._signer = BilibiliSign(img_key, sub_key)
                        logger.info("[BilibiliClient] 从 API 获取 WBI 密钥成功")
                        return

            logger.error("[BilibiliClient] 无法获取 WBI 密钥")

        except Exception as e:
            logger.error(f"[BilibiliClient] 获取 WBI 密钥失败: {e}")

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        enable_sign: bool = False
    ) -> Optional[Dict]:
        """
        发送 HTTP 请求

        Args:
            method: 请求方法（GET/POST）
            url: 请求 URL
            params: URL 参数
            data: POST 数据
            enable_sign: 是否启用 WBI 签名

        Returns:
            Dict: 响应数据
        """
        if not HAS_HTTPX:
            logger.error("[BilibiliClient] httpx 未安装")
            return None

        try:
            # 如果需要签名
            if enable_sign and self._signer and params:
                params = self._signer.sign(params)

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=self.headers)
                else:
                    response = await client.post(url, params=params, data=data, headers=self.headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"[BilibiliClient] 请求失败: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"[BilibiliClient] 请求出错: {e}")
            return None

    async def search_video_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        order: str = "",
    ) -> List[BilibiliVideo]:
        """
        按关键词搜索视频

        Args:
            keyword: 搜索关键词
            page: 页码（从1开始）
            page_size: 每页数量（B站固定为20）
            order: 排序方式（空=综合，click=最多点击，pubdate=最新发布）

        Returns:
            List[BilibiliVideo]: 视频列表
        """
        logger.info(f"[BilibiliClient] 搜索视频: {keyword}, 第 {page} 页")

        params = {
            "keyword": keyword,
            "search_type": "video",
            "page": page,
            "page_size": page_size,
            "order": order,
        }

        data = await self._request(
            "GET",
            bilibili_config.SEARCH_URL,
            params=params,
            enable_sign=True
        )

        if not data:
            return []

        if data.get("code") != 0:
            logger.error(f"[BilibiliClient] 搜索失败: {data.get('message')}")
            return []

        # 解析搜索结果
        result = data.get("data", {})
        video_list = result.get("result", [])

        videos = []
        for item in video_list:
            try:
                video = BilibiliVideo.from_search_result(item, keyword)
                videos.append(video)
            except Exception as e:
                logger.debug(f"[BilibiliClient] 解析视频失败: {e}")
                continue

        logger.info(f"[BilibiliClient] 搜索到 {len(videos)} 个视频")
        return videos

    async def get_video_info(
        self,
        aid: Optional[str] = None,
        bvid: Optional[str] = None
    ) -> Optional[BilibiliVideo]:
        """
        获取视频详情

        aid 和 bvid 至少提供一个。

        Args:
            aid: 视频 aid
            bvid: 视频 BV 号

        Returns:
            BilibiliVideo: 视频信息
        """
        if not aid and not bvid:
            logger.error("[BilibiliClient] aid 和 bvid 至少提供一个")
            return None

        params = {}
        if bvid:
            params["bvid"] = bvid
        elif aid:
            params["aid"] = aid

        logger.info(f"[BilibiliClient] 获取视频详情: {bvid or aid}")

        data = await self._request(
            "GET",
            bilibili_config.VIDEO_INFO_URL,
            params=params,
            enable_sign=False  # 视频详情 API 不需要签名
        )

        if not data:
            return None

        if data.get("code") != 0:
            logger.error(f"[BilibiliClient] 获取视频详情失败: {data.get('message')}")
            return None

        video_data = data.get("data", {})
        return BilibiliVideo.from_api_response(video_data)

    async def get_video_info_batch(
        self,
        bvid_list: List[str],
        callback: Optional[Callable[[BilibiliVideo], Any]] = None
    ) -> List[BilibiliVideo]:
        """
        批量获取视频详情

        Args:
            bvid_list: BV 号列表
            callback: 每获取一个视频后的回调函数

        Returns:
            List[BilibiliVideo]: 视频列表
        """
        videos = []

        for bvid in bvid_list:
            video = await self.get_video_info(bvid=bvid)
            if video:
                videos.append(video)
                if callback:
                    await callback(video) if asyncio.iscoroutinefunction(callback) else callback(video)

        return videos

    async def pong(self) -> bool:
        """
        检查登录状态

        通过调用 nav API 检查是否已登录。

        Returns:
            bool: 是否已登录
        """
        try:
            data = await self._request(
                "GET",
                "https://api.bilibili.com/x/web-interface/nav",
                enable_sign=False
            )

            if data and data.get("code") == 0:
                user_data = data.get("data", {})
                if user_data.get("isLogin"):
                    username = user_data.get("uname", "未知用户")
                    logger.info(f"[BilibiliClient] 已登录: {username}")
                    return True

            return False

        except Exception as e:
            logger.debug(f"[BilibiliClient] 检查登录状态失败: {e}")
            return False


# 为了兼容性，添加 asyncio 导入
import asyncio


if __name__ == '__main__':
    # 测试代码
    async def test():
        client = BilibiliClient()

        # 测试搜索（无需登录，但可能被限制）
        videos = await client.search_video_by_keyword("Python教程", page=1)
        print(f"搜索到 {len(videos)} 个视频")

        for video in videos[:3]:
            print(f"  - {video.title} (播放: {video.play_count})")

    asyncio.run(test())
