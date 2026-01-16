# -*- coding: utf-8 -*-
"""
B站视频数据分析实战

本模块展示B站视频数据的完整分析流程，包括：
- pandas 数据处理与统计分析
- jieba 中文分词与关键词提取
- wordcloud 词云生成
- matplotlib 数据可视化
- 自动化分析报告生成

这是第10章"数据分析与可视化"的B站实战示例。

与第11章综合实战项目的关联：
- analysis/report.py: ReportGenerator 报告生成器
- analysis/wordcloud_generator.py: 词云生成模块

依赖安装：
    pip install pandas jieba wordcloud matplotlib
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import Counter

import pandas as pd
from loguru import logger

# 可选依赖：jieba 分词
try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False
    logger.warning("未安装 jieba 库，中文分词功能不可用。安装: pip install jieba")

# 可选依赖：词云生成
try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False
    logger.warning("未安装 wordcloud 库，词云生成功能不可用。安装: pip install wordcloud")

# 可选依赖：matplotlib 绑定
try:
    import matplotlib
    matplotlib.use('Agg')  # 无头模式
    import matplotlib.pyplot as plt
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'PingFang SC']
    matplotlib.rcParams['axes.unicode_minus'] = False
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("未安装 matplotlib 库，图表生成功能不可用。安装: pip install matplotlib")


# ============== B站视频数据模型 ==============

@dataclass
class BilibiliVideo:
    """
    B站视频数据模型

    用于存储清洗后的视频数据，便于分析
    """
    bvid: str
    title: str
    owner_name: str
    owner_mid: int
    view_count: int
    like_count: int
    coin_count: int
    favorite_count: int
    share_count: int
    danmaku_count: int
    comment_count: int
    duration_seconds: int
    publish_time: datetime
    tags: List[str] = field(default_factory=list)


# ============== B站停用词 ==============

BILIBILI_STOPWORDS = {
    # 通用中文停用词
    '的', '是', '在', '了', '和', '与', '或', '有', '个', '人',
    '这', '那', '就', '都', '也', '为', '对', '到', '从', '把',
    '被', '让', '给', '向', '往', '于', '及', '以', '等', '不',
    '很', '会', '能', '可', '要', '我', '你', '他', '她', '它',
    '啊', '吧', '呢', '呀', '哦', '嗯', '哈', '嘿', '吗', '么',
    '而', '但', '如', '果', '因', '所', '然', '后', '前', '上',
    '下', '中', '内', '外', '里', '时', '日', '月', '年',
    # B站特定停用词
    '视频', '合集', '第一', '第二', '第三', '更新', '最新',
    'BV', 'av', '哔哩哔哩', 'bilibili', 'UP', 'up', 'P1', 'P2',
    '一个', '什么', '怎么', '如何', '为什么', '这个', '那个',
}


# ============== 词频分析工具 ==============

def analyze_word_frequency(
    texts: List[str],
    stopwords: set = BILIBILI_STOPWORDS,
    top_n: int = 50
) -> List[tuple]:
    """
    分析文本词频

    Args:
        texts: 文本列表
        stopwords: 停用词集合
        top_n: 返回TOP N词语

    Returns:
        [(word, count), ...] 格式的词频列表
    """
    if not HAS_JIEBA:
        logger.warning("jieba 未安装，无法进行中文分词")
        return []

    all_words = []

    for text in texts:
        words = jieba.lcut(str(text))
        # 过滤停用词和单字
        words = [
            w.strip() for w in words
            if w.strip() and w not in stopwords and len(w) > 1
        ]
        all_words.extend(words)

    return Counter(all_words).most_common(top_n)


def filter_stopwords(words: List[str], stopwords: set = BILIBILI_STOPWORDS) -> List[str]:
    """过滤停用词和单字"""
    return [
        w for w in words
        if w not in stopwords and len(w) > 1
    ]


# ============== B站视频数据分析器 ==============

class BilibiliVideoAnalyzer:
    """
    B站视频数据分析器

    功能：
    - 基础统计分析（播放量、点赞量等）
    - 热门视频排行
    - UP主活跃度分析
    - 发布时间分布分析
    - 标题关键词分析
    - 词云生成
    - 自动化报告生成

    使用示例：
        videos = [...]  # BilibiliVideo 列表
        analyzer = BilibiliVideoAnalyzer(videos, "./output")
        report_path = analyzer.generate_report()
    """

    def __init__(
        self,
        videos: List[BilibiliVideo],
        output_dir: str = "./bilibili_analysis"
    ):
        """
        初始化分析器

        Args:
            videos: B站视频数据列表
            output_dir: 输出目录
        """
        self.videos = videos
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 转换为DataFrame便于分析
        self.df = pd.DataFrame([
            {
                'bvid': v.bvid,
                'title': v.title,
                'owner_name': v.owner_name,
                'owner_mid': v.owner_mid,
                'view_count': v.view_count,
                'like_count': v.like_count,
                'coin_count': v.coin_count,
                'favorite_count': v.favorite_count,
                'share_count': v.share_count,
                'danmaku_count': v.danmaku_count,
                'comment_count': v.comment_count,
                'duration_seconds': v.duration_seconds,
                'publish_time': v.publish_time,
            }
            for v in videos
        ])

        logger.info(f"分析器初始化完成，共 {len(videos)} 条视频数据")

    def basic_statistics(self) -> Dict[str, Any]:
        """
        基础统计分析

        Returns:
            统计指标字典
        """
        stats = {
            "总视频数": len(self.df),
            "独立UP主数": self.df['owner_mid'].nunique(),
            "总播放量": f"{self.df['view_count'].sum():,}",
            "平均播放量": f"{self.df['view_count'].mean():,.0f}",
            "最高播放量": f"{self.df['view_count'].max():,}",
            "总点赞数": f"{self.df['like_count'].sum():,}",
            "总投币数": f"{self.df['coin_count'].sum():,}",
            "总收藏数": f"{self.df['favorite_count'].sum():,}",
            "总弹幕数": f"{self.df['danmaku_count'].sum():,}",
            "平均时长": f"{self.df['duration_seconds'].mean() / 60:.1f} 分钟",
        }

        # 计算互动率
        total_views = self.df['view_count'].sum()
        if total_views > 0:
            total_interactions = (
                self.df['like_count'].sum() +
                self.df['coin_count'].sum() +
                self.df['favorite_count'].sum()
            )
            engagement_rate = total_interactions / total_views * 100
            stats["平均互动率"] = f"{engagement_rate:.2f}%"

        # 时间范围
        if 'publish_time' in self.df.columns:
            min_time = self.df['publish_time'].min()
            max_time = self.df['publish_time'].max()
            if pd.notna(min_time) and pd.notna(max_time):
                stats["时间范围"] = f"{min_time.strftime('%Y-%m-%d')} ~ {max_time.strftime('%Y-%m-%d')}"

        return stats

    def top_videos_by_views(self, top_n: int = 10) -> pd.DataFrame:
        """
        播放量TOP N视频

        Args:
            top_n: 返回数量

        Returns:
            视频排行DataFrame
        """
        return self.df.nlargest(top_n, 'view_count')[
            ['title', 'owner_name', 'view_count', 'like_count', 'publish_time']
        ]

    def top_videos_by_likes(self, top_n: int = 10) -> pd.DataFrame:
        """点赞数TOP N视频"""
        return self.df.nlargest(top_n, 'like_count')[
            ['title', 'owner_name', 'view_count', 'like_count', 'publish_time']
        ]

    def top_uploaders(self, top_n: int = 10) -> pd.DataFrame:
        """
        最活跃UP主（视频数量）

        Args:
            top_n: 返回数量

        Returns:
            UP主排行DataFrame
        """
        uploader_stats = self.df.groupby(['owner_mid', 'owner_name']).agg({
            'bvid': 'count',
            'view_count': 'sum',
            'like_count': 'sum'
        }).reset_index()

        uploader_stats.columns = ['owner_mid', 'owner_name', 'video_count', 'total_views', 'total_likes']
        return uploader_stats.nlargest(top_n, 'video_count')

    def top_uploaders_by_views(self, top_n: int = 10) -> pd.DataFrame:
        """总播放量TOP N UP主"""
        uploader_stats = self.df.groupby(['owner_mid', 'owner_name']).agg({
            'bvid': 'count',
            'view_count': 'sum',
            'like_count': 'sum'
        }).reset_index()

        uploader_stats.columns = ['owner_mid', 'owner_name', 'video_count', 'total_views', 'total_likes']
        return uploader_stats.nlargest(top_n, 'total_views')

    def analyze_publish_time(self) -> Dict[str, pd.Series]:
        """
        发布时间分析

        Returns:
            包含各维度时间分布的字典
        """
        df = self.df.copy()
        df['publish_time'] = pd.to_datetime(df['publish_time'])

        # 按小时分布
        df['hour'] = df['publish_time'].dt.hour
        hourly = df.groupby('hour')['bvid'].count()

        # 按星期分布
        df['weekday'] = df['publish_time'].dt.dayofweek
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        daily = df.groupby('weekday')['bvid'].count()
        daily.index = [weekday_names[i] for i in daily.index]

        # 按日期趋势
        df['date'] = df['publish_time'].dt.date
        date_trend = df.groupby('date')['bvid'].count()

        return {
            'hourly': hourly,
            'daily': daily,
            'date_trend': date_trend
        }

    def analyze_title_keywords(self, top_n: int = 50) -> List[tuple]:
        """
        标题关键词分析

        Args:
            top_n: 返回TOP N关键词

        Returns:
            [(word, count), ...] 格式的词频列表
        """
        titles = self.df['title'].tolist()
        return analyze_word_frequency(titles, BILIBILI_STOPWORDS, top_n)

    def generate_views_distribution_chart(self) -> Optional[str]:
        """
        生成播放量分布图

        Returns:
            图片路径，如果matplotlib未安装则返回None
        """
        if not HAS_MATPLOTLIB:
            logger.warning("matplotlib 未安装，跳过图表生成")
            return None

        import numpy as np

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 播放量直方图
        axes[0].hist(self.df['view_count'], bins=30, color='steelblue', edgecolor='white')
        axes[0].set_title('播放量分布', fontsize=14)
        axes[0].set_xlabel('播放量')
        axes[0].set_ylabel('视频数')

        # 播放量箱线图（对数尺度）
        log_views = np.log10(self.df['view_count'] + 1)
        axes[1].boxplot(log_views)
        axes[1].set_title('播放量分布（对数）', fontsize=14)
        axes[1].set_ylabel('log10(播放量)')

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, 'views_distribution.png')
        plt.savefig(output_path, dpi=150)
        plt.close()

        logger.info(f"播放量分布图已保存: {output_path}")
        return output_path

    def generate_publish_time_chart(self) -> Optional[str]:
        """
        生成发布时间分析图

        Returns:
            图片路径
        """
        if not HAS_MATPLOTLIB:
            return None

        time_data = self.analyze_publish_time()

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 小时分布
        axes[0, 0].bar(time_data['hourly'].index, time_data['hourly'].values, color='steelblue')
        axes[0, 0].set_title('发布时间分布（按小时）', fontsize=12)
        axes[0, 0].set_xlabel('小时')
        axes[0, 0].set_ylabel('视频数')
        axes[0, 0].set_xticks(range(0, 24, 2))

        # 星期分布
        axes[0, 1].bar(time_data['daily'].index, time_data['daily'].values, color='coral')
        axes[0, 1].set_title('发布时间分布（按星期）', fontsize=12)
        axes[0, 1].set_xlabel('星期')
        axes[0, 1].set_ylabel('视频数')

        # 日期趋势
        axes[1, 0].plot(
            time_data['date_trend'].index,
            time_data['date_trend'].values,
            marker='o', markersize=3, linewidth=1, color='green'
        )
        axes[1, 0].set_title('发布趋势', fontsize=12)
        axes[1, 0].set_xlabel('日期')
        axes[1, 0].set_ylabel('视频数')
        axes[1, 0].tick_params(axis='x', rotation=45)

        # 互动数据对比
        interaction_data = {
            '点赞': self.df['like_count'].sum(),
            '投币': self.df['coin_count'].sum(),
            '收藏': self.df['favorite_count'].sum(),
            '分享': self.df['share_count'].sum(),
        }
        axes[1, 1].bar(interaction_data.keys(), interaction_data.values(), color='purple')
        axes[1, 1].set_title('互动数据汇总', fontsize=12)
        axes[1, 1].set_ylabel('总数')

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, 'publish_time_analysis.png')
        plt.savefig(output_path, dpi=150)
        plt.close()

        logger.info(f"发布时间分析图已保存: {output_path}")
        return output_path

    def generate_title_wordcloud(self, font_path: Optional[str] = None) -> Optional[str]:
        """
        生成标题词云

        Args:
            font_path: 中文字体路径

        Returns:
            图片路径
        """
        if not HAS_WORDCLOUD:
            logger.warning("wordcloud 未安装，跳过词云生成")
            return None

        if not HAS_JIEBA:
            logger.warning("jieba 未安装，跳过词云生成")
            return None

        keywords = self.analyze_title_keywords(200)
        if not keywords:
            logger.warning("没有提取到关键词，跳过词云生成")
            return None

        freq_dict = dict(keywords)

        wc = WordCloud(
            width=1200,
            height=800,
            background_color='white',
            font_path=font_path,
            max_words=200,
            max_font_size=150,
            random_state=42,
            colormap='viridis'
        )

        wc.generate_from_frequencies(freq_dict)

        output_path = os.path.join(self.output_dir, 'title_wordcloud.png')
        wc.to_file(output_path)

        logger.info(f"标题词云已保存: {output_path}")
        return output_path

    def generate_up_ranking_chart(self, top_n: int = 15) -> Optional[str]:
        """
        生成UP主排行图

        Args:
            top_n: 显示TOP N

        Returns:
            图片路径
        """
        if not HAS_MATPLOTLIB:
            return None

        top_ups = self.top_uploaders(top_n)

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # 视频数量排行
        axes[0].barh(range(len(top_ups)), top_ups['video_count'].values, color='steelblue')
        axes[0].set_yticks(range(len(top_ups)))
        axes[0].set_yticklabels(top_ups['owner_name'].values)
        axes[0].set_title(f'视频数量 TOP {top_n} UP主', fontsize=12)
        axes[0].set_xlabel('视频数')
        axes[0].invert_yaxis()

        # 总播放量排行
        top_by_views = self.top_uploaders_by_views(top_n)

        axes[1].barh(range(len(top_by_views)), top_by_views['total_views'].values, color='coral')
        axes[1].set_yticks(range(len(top_by_views)))
        axes[1].set_yticklabels(top_by_views['owner_name'].values)
        axes[1].set_title(f'总播放量 TOP {top_n} UP主', fontsize=12)
        axes[1].set_xlabel('总播放量')
        axes[1].invert_yaxis()

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, 'up_ranking.png')
        plt.savefig(output_path, dpi=150)
        plt.close()

        logger.info(f"UP主排行图已保存: {output_path}")
        return output_path

    def generate_report(self, font_path: Optional[str] = None) -> str:
        """
        生成完整分析报告

        Args:
            font_path: 中文字体路径（用于词云）

        Returns:
            报告文件路径
        """
        report_lines = []

        # 标题
        report_lines.append("# B站视频数据分析报告")
        report_lines.append("")
        report_lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"> 数据量：{len(self.videos)} 条视频")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

        # 1. 基础统计
        stats = self.basic_statistics()
        report_lines.append("## 1. 基础统计")
        report_lines.append("")
        report_lines.append("| 指标 | 数值 |")
        report_lines.append("| --- | --- |")
        for key, value in stats.items():
            report_lines.append(f"| {key} | {value} |")
        report_lines.append("")

        # 2. 热门视频排行
        report_lines.append("## 2. 播放量 TOP 10 视频")
        report_lines.append("")
        top_videos = self.top_videos_by_views(10)
        report_lines.append("| 排名 | 标题 | UP主 | 播放量 | 点赞数 |")
        report_lines.append("| --- | --- | --- | --- | --- |")
        for i, (_, row) in enumerate(top_videos.iterrows(), 1):
            title = row['title'][:30] + '...' if len(row['title']) > 30 else row['title']
            report_lines.append(
                f"| {i} | {title} | {row['owner_name']} | "
                f"{row['view_count']:,} | {row['like_count']:,} |"
            )
        report_lines.append("")

        # 3. 关键词排行
        report_lines.append("## 3. 标题热门关键词 TOP 20")
        report_lines.append("")
        keywords = self.analyze_title_keywords(20)
        if keywords:
            report_lines.append("| 排名 | 关键词 | 出现次数 |")
            report_lines.append("| --- | --- | --- |")
            for i, (word, count) in enumerate(keywords, 1):
                report_lines.append(f"| {i} | {word} | {count} |")
        else:
            report_lines.append("*（jieba 未安装，跳过关键词分析）*")
        report_lines.append("")

        # 4. 数据可视化
        report_lines.append("## 4. 数据可视化")
        report_lines.append("")

        # 播放量分布
        views_chart = self.generate_views_distribution_chart()
        if views_chart:
            report_lines.append("### 4.1 播放量分布")
            report_lines.append(f"![播放量分布]({os.path.basename(views_chart)})")
            report_lines.append("")

        # 发布时间分析
        time_chart = self.generate_publish_time_chart()
        if time_chart:
            report_lines.append("### 4.2 发布时间分析")
            report_lines.append(f"![发布时间分析]({os.path.basename(time_chart)})")
            report_lines.append("")

        # UP主排行
        up_chart = self.generate_up_ranking_chart()
        if up_chart:
            report_lines.append("### 4.3 UP主排行")
            report_lines.append(f"![UP主排行]({os.path.basename(up_chart)})")
            report_lines.append("")

        # 标题词云
        wordcloud_path = self.generate_title_wordcloud(font_path)
        if wordcloud_path:
            report_lines.append("### 4.4 标题词云")
            report_lines.append(f"![标题词云]({os.path.basename(wordcloud_path)})")
            report_lines.append("")

        # 写入报告
        report_content = "\n".join(report_lines)
        report_path = os.path.join(self.output_dir, "bilibili_analysis_report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"B站数据分析报告已生成: {report_path}")
        return report_path


# ============== 快捷分析函数 ==============

def quick_analyze(
    videos: List[BilibiliVideo],
    output_dir: str = "./bilibili_analysis"
) -> str:
    """
    快速分析入口

    Args:
        videos: B站视频数据列表
        output_dir: 输出目录

    Returns:
        报告文件路径
    """
    analyzer = BilibiliVideoAnalyzer(videos, output_dir)
    return analyzer.generate_report()


def analyze_from_json(
    json_path: str,
    output_dir: str = "./bilibili_analysis"
) -> str:
    """
    从JSON文件加载数据并分析

    Args:
        json_path: JSON文件路径
        output_dir: 输出目录

    Returns:
        报告文件路径
    """
    import json

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    videos = []
    for item in data:
        video = BilibiliVideo(
            bvid=item.get('bvid', ''),
            title=item.get('title', ''),
            owner_name=item.get('owner_name', item.get('author', '')),
            owner_mid=item.get('owner_mid', item.get('mid', 0)),
            view_count=item.get('view_count', item.get('play', 0)),
            like_count=item.get('like_count', item.get('like', 0)),
            coin_count=item.get('coin_count', item.get('coin', 0)),
            favorite_count=item.get('favorite_count', item.get('favorites', 0)),
            share_count=item.get('share_count', item.get('share', 0)),
            danmaku_count=item.get('danmaku_count', item.get('video_review', 0)),
            comment_count=item.get('comment_count', item.get('review', 0)),
            duration_seconds=item.get('duration_seconds', item.get('duration', 0)),
            publish_time=datetime.fromisoformat(item['publish_time']) if 'publish_time' in item else datetime.now(),
            tags=item.get('tags', [])
        )
        videos.append(video)

    return quick_analyze(videos, output_dir)


# ============== 演示入口 ==============

async def demo_bilibili_analysis():
    """B站数据分析演示"""
    import random

    logger.info("=" * 50)
    logger.info("B站视频数据分析演示")
    logger.info("=" * 50)

    # 模拟B站视频数据
    sample_titles = [
        "Python爬虫从入门到精通",
        "B站数据分析实战教程",
        "机器学习入门指南",
        "数据可视化技巧分享",
        "Web开发最佳实践",
        "深度学习PyTorch教程",
        "数据清洗与预处理",
        "API接口设计规范",
        "前端Vue3教程合集",
        "后端架构设计思路",
    ]

    sample_ups = [
        ("技术UP主A", 12345678),
        ("数据分析师B", 23456789),
        ("Python教学C", 34567890),
        ("编程达人D", 45678901),
        ("全栈开发E", 56789012),
    ]

    videos = []
    base_time = datetime.now() - timedelta(days=30)

    logger.info("生成模拟数据...")
    for i in range(50):
        up_name, up_mid = random.choice(sample_ups)
        video = BilibiliVideo(
            bvid=f"BV1{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))}",
            title=f"{random.choice(sample_titles)} 第{i+1}集",
            owner_name=up_name,
            owner_mid=up_mid,
            view_count=random.randint(1000, 500000),
            like_count=random.randint(100, 20000),
            coin_count=random.randint(50, 5000),
            favorite_count=random.randint(100, 10000),
            share_count=random.randint(10, 1000),
            danmaku_count=random.randint(50, 5000),
            comment_count=random.randint(20, 2000),
            duration_seconds=random.randint(60, 3600),
            publish_time=base_time + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23)
            ),
            tags=[]
        )
        videos.append(video)

    logger.info(f"共生成 {len(videos)} 条模拟视频数据")

    # 创建分析器并生成报告
    output_dir = "./bilibili_demo_output"
    analyzer = BilibiliVideoAnalyzer(videos, output_dir)

    # 打印基础统计
    logger.info("\n--- 基础统计 ---")
    stats = analyzer.basic_statistics()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # 打印TOP 5视频
    logger.info("\n--- 播放量 TOP 5 视频 ---")
    top_videos = analyzer.top_videos_by_views(5)
    for _, row in top_videos.iterrows():
        logger.info(f"  {row['title'][:30]}... - {row['view_count']:,} 播放")

    # 打印TOP 5关键词
    keywords = analyzer.analyze_title_keywords(5)
    if keywords:
        logger.info("\n--- 标题热门关键词 TOP 5 ---")
        for word, count in keywords:
            logger.info(f"  {word}: {count} 次")

    # 生成完整报告
    logger.info("\n--- 生成分析报告 ---")
    report_path = analyzer.generate_report()

    logger.info("\n" + "=" * 50)
    logger.info(f"分析完成！报告已保存至: {report_path}")
    logger.info(f"输出目录: {output_dir}")
    logger.info("=" * 50)


async def main():
    """主演示函数"""
    await demo_bilibili_analysis()


if __name__ == "__main__":
    asyncio.run(main())
