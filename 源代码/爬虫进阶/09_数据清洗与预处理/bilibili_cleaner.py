# -*- coding: utf-8 -*-
"""
B站数据清洗实战

本模块展示B站视频数据的清洗处理，包括：
- 标题清洗（移除<em>高亮标签）
- 播放量解析（支持万、亿单位）
- 时长转换（MM:SS、HH:MM:SS）
- 发布时间标准化（相对时间、时间戳、日期字符串）
- 数据去重
- 数据质量报告

这是第09章"数据清洗与预处理"的B站实战示例。

与第11章综合实战项目的关联：
- analysis/cleaner.py: 数据清洗模块
- models/video.py: 数据模型定义
"""

import re
import html
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set

from loguru import logger


# ============== B站视频数据模型 ==============

@dataclass
class BilibiliVideo:
    """
    B站视频数据模型（清洗后）

    所有字段都已标准化处理
    """
    bvid: str                          # 视频BV号
    title: str                         # 标题（纯文本）
    description: str                   # 简介（纯文本）
    owner_name: str                    # UP主名称
    owner_mid: int                     # UP主ID
    view_count: int                    # 播放量（数值）
    like_count: int                    # 点赞数
    coin_count: int                    # 投币数
    favorite_count: int                # 收藏数
    share_count: int                   # 分享数
    danmaku_count: int                 # 弹幕数
    comment_count: int                 # 评论数
    duration_seconds: int              # 时长（秒）
    publish_time: Optional[datetime]   # 发布时间
    tags: List[str] = field(default_factory=list)  # 标签列表

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "bvid": self.bvid,
            "title": self.title,
            "description": self.description,
            "owner_name": self.owner_name,
            "owner_mid": self.owner_mid,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "coin_count": self.coin_count,
            "favorite_count": self.favorite_count,
            "share_count": self.share_count,
            "danmaku_count": self.danmaku_count,
            "comment_count": self.comment_count,
            "duration_seconds": self.duration_seconds,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "tags": self.tags,
        }


# ============== B站数据清洗器 ==============

class BilibiliDataCleaner:
    """
    B站数据清洗器

    处理B站API返回的原始数据，转换为标准化格式
    """

    @staticmethod
    def clean_title(title: str) -> str:
        """
        清洗视频标题

        处理：
        - 移除搜索高亮标签 <em class="keyword">...</em>
        - 移除其他HTML标签
        - HTML实体解码
        - 标准化空白字符

        Args:
            title: 原始标题

        Returns:
            清洗后的标题
        """
        if not title:
            return ""

        # 移除 <em> 标签但保留内容
        title = re.sub(r'<em[^>]*>([^<]*)</em>', r'\1', title)
        # 移除其他HTML标签
        title = re.sub(r'<[^>]+>', '', title)
        # HTML实体解码
        title = html.unescape(title)
        # 标准化空白
        title = re.sub(r'\s+', ' ', title).strip()

        return title

    @staticmethod
    def clean_description(desc: str) -> str:
        """
        清洗视频简介

        处理：
        - 移除HTML标签
        - 保留换行结构
        - 移除过多空行

        Args:
            desc: 原始简介

        Returns:
            清洗后的简介
        """
        if not desc:
            return ""

        # 移除HTML标签
        desc = re.sub(r'<[^>]+>', '', desc)
        # HTML实体解码
        desc = html.unescape(desc)
        # 合并多个换行
        desc = re.sub(r'\n{3,}', '\n\n', desc)
        # 去除首尾空白
        desc = desc.strip()

        return desc

    @staticmethod
    def parse_view_count(view_str: Any) -> int:
        """
        解析播放量

        支持格式：
        - 15000 (int)
        - "15000" -> 15000
        - "1.5万" -> 15000
        - "3.2亿" -> 320000000
        - "1,234,567" -> 1234567

        Args:
            view_str: 播放量（可能是数字或字符串）

        Returns:
            播放量数值
        """
        if not view_str:
            return 0

        # 如果已是数字
        if isinstance(view_str, (int, float)):
            return int(view_str)

        view_str = str(view_str).strip()

        # 移除逗号
        view_str = view_str.replace(',', '')

        # 处理中文单位
        if '亿' in view_str:
            num = float(view_str.replace('亿', ''))
            return int(num * 100000000)
        elif '万' in view_str:
            num = float(view_str.replace('万', ''))
            return int(num * 10000)
        else:
            # 尝试直接转换
            try:
                return int(float(view_str))
            except ValueError:
                return 0

    @staticmethod
    def parse_duration(duration_str: Any) -> int:
        """
        解析视频时长为秒数

        支持格式：
        - 150 (已是秒数) -> 150
        - "150" -> 150
        - "02:30" -> 150
        - "1:23:45" -> 5025

        Args:
            duration_str: 时长（秒数或时间格式字符串）

        Returns:
            时长秒数
        """
        if not duration_str:
            return 0

        # 如果已经是数字，直接返回
        if isinstance(duration_str, (int, float)):
            return int(duration_str)

        duration_str = str(duration_str).strip()

        # 尝试直接转换（API返回的可能已是秒数）
        try:
            return int(duration_str)
        except ValueError:
            pass

        # 解析时:分:秒格式
        parts = duration_str.split(':')
        try:
            if len(parts) == 2:
                # MM:SS
                minutes, seconds = int(parts[0]), int(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                # HH:MM:SS
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            pass

        return 0

    @staticmethod
    def parse_publish_time(pubdate: Any) -> Optional[datetime]:
        """
        解析发布时间

        支持格式：
        - Unix时间戳 (int)
        - "刚刚", "3分钟前", "2小时前", "3天前"
        - "2024-01-15"
        - "2024-01-15 10:30:00"
        - "2024年1月15日"

        Args:
            pubdate: 发布时间（多种格式）

        Returns:
            datetime对象，解析失败返回None
        """
        if not pubdate:
            return None

        # Unix时间戳
        if isinstance(pubdate, (int, float)):
            if pubdate > 1000000000000:  # 毫秒
                pubdate = pubdate / 1000
            return datetime.fromtimestamp(pubdate)

        pubdate_str = str(pubdate).strip()
        now = datetime.now()

        # 相对时间模式
        relative_patterns = [
            (r'刚刚', lambda m: now),
            (r'(\d+)\s*秒前', lambda m: now - timedelta(seconds=int(m.group(1)))),
            (r'(\d+)\s*分钟前', lambda m: now - timedelta(minutes=int(m.group(1)))),
            (r'(\d+)\s*小时前', lambda m: now - timedelta(hours=int(m.group(1)))),
            (r'(\d+)\s*天前', lambda m: now - timedelta(days=int(m.group(1)))),
            (r'昨天', lambda m: now - timedelta(days=1)),
            (r'前天', lambda m: now - timedelta(days=2)),
        ]

        for pattern, handler in relative_patterns:
            match = re.search(pattern, pubdate_str)
            if match:
                return handler(match)

        # 绝对时间格式
        date_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
            '%Y年%m月%d日 %H:%M',
            '%Y年%m月%d日',
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(pubdate_str, fmt)
            except ValueError:
                continue

        return None

    @classmethod
    def clean_video_data(cls, raw_data: Dict[str, Any]) -> Optional[BilibiliVideo]:
        """
        清洗单条视频数据

        Args:
            raw_data: B站API返回的原始数据

        Returns:
            清洗后的BilibiliVideo对象，失败返回None
        """
        try:
            # 获取统计数据
            stat = raw_data.get('stat', {})
            owner = raw_data.get('owner', {})

            return BilibiliVideo(
                bvid=raw_data.get('bvid', ''),
                title=cls.clean_title(raw_data.get('title', '')),
                description=cls.clean_description(raw_data.get('desc', '')),
                owner_name=owner.get('name', ''),
                owner_mid=owner.get('mid', 0),
                view_count=cls.parse_view_count(stat.get('view', 0)),
                like_count=stat.get('like', 0),
                coin_count=stat.get('coin', 0),
                favorite_count=stat.get('favorite', 0),
                share_count=stat.get('share', 0),
                danmaku_count=stat.get('danmaku', 0),
                comment_count=stat.get('reply', 0),
                duration_seconds=cls.parse_duration(raw_data.get('duration', 0)),
                publish_time=cls.parse_publish_time(raw_data.get('pubdate', 0)),
                tags=raw_data.get('tags', []) if isinstance(raw_data.get('tags'), list) else [],
            )
        except Exception as e:
            logger.error(f"清洗视频数据失败: {e}")
            return None

    @classmethod
    def clean_video_list(cls, raw_list: List[Dict[str, Any]]) -> List[BilibiliVideo]:
        """
        清洗视频列表

        Args:
            raw_list: 原始数据列表

        Returns:
            清洗后的视频列表
        """
        results = []
        for raw_data in raw_list:
            video = cls.clean_video_data(raw_data)
            if video:
                results.append(video)
        return results


# ============== B站数据去重器 ==============

class BilibiliDeduplicator:
    """
    B站数据去重器

    支持多种去重策略：
    - BV号去重（精确）
    - 内容哈希去重（检测相似内容）
    """

    def __init__(self):
        self._seen_bvids: Set[str] = set()
        self._seen_hashes: Set[str] = set()

    def is_duplicate_by_bvid(self, bvid: str) -> bool:
        """
        通过BV号判断是否重复

        Args:
            bvid: 视频BV号

        Returns:
            是否重复
        """
        if bvid in self._seen_bvids:
            return True
        self._seen_bvids.add(bvid)
        return False

    def is_duplicate_by_content(self, title: str, owner_mid: int) -> bool:
        """
        通过内容哈希判断是否重复

        用于检测同一UP主发布的相似标题视频

        Args:
            title: 视频标题
            owner_mid: UP主ID

        Returns:
            是否重复
        """
        content = f"{title}|{owner_mid}"
        content_hash = hashlib.md5(content.encode()).hexdigest()

        if content_hash in self._seen_hashes:
            return True
        self._seen_hashes.add(content_hash)
        return False

    def dedupe_videos(self, videos: List[BilibiliVideo]) -> List[BilibiliVideo]:
        """
        去重视频列表

        优先使用BV号去重，同时检测内容重复

        Args:
            videos: 视频列表

        Returns:
            去重后的视频列表
        """
        results = []

        for video in videos:
            # BV号去重
            if self.is_duplicate_by_bvid(video.bvid):
                continue

            # 内容去重（可选）
            if self.is_duplicate_by_content(video.title, video.owner_mid):
                continue

            results.append(video)

        return results

    def reset(self):
        """重置去重状态"""
        self._seen_bvids.clear()
        self._seen_hashes.clear()

    @property
    def seen_count(self) -> int:
        """已处理的唯一BV号数量"""
        return len(self._seen_bvids)


# ============== 数据质量报告 ==============

@dataclass
class BilibiliDataQualityReport:
    """B站数据质量报告"""
    total_count: int           # 总记录数
    valid_count: int           # 有效记录数
    duplicate_count: int       # 重复记录数
    missing_title: int         # 缺失标题数
    missing_owner: int         # 缺失UP主数
    zero_views: int            # 零播放数
    invalid_duration: int      # 无效时长数
    invalid_pubdate: int       # 无效发布时间数

    @property
    def valid_rate(self) -> float:
        """有效率"""
        return self.valid_count / self.total_count if self.total_count > 0 else 0

    @property
    def duplicate_rate(self) -> float:
        """重复率"""
        return self.duplicate_count / self.total_count if self.total_count > 0 else 0

    def __str__(self) -> str:
        return f"""
B站数据质量报告:
  总记录数: {self.total_count}
  有效记录: {self.valid_count} ({self.valid_rate:.1%})
  重复记录: {self.duplicate_count} ({self.duplicate_rate:.1%})
  缺失标题: {self.missing_title}
  缺失UP主: {self.missing_owner}
  零播放: {self.zero_views}
  无效时长: {self.invalid_duration}
  无效发布时间: {self.invalid_pubdate}
        """.strip()


def generate_quality_report(
    videos: List[BilibiliVideo],
    duplicate_count: int = 0
) -> BilibiliDataQualityReport:
    """
    生成数据质量报告

    Args:
        videos: 清洗后的视频列表
        duplicate_count: 已去除的重复数量

    Returns:
        数据质量报告
    """
    missing_title = sum(1 for v in videos if not v.title)
    missing_owner = sum(1 for v in videos if not v.owner_name)
    zero_views = sum(1 for v in videos if v.view_count == 0)
    invalid_duration = sum(1 for v in videos if v.duration_seconds <= 0)
    invalid_pubdate = sum(1 for v in videos if v.publish_time is None)

    valid_count = sum(
        1 for v in videos
        if v.title and v.owner_name and v.view_count > 0
        and v.duration_seconds > 0 and v.publish_time
    )

    return BilibiliDataQualityReport(
        total_count=len(videos) + duplicate_count,
        valid_count=valid_count,
        duplicate_count=duplicate_count,
        missing_title=missing_title,
        missing_owner=missing_owner,
        zero_views=zero_views,
        invalid_duration=invalid_duration,
        invalid_pubdate=invalid_pubdate,
    )


# ============== 演示入口 ==============

async def demo_bilibili_data_cleaning():
    """B站数据清洗完整演示"""
    logger.info("=" * 50)
    logger.info("B站数据清洗实战演示")
    logger.info("=" * 50)

    # 模拟B站API返回的原始数据
    raw_videos = [
        {
            "bvid": "BV1xx411c7mD",
            "title": "<em class=\"keyword\">Python</em>爬虫教程 - 从入门到精通",
            "desc": "本视频介绍Python爬虫的基础知识。\n\n包含以下内容：\n1. 环境搭建\n2. 请求发送\n3. 数据解析",
            "owner": {"name": "技术UP主", "mid": 12345678},
            "stat": {
                "view": "15.6万",
                "like": 8500,
                "coin": 3200,
                "favorite": 12000,
                "share": 450,
                "danmaku": 2300,
                "reply": 680
            },
            "duration": "15:30",
            "pubdate": 1705286400  # Unix时间戳
        },
        {
            "bvid": "BV1yy411c8nM",
            "title": "B站数据分析实战 - <em class=\"keyword\">Python</em>项目",
            "desc": "使用Python分析B站热门视频数据。",
            "owner": {"name": "数据分析师", "mid": 87654321},
            "stat": {
                "view": "3.2万",
                "like": 2100,
                "coin": 890,
                "favorite": 4500,
                "share": 180,
                "danmaku": 560,
                "reply": 230
            },
            "duration": "1:05:20",
            "pubdate": "2024-01-10"
        },
        {
            "bvid": "BV1xx411c7mD",  # 重复的BV号
            "title": "<em class=\"keyword\">Python</em>爬虫教程 - 从入门到精通",
            "desc": "重复数据",
            "owner": {"name": "技术UP主", "mid": 12345678},
            "stat": {"view": "15.6万", "like": 8500, "coin": 3200, "favorite": 12000},
            "duration": "15:30",
            "pubdate": 1705286400
        },
        {
            "bvid": "BV1zz411c9pQ",
            "title": "机器学习入门教程",
            "desc": "",
            "owner": {"name": "AI老师", "mid": 11223344},
            "stat": {
                "view": "2.1亿",  # 亿级播放
                "like": 1500000,
                "coin": 800000,
                "favorite": 2000000,
            },
            "duration": 7200,  # 已是秒数
            "pubdate": "3小时前"  # 相对时间
        }
    ]

    # 1. 展示原始数据
    print("\n1. 原始数据:")
    print("-" * 40)
    for i, video in enumerate(raw_videos, 1):
        print(f"  [{i}] 标题: {video['title'][:40]}...")
        print(f"      播放: {video['stat'].get('view', 'N/A')}")
        print(f"      时长: {video.get('duration', 'N/A')}")
        print(f"      发布: {video.get('pubdate', 'N/A')}")

    # 2. 清洗数据
    print("\n2. 清洗数据...")
    print("-" * 40)
    cleaner = BilibiliDataCleaner()
    cleaned_videos = cleaner.clean_video_list(raw_videos)
    print(f"  清洗完成，共 {len(cleaned_videos)} 条记录")

    # 3. 去重
    print("\n3. 去重处理...")
    print("-" * 40)
    deduplicator = BilibiliDeduplicator()
    deduped_videos = deduplicator.dedupe_videos(cleaned_videos)
    duplicate_count = len(cleaned_videos) - len(deduped_videos)
    print(f"  去重前: {len(cleaned_videos)} 条")
    print(f"  去重后: {len(deduped_videos)} 条")
    print(f"  移除重复: {duplicate_count} 条")

    # 4. 展示清洗后数据
    print("\n4. 清洗后数据:")
    print("-" * 40)
    for i, video in enumerate(deduped_videos, 1):
        print(f"  [{i}] BV号: {video.bvid}")
        print(f"      标题: {video.title}")
        print(f"      播放量: {video.view_count:,}")
        print(f"      时长: {video.duration_seconds}秒 ({video.duration_seconds // 60}分{video.duration_seconds % 60}秒)")
        print(f"      发布时间: {video.publish_time}")
        print()

    # 5. 生成质量报告
    print("\n5. 数据质量报告:")
    print("-" * 40)
    report = generate_quality_report(deduped_videos, duplicate_count)
    print(report)


async def demo_field_cleaning():
    """演示各字段的清洗"""
    logger.info("=" * 50)
    logger.info("字段清洗演示")
    logger.info("=" * 50)

    cleaner = BilibiliDataCleaner()

    # 标题清洗
    print("\n标题清洗:")
    titles = [
        "<em class=\"keyword\">Python</em>教程",
        "B站&amp;YouTube数据分析",
        "  多余空格   的标题  ",
    ]
    for title in titles:
        print(f"  原始: {title}")
        print(f"  清洗: {cleaner.clean_title(title)}")
        print()

    # 播放量解析
    print("播放量解析:")
    views = ["15000", "1.5万", "3.2亿", "1,234,567"]
    for view in views:
        print(f"  {view} -> {cleaner.parse_view_count(view):,}")

    # 时长解析
    print("\n时长解析:")
    durations = ["02:30", "1:23:45", 150, "300"]
    for duration in durations:
        seconds = cleaner.parse_duration(duration)
        print(f"  {duration} -> {seconds}秒")

    # 发布时间解析
    print("\n发布时间解析:")
    pubdates = [1705286400, "2024-01-15", "3小时前", "刚刚"]
    for pubdate in pubdates:
        dt = cleaner.parse_publish_time(pubdate)
        print(f"  {pubdate} -> {dt}")


async def main():
    """主演示函数"""
    import asyncio

    # 完整演示
    await demo_bilibili_data_cleaning()

    print("\n" + "=" * 60)

    # 字段清洗演示
    await demo_field_cleaning()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
