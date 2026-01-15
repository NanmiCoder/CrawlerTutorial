# -*- coding: utf-8 -*-
# @Desc: 请求头构建器

from typing import Dict, Optional
from ua_rotator import UARotator


class HeadersBuilder:
    """
    HTTP 请求头构建器

    功能：
    - 构建完整的浏览器请求头
    - 支持页面请求和 API 请求
    - 自动设置 Referer 和 Origin
    - 集成 UA 轮换
    """

    # 页面请求头模板（访问 HTML 页面）
    PAGE_HEADERS_TEMPLATE = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    # API 请求头模板（AJAX/Fetch 请求）
    API_HEADERS_TEMPLATE = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    def __init__(self, ua_rotator: Optional[UARotator] = None):
        """
        初始化请求头构建器

        Args:
            ua_rotator: UA 轮换器实例，如果不提供则创建默认实例
        """
        self.ua_rotator = ua_rotator or UARotator()

    def build_page_headers(
        self,
        referer: Optional[str] = None,
        host: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        构建页面请求头

        Args:
            referer: Referer 地址
            host: Host 地址
            extra_headers: 额外的请求头

        Returns:
            完整的请求头字典
        """
        headers = self.PAGE_HEADERS_TEMPLATE.copy()
        headers["User-Agent"] = self.ua_rotator.get_random()

        if host:
            headers["Host"] = host

        if referer:
            headers["Referer"] = referer
            # 有 Referer 时，Sec-Fetch-Site 应该改为 same-origin 或 cross-site
            headers["Sec-Fetch-Site"] = "same-origin"

        if extra_headers:
            headers.update(extra_headers)

        return headers

    def build_api_headers(
        self,
        referer: str,
        origin: Optional[str] = None,
        content_type: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        构建 API 请求头

        Args:
            referer: Referer 地址（API 请求通常需要）
            origin: Origin 地址（POST 请求通常需要）
            content_type: Content-Type
            extra_headers: 额外的请求头

        Returns:
            完整的请求头字典
        """
        headers = self.API_HEADERS_TEMPLATE.copy()
        headers["User-Agent"] = self.ua_rotator.get_random()
        headers["Referer"] = referer

        if origin:
            headers["Origin"] = origin

        if content_type:
            headers["Content-Type"] = content_type

        if extra_headers:
            headers.update(extra_headers)

        return headers

    def build_ajax_headers(
        self,
        referer: str,
        x_requested_with: bool = True
    ) -> Dict[str, str]:
        """
        构建传统 AJAX 请求头

        Args:
            referer: Referer 地址
            x_requested_with: 是否添加 X-Requested-With 头

        Returns:
            AJAX 请求头字典
        """
        headers = self.build_api_headers(referer=referer)

        if x_requested_with:
            headers["X-Requested-With"] = "XMLHttpRequest"

        return headers

    def build_mobile_headers(
        self,
        referer: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        构建移动端请求头

        Args:
            referer: Referer 地址
            extra_headers: 额外的请求头

        Returns:
            移动端请求头字典
        """
        headers = self.PAGE_HEADERS_TEMPLATE.copy()
        headers["User-Agent"] = self.ua_rotator.get_mobile()
        headers["Sec-Ch-Ua-Mobile"] = "?1"
        headers["Sec-Ch-Ua-Platform"] = '"Android"'

        if referer:
            headers["Referer"] = referer
            headers["Sec-Fetch-Site"] = "same-origin"

        if extra_headers:
            headers.update(extra_headers)

        return headers


def demo():
    """演示请求头构建器的使用"""
    print("=" * 60)
    print("请求头构建器演示")
    print("=" * 60)

    builder = HeadersBuilder()

    print("\n1. 页面请求头:")
    page_headers = builder.build_page_headers(
        referer="https://example.com/list",
        host="example.com"
    )
    for key, value in list(page_headers.items())[:8]:
        print(f"   {key}: {value[:50]}...")

    print("\n2. API 请求头:")
    api_headers = builder.build_api_headers(
        referer="https://example.com/page",
        origin="https://example.com",
        content_type="application/json"
    )
    for key, value in list(api_headers.items())[:6]:
        print(f"   {key}: {value[:50]}...")

    print("\n3. AJAX 请求头:")
    ajax_headers = builder.build_ajax_headers(
        referer="https://example.com/dashboard"
    )
    print(f"   X-Requested-With: {ajax_headers.get('X-Requested-With')}")

    print("\n4. 移动端请求头:")
    mobile_headers = builder.build_mobile_headers()
    print(f"   User-Agent: {mobile_headers['User-Agent'][:60]}...")
    print(f"   Sec-Ch-Ua-Mobile: {mobile_headers['Sec-Ch-Ua-Mobile']}")


if __name__ == "__main__":
    demo()
