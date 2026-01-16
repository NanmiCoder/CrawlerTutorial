# -*- coding: utf-8 -*-
"""
B站数据模型

本模块定义了 B站爬虫使用的 Pydantic 数据模型，用于：
- 数据验证：确保爬取的数据符合预期格式
- 数据序列化：方便存储为 JSON、CSV 等格式
- 类型提示：提供更好的 IDE 支持和代码可读性

数据模型说明：
- BilibiliVideo: 视频信息模型，包含视频的所有元数据
- BilibiliSearchResult: 搜索结果模型，对应 API 返回的搜索结果
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class BilibiliVideo(BaseModel):
    """
    B站视频信息模型

    该模型对应 B站视频详情 API 返回的数据结构，
    包含了视频的基本信息、统计数据和作者信息。
    """

    # ==================== 视频基本信息 ====================

    video_id: str = Field(
        description="视频 aid（旧版 ID）"
    )
    bvid: str = Field(
        description="视频 BV 号（新版 ID）"
    )
    title: str = Field(
        description="视频标题"
    )
    desc: str = Field(
        default="",
        description="视频描述/简介"
    )
    cover_url: str = Field(
        default="",
        description="视频封面图 URL"
    )
    duration: int = Field(
        default=0,
        description="视频时长（秒）"
    )
    create_time: int = Field(
        default=0,
        description="发布时间戳"
    )
    pubdate_str: str = Field(
        default="",
        description="发布时间（格式化字符串）"
    )

    # ==================== UP主信息 ====================

    user_id: int = Field(
        description="UP主 UID"
    )
    nickname: str = Field(
        default="",
        description="UP主昵称"
    )
    avatar: str = Field(
        default="",
        description="UP主头像 URL"
    )

    # ==================== 统计数据 ====================

    play_count: int = Field(
        default=0,
        description="播放量"
    )
    danmaku_count: int = Field(
        default=0,
        description="弹幕数"
    )
    comment_count: int = Field(
        default=0,
        description="评论数"
    )
    liked_count: int = Field(
        default=0,
        description="点赞数"
    )
    coin_count: int = Field(
        default=0,
        description="投币数"
    )
    favorite_count: int = Field(
        default=0,
        description="收藏数"
    )
    share_count: int = Field(
        default=0,
        description="分享数"
    )

    # ==================== 其他信息 ====================

    video_url: str = Field(
        default="",
        description="视频页面 URL"
    )
    tname: str = Field(
        default="",
        description="视频分区名称"
    )
    source_keyword: str = Field(
        default="",
        description="搜索来源关键词"
    )
    crawl_time: str = Field(
        default="",
        description="爬取时间"
    )

    def __init__(self, **data):
        """初始化时自动设置默认值"""
        # 如果没有提供 crawl_time，使用当前时间
        if 'crawl_time' not in data or not data['crawl_time']:
            data['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 如果没有提供 video_url，根据 bvid 生成
        if 'video_url' not in data or not data['video_url']:
            if 'bvid' in data:
                data['video_url'] = f"https://www.bilibili.com/video/{data['bvid']}"

        # 如果没有提供 pubdate_str，根据 create_time 生成
        if 'pubdate_str' not in data or not data['pubdate_str']:
            if 'create_time' in data and data['create_time']:
                try:
                    dt = datetime.fromtimestamp(data['create_time'])
                    data['pubdate_str'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, OSError):
                    pass

        super().__init__(**data)

    @classmethod
    def from_api_response(cls, data: dict, source_keyword: str = "") -> "BilibiliVideo":
        """
        从 API 响应数据创建 BilibiliVideo 实例

        Args:
            data: API 返回的视频详情数据
            source_keyword: 搜索来源关键词

        Returns:
            BilibiliVideo: 视频信息模型实例
        """
        # 提取作者信息
        owner = data.get("owner", {})

        # 提取统计信息
        stat = data.get("stat", {})

        return cls(
            video_id=str(data.get("aid", "")),
            bvid=data.get("bvid", ""),
            title=data.get("title", ""),
            desc=data.get("desc", ""),
            cover_url=data.get("pic", ""),
            duration=data.get("duration", 0),
            create_time=data.get("pubdate", 0),
            user_id=owner.get("mid", 0),
            nickname=owner.get("name", ""),
            avatar=owner.get("face", ""),
            play_count=stat.get("view", 0),
            danmaku_count=stat.get("danmaku", 0),
            comment_count=stat.get("reply", 0),
            liked_count=stat.get("like", 0),
            coin_count=stat.get("coin", 0),
            favorite_count=stat.get("favorite", 0),
            share_count=stat.get("share", 0),
            tname=data.get("tname", ""),
            source_keyword=source_keyword,
        )

    @classmethod
    def from_search_result(cls, data: dict, source_keyword: str = "") -> "BilibiliVideo":
        """
        从搜索结果数据创建 BilibiliVideo 实例

        搜索结果的数据结构与视频详情略有不同，需要单独处理。

        Args:
            data: API 返回的搜索结果数据
            source_keyword: 搜索关键词

        Returns:
            BilibiliVideo: 视频信息模型实例
        """
        return cls(
            video_id=str(data.get("aid", "")),
            bvid=data.get("bvid", ""),
            title=data.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
            desc=data.get("description", ""),
            cover_url="https:" + data.get("pic", "") if data.get("pic", "").startswith("//") else data.get("pic", ""),
            duration=cls._parse_duration(data.get("duration", "0:00")),
            create_time=data.get("pubdate", 0),
            user_id=data.get("mid", 0),
            nickname=data.get("author", ""),
            avatar="",  # 搜索结果中没有头像
            play_count=data.get("play", 0),
            danmaku_count=data.get("danmaku", 0),
            comment_count=data.get("review", 0),
            liked_count=data.get("like", 0),
            favorite_count=data.get("favorites", 0),
            tname=data.get("typename", ""),
            source_keyword=source_keyword,
        )

    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """
        解析时长字符串为秒数

        Args:
            duration_str: 时长字符串，如 "3:45" 或 "1:23:45"

        Returns:
            int: 时长（秒）
        """
        if isinstance(duration_str, int):
            return duration_str

        try:
            parts = str(duration_str).split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0
        except (ValueError, TypeError):
            return 0

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return self.model_dump()

    def to_csv_row(self) -> dict:
        """
        转换为适合 CSV 存储的行格式

        Returns:
            dict: CSV 行数据
        """
        return {
            "BV号": self.bvid,
            "标题": self.title,
            "UP主": self.nickname,
            "UP主ID": self.user_id,
            "播放量": self.play_count,
            "点赞数": self.liked_count,
            "投币数": self.coin_count,
            "收藏数": self.favorite_count,
            "分享数": self.share_count,
            "弹幕数": self.danmaku_count,
            "评论数": self.comment_count,
            "发布时间": self.pubdate_str,
            "视频时长(秒)": self.duration,
            "分区": self.tname,
            "描述": self.desc[:100] + "..." if len(self.desc) > 100 else self.desc,
            "视频链接": self.video_url,
            "搜索关键词": self.source_keyword,
            "爬取时间": self.crawl_time,
        }


class BilibiliSearchResponse(BaseModel):
    """
    B站搜索响应模型

    对应搜索 API 的完整响应结构。
    """

    seid: str = Field(default="", description="搜索会话 ID")
    page: int = Field(default=1, description="当前页码")
    pagesize: int = Field(default=20, description="每页数量")
    numResults: int = Field(default=0, description="搜索结果总数")
    numPages: int = Field(default=0, description="总页数")
    result: List[dict] = Field(default_factory=list, description="搜索结果列表")

    @property
    def has_more(self) -> bool:
        """是否还有更多结果"""
        return self.page < self.numPages

    def get_videos(self, source_keyword: str = "") -> List[BilibiliVideo]:
        """
        获取视频列表

        Args:
            source_keyword: 搜索关键词

        Returns:
            List[BilibiliVideo]: 视频列表
        """
        videos = []
        for item in self.result:
            try:
                video = BilibiliVideo.from_search_result(item, source_keyword)
                videos.append(video)
            except Exception:
                continue
        return videos


if __name__ == '__main__':
    # 测试代码
    print("=" * 50)
    print("数据模型测试")
    print("=" * 50)

    # 测试创建视频模型
    video = BilibiliVideo(
        video_id="123456",
        bvid="BV1xx411c7mD",
        title="测试视频标题",
        user_id=12345,
        nickname="测试UP主",
        play_count=10000,
        liked_count=500,
    )

    print(f"视频信息: {video}")
    print(f"视频 URL: {video.video_url}")
    print(f"爬取时间: {video.crawl_time}")

    # 测试 CSV 行格式
    print(f"\nCSV 行格式:")
    for key, value in video.to_csv_row().items():
        print(f"  {key}: {value}")

    # 测试从 API 响应创建
    mock_api_response = {
        "aid": 789012,
        "bvid": "BV1yy411a7bC",
        "title": "Python 入门教程",
        "desc": "这是一个 Python 入门教程视频",
        "pic": "https://example.com/cover.jpg",
        "duration": 600,
        "pubdate": 1640000000,
        "owner": {
            "mid": 54321,
            "name": "Python老师",
            "face": "https://example.com/avatar.jpg"
        },
        "stat": {
            "view": 50000,
            "danmaku": 200,
            "reply": 100,
            "like": 2000,
            "coin": 500,
            "favorite": 1000,
            "share": 300
        },
        "tname": "知识"
    }

    video2 = BilibiliVideo.from_api_response(mock_api_response, "Python教程")
    print(f"\n从 API 响应创建的视频:")
    print(f"  标题: {video2.title}")
    print(f"  UP主: {video2.nickname}")
    print(f"  播放量: {video2.play_count}")
    print(f"  发布时间: {video2.pubdate_str}")
