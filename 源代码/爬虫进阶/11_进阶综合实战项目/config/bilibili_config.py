# -*- coding: utf-8 -*-
"""
B站特定配置

本模块包含 B站 API 相关的常量和配置，包括：
- API 端点地址
- 请求头配置
- WBI 签名相关常量
- 搜索排序类型
"""

from enum import Enum


class SearchOrderType(str, Enum):
    """搜索排序类型"""
    DEFAULT = ""           # 综合排序
    MOST_CLICK = "click"   # 最多点击
    LAST_PUBLISH = "pubdate"  # 最新发布
    MOST_DANMU = "dm"      # 最多弹幕
    MOST_MARK = "stow"     # 最多收藏


# ==================== API 端点 ====================

# B站主站
BILIBILI_URL = "https://www.bilibili.com"

# 搜索 API
SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"

# 视频详情 API
VIDEO_INFO_URL = "https://api.bilibili.com/x/web-interface/view"

# 视频播放地址 API
VIDEO_PLAY_URL = "https://api.bilibili.com/x/player/playurl"

# 用户信息 API
USER_INFO_URL = "https://api.bilibili.com/x/space/wbi/acc/info"


# ==================== 请求头配置 ====================

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.bilibili.com",
}


# ==================== WBI 签名相关 ====================

# WBI 签名混淆映射表（固定值）
WBI_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


# ==================== 登录相关 ====================

# 登录页面 URL
LOGIN_URL = "https://www.bilibili.com"

# 登录按钮选择器
LOGIN_BUTTON_SELECTOR = "xpath=//div[@class='right-entry__outside go-login-btn']//div"

# 二维码选择器
QRCODE_SELECTOR = "//div[@class='login-scan-box']//img"

# 登录成功后的 Cookie 关键字段
LOGIN_COOKIE_KEYS = ["SESSDATA", "DedeUserID", "bili_jct"]


# ==================== 页面选择器 ====================

# 搜索结果项选择器
SEARCH_ITEM_SELECTOR = ".video-list-item"

# 视频标题选择器
VIDEO_TITLE_SELECTOR = ".title"

# 视频播放量选择器
VIDEO_PLAY_COUNT_SELECTOR = ".play-count"


# ==================== 其他配置 ====================

# 每页搜索结果数量（B站固定值）
SEARCH_PAGE_SIZE = 20

# 最大重试次数
MAX_RETRY_COUNT = 3

# 请求超时时间（秒）
REQUEST_TIMEOUT = 10
