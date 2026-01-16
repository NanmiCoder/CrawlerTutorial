# -*- coding: utf-8 -*-
"""
B站 WBI 签名工具

本模块实现了 B站 API 请求的 WBI 签名算法，用于防止接口被滥用。
WBI 签名是 B站 API 的一种保护机制，需要在请求参数中添加 wts（时间戳）和 w_rid（签名）。

签名算法说明：
1. 从浏览器的 localStorage 中获取 wbi_img_urls，包含 img_url 和 sub_url
2. 从这两个 URL 中提取 img_key 和 sub_key
3. 将两个 key 拼接后，按照混淆映射表重新排列，取前32位作为 salt
4. 将请求参数按 key 排序，URL 编码后与 salt 拼接
5. 计算 MD5 哈希值作为 w_rid

参考资料：
- https://socialsisteryi.github.io/bilibili-API-collect/docs/misc/sign/wbi.html
"""

import re
import time
import urllib.parse
from hashlib import md5
from typing import Dict, Optional
from dataclasses import dataclass


# WBI 签名混淆映射表（固定值，从 B站 JS 代码中逆向得到）
WBI_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


@dataclass
class VideoUrlInfo:
    """视频 URL 信息"""
    video_id: str  # BV 号
    video_type: str = "video"


@dataclass
class CreatorUrlInfo:
    """创作者 URL 信息"""
    creator_id: str  # UID


class BilibiliSign:
    """
    B站 WBI 签名类

    使用方法：
    ```python
    # 创建签名实例（需要先从浏览器获取 img_key 和 sub_key）
    signer = BilibiliSign(img_key="xxx", sub_key="yyy")

    # 对请求参数进行签名
    params = {"keyword": "Python教程", "page": 1}
    signed_params = signer.sign(params)
    # signed_params 会包含 wts 和 w_rid
    ```
    """

    def __init__(self, img_key: str, sub_key: str):
        """
        初始化签名器

        Args:
            img_key: 从 wbi_img_urls 中提取的 img_key
            sub_key: 从 wbi_img_urls 中提取的 sub_key
        """
        self.img_key = img_key
        self.sub_key = sub_key

    def get_salt(self) -> str:
        """
        生成混淆后的 salt

        算法：
        1. 将 img_key 和 sub_key 拼接
        2. 按照映射表重新排列字符
        3. 取前 32 位作为 salt

        Returns:
            str: 32位的 salt 字符串
        """
        salt = ""
        mixin_key = self.img_key + self.sub_key
        for index in WBI_MIXIN_KEY_ENC_TAB:
            salt += mixin_key[index]
        return salt[:32]

    def sign(self, req_data: Dict) -> Dict:
        """
        对请求参数进行签名

        签名流程：
        1. 添加当前时间戳 wts
        2. 按 key 字典序排序
        3. 过滤特殊字符
        4. URL 编码后与 salt 拼接
        5. 计算 MD5 作为 w_rid

        Args:
            req_data: 原始请求参数

        Returns:
            Dict: 签名后的请求参数（包含 wts 和 w_rid）
        """
        # 复制参数，避免修改原始数据
        params = req_data.copy()

        # 添加当前时间戳（秒级）
        current_ts = int(time.time())
        params["wts"] = current_ts

        # 按 key 字典序排序
        params = dict(sorted(params.items()))

        # 过滤特殊字符 !'()*
        params = {
            k: ''.join(filter(lambda ch: ch not in "!'()*", str(v)))
            for k, v in params.items()
        }

        # URL 编码
        query = urllib.parse.urlencode(params)

        # 获取 salt 并计算签名
        salt = self.get_salt()
        w_rid = md5((query + salt).encode()).hexdigest()

        # 添加签名到参数
        params['w_rid'] = w_rid

        return params


def extract_wbi_keys_from_urls(img_url: str, sub_url: str) -> tuple:
    """
    从 wbi_img_urls 中提取 img_key 和 sub_key

    Args:
        img_url: img_url 完整地址
        sub_url: sub_url 完整地址

    Returns:
        tuple: (img_key, sub_key)

    Example:
        img_url = "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png"
        sub_url = "https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png"
        # 返回 ("7cd084941338484aae1ad9425b84077c", "4932caff0ff746eab6f01bf08b70ac45")
    """
    # 从 URL 中提取文件名（不含扩展名）
    img_key = img_url.rsplit('/', 1)[-1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[-1].split('.')[0]
    return img_key, sub_key


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    从 B站视频 URL 中解析视频 ID

    支持的格式：
    - https://www.bilibili.com/video/BV1dwuKzmE26/?spm_id_from=...
    - https://www.bilibili.com/video/BV1d54y1g7db
    - BV1d54y1g7db（直接传入 BV 号）

    Args:
        url: B站视频链接或 BV 号

    Returns:
        VideoUrlInfo: 包含视频 ID 的对象

    Raises:
        ValueError: 无法解析视频 ID
    """
    # 如果直接是 BV 号，直接返回
    if url.startswith("BV"):
        return VideoUrlInfo(video_id=url)

    # 使用正则提取 BV 号
    bv_pattern = r'/video/(BV[a-zA-Z0-9]+)'
    match = re.search(bv_pattern, url)

    if match:
        video_id = match.group(1)
        return VideoUrlInfo(video_id=video_id)

    raise ValueError(f"无法从 URL 解析视频 ID: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    从 B站用户空间 URL 中解析用户 ID

    支持的格式：
    - https://space.bilibili.com/434377496?spm_id_from=...
    - https://space.bilibili.com/20813884
    - 434377496（直接传入 UID）

    Args:
        url: B站用户空间链接或 UID

    Returns:
        CreatorUrlInfo: 包含用户 ID 的对象

    Raises:
        ValueError: 无法解析用户 ID
    """
    # 如果直接是数字 ID，直接返回
    if url.isdigit():
        return CreatorUrlInfo(creator_id=url)

    # 使用正则提取 UID
    uid_pattern = r'space\.bilibili\.com/(\d+)'
    match = re.search(uid_pattern, url)

    if match:
        creator_id = match.group(1)
        return CreatorUrlInfo(creator_id=creator_id)

    raise ValueError(f"无法从 URL 解析用户 ID: {url}")


if __name__ == '__main__':
    # 测试代码
    print("=" * 50)
    print("WBI 签名测试")
    print("=" * 50)

    # 模拟从浏览器获取的 key
    test_img_key = "7cd084941338484aae1ad9425b84077c"
    test_sub_key = "4932caff0ff746eab6f01bf08b70ac45"

    signer = BilibiliSign(test_img_key, test_sub_key)
    print(f"Salt: {signer.get_salt()}")

    # 测试签名
    test_params = {"keyword": "Python教程", "page": 1, "search_type": "video"}
    signed_params = signer.sign(test_params)
    print(f"原始参数: {test_params}")
    print(f"签名参数: {signed_params}")

    print("\n" + "=" * 50)
    print("URL 解析测试")
    print("=" * 50)

    # 测试视频 URL 解析
    video_urls = [
        "https://www.bilibili.com/video/BV1dwuKzmE26/?spm_id_from=333.1387",
        "BV1d54y1g7db",
    ]
    for url in video_urls:
        try:
            info = parse_video_info_from_url(url)
            print(f"视频 URL: {url} -> {info}")
        except ValueError as e:
            print(f"解析失败: {e}")

    # 测试创作者 URL 解析
    creator_urls = [
        "https://space.bilibili.com/434377496?spm_id_from=333.1007.0.0",
        "20813884",
    ]
    for url in creator_urls:
        try:
            info = parse_creator_info_from_url(url)
            print(f"创作者 URL: {url} -> {info}")
        except ValueError as e:
            print(f"解析失败: {e}")
