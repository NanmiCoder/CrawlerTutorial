# -*- coding: utf-8 -*-
"""
数据分析与报告生成模块

本模块实现了 B站视频数据的分析功能，包括：
- DataAnalyzer: 数据分析器（基础统计、词频分析、分布统计）
- BilibiliAnalyzer: B站视频专用分析器
- ReportGenerator: 报告生成器（Markdown 格式）

参考 MediaCrawler 项目的数据分析实践。
"""

import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from collections import Counter
from pathlib import Path
from loguru import logger

# 尝试导入模型
try:
    from models.bilibili import BilibiliVideo
    HAS_MODEL = True
except ImportError:
    HAS_MODEL = False

# 可选依赖
try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class DataAnalyzer:
    """数据分析器"""

    # 中文停用词
    STOPWORDS = {
        '的', '是', '在', '了', '和', '与', '或', '有', '个', '人',
        '这', '那', '就', '都', '也', '为', '对', '到', '从', '把',
        '被', '让', '给', '向', '往', '于', '及', '以', '等', '不',
        '很', '会', '能', '可', '要', '我', '你', '他', '她', '它',
        '啊', '吧', '呢', '呀', '哦', '嗯', '哈', '嘿', '么', '吗',
        '什么', '怎么', '这样', '那样', '如何', '为什么', '怎样',
        '一个', '一些', '一种', '一下', '没有', '还是', '已经',
    }

    def __init__(self, data: List[Dict], output_dir: str = "./output"):
        """
        初始化数据分析器

        Args:
            data: 数据列表
            output_dir: 输出目录
        """
        self.data = data
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if HAS_PANDAS and data:
            self.df = pd.DataFrame(data)
        else:
            self.df = None

    def basic_stats(self) -> Dict[str, Any]:
        """基础统计"""
        stats = {
            'total_records': len(self.data),
            'fields': list(self.data[0].keys()) if self.data else [],
        }

        if self.df is not None:
            # 数值列统计
            numeric_cols = self.df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                stats['numeric_fields'] = numeric_cols
                for col in numeric_cols:
                    stats[f'{col}_sum'] = float(self.df[col].sum())
                    stats[f'{col}_mean'] = float(self.df[col].mean())
                    stats[f'{col}_max'] = float(self.df[col].max())
                    stats[f'{col}_min'] = float(self.df[col].min())

        return stats

    def word_frequency(
        self,
        text_field: str,
        top_n: int = 50,
        min_length: int = 2
    ) -> List[tuple]:
        """
        词频统计

        Args:
            text_field: 文本字段名
            top_n: 返回 Top N
            min_length: 最小词长度

        Returns:
            (词语, 频次) 列表
        """
        if not HAS_JIEBA:
            logger.warning("jieba 未安装，跳过词频分析")
            return []

        all_words = []
        for item in self.data:
            text = item.get(text_field, '')
            if text:
                words = jieba.lcut(str(text))
                words = [
                    w for w in words
                    if w not in self.STOPWORDS
                    and len(w) >= min_length
                    and not w.isspace()
                ]
                all_words.extend(words)

        return Counter(all_words).most_common(top_n)

    def generate_wordcloud(
        self,
        text_field: str,
        output_file: str = "wordcloud.png",
        font_path: str = None,
        width: int = 1200,
        height: int = 800
    ) -> Optional[str]:
        """
        生成词云

        Args:
            text_field: 文本字段名
            output_file: 输出文件名
            font_path: 字体路径（中文需要指定）
            width: 图片宽度
            height: 图片高度

        Returns:
            输出文件路径，失败返回 None
        """
        if not HAS_WORDCLOUD:
            logger.warning("wordcloud 未安装，跳过词云生成")
            return None

        word_freq = self.word_frequency(text_field, 200)
        if not word_freq:
            logger.warning("没有词频数据，跳过词云生成")
            return None

        freq_dict = dict(word_freq)

        try:
            wc = WordCloud(
                width=width,
                height=height,
                background_color='white',
                font_path=font_path,
                max_words=200,
                max_font_size=150,
                random_state=42
            )

            wc.generate_from_frequencies(freq_dict)

            output_path = self.output_dir / output_file
            wc.to_file(str(output_path))
            logger.info(f"词云已保存: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"生成词云失败: {e}")
            return None

    def value_distribution(self, field: str) -> Dict[Any, int]:
        """
        值分布统计

        Args:
            field: 字段名

        Returns:
            {值: 计数} 字典
        """
        counter = Counter()
        for item in self.data:
            value = item.get(field)
            if value is not None:
                counter[value] += 1
        return dict(counter)


class BilibiliAnalyzer(DataAnalyzer):
    """
    B站视频数据分析器

    提供针对 B站视频数据的专用分析方法。
    """

    def __init__(
        self,
        videos: List[Union[Dict, "BilibiliVideo"]],
        output_dir: str = "./output"
    ):
        """
        初始化 B站分析器

        Args:
            videos: 视频数据列表（BilibiliVideo 或字典）
            output_dir: 输出目录
        """
        # 转换为字典列表
        data = []
        for video in videos:
            if HAS_MODEL and isinstance(video, BilibiliVideo):
                data.append(video.to_dict())
            elif hasattr(video, 'model_dump'):
                data.append(video.model_dump())
            elif isinstance(video, dict):
                data.append(video)
            else:
                data.append(dict(video))

        super().__init__(data, output_dir)

    def video_metrics_stats(self) -> Dict[str, Any]:
        """
        视频指标统计

        统计播放量、点赞、收藏、投币等指标。

        Returns:
            统计结果字典
        """
        metrics = {
            'play_count': [],
            'liked_count': [],
            'coin_count': [],
            'favorite_count': [],
            'share_count': [],
            'danmaku_count': [],
            'comment_count': [],
        }

        for item in self.data:
            for key in metrics.keys():
                value = item.get(key, 0)
                if value is not None:
                    try:
                        metrics[key].append(int(value))
                    except (ValueError, TypeError):
                        metrics[key].append(0)

        stats = {}
        for key, values in metrics.items():
            if values:
                stats[key] = {
                    'total': sum(values),
                    'avg': sum(values) / len(values),
                    'max': max(values),
                    'min': min(values),
                }

        return stats

    def up_distribution(self, top_n: int = 10) -> List[tuple]:
        """
        UP主分布统计

        Args:
            top_n: 返回 Top N

        Returns:
            [(UP主昵称, 视频数量)] 列表
        """
        counter = Counter()
        for item in self.data:
            nickname = item.get('nickname', '未知UP主')
            if nickname:
                counter[nickname] += 1
        return counter.most_common(top_n)

    def keyword_distribution(self) -> Dict[str, int]:
        """
        搜索关键词分布统计

        Returns:
            {关键词: 视频数量} 字典
        """
        counter = Counter()
        for item in self.data:
            keyword = item.get('source_keyword', '')
            if keyword:
                counter[keyword] += 1
        return dict(counter)

    def top_videos(
        self,
        metric: str = 'play_count',
        top_n: int = 10
    ) -> List[Dict]:
        """
        获取指标排名前 N 的视频

        Args:
            metric: 排序指标（play_count, liked_count 等）
            top_n: 返回数量

        Returns:
            视频列表
        """
        sorted_data = sorted(
            self.data,
            key=lambda x: x.get(metric, 0) or 0,
            reverse=True
        )
        return sorted_data[:top_n]

    def generate_title_wordcloud(
        self,
        output_file: str = "title_wordcloud.png",
        font_path: str = None
    ) -> Optional[str]:
        """
        生成视频标题词云

        Args:
            output_file: 输出文件名
            font_path: 字体路径

        Returns:
            输出文件路径
        """
        return self.generate_wordcloud(
            text_field='title',
            output_file=output_file,
            font_path=font_path
        )


class ReportGenerator:
    """
    报告生成器

    生成 B站视频数据的 Markdown 格式分析报告。
    """

    def __init__(
        self,
        videos: List[Union[Dict, "BilibiliVideo"]],
        output_dir: str = "./output"
    ):
        """
        初始化报告生成器

        Args:
            videos: 视频数据列表
            output_dir: 输出目录
        """
        self.videos = videos
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 创建分析器
        self.analyzer = BilibiliAnalyzer(videos, output_dir)

    def generate(
        self,
        font_path: str = None,
        title: str = "B站视频数据分析报告"
    ) -> str:
        """
        生成完整分析报告

        Args:
            font_path: 字体路径（词云使用）
            title: 报告标题

        Returns:
            报告文件路径
        """
        lines = []

        # 标题
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 数据来源: B站视频采集")
        lines.append(f"> 数据量: {len(self.analyzer.data)} 条")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 1. 视频指标统计
        lines.append("## 1. 视频指标统计")
        lines.append("")
        metrics_stats = self.analyzer.video_metrics_stats()
        if metrics_stats:
            lines.append("| 指标 | 总计 | 平均 | 最高 | 最低 |")
            lines.append("| --- | ---: | ---: | ---: | ---: |")

            metric_names = {
                'play_count': '播放量',
                'liked_count': '点赞数',
                'coin_count': '投币数',
                'favorite_count': '收藏数',
                'share_count': '分享数',
                'danmaku_count': '弹幕数',
                'comment_count': '评论数',
            }

            for key, name in metric_names.items():
                if key in metrics_stats:
                    stat = metrics_stats[key]
                    lines.append(
                        f"| {name} | "
                        f"{stat['total']:,} | "
                        f"{stat['avg']:,.0f} | "
                        f"{stat['max']:,} | "
                        f"{stat['min']:,} |"
                    )
            lines.append("")

        # 2. 热门视频 TOP 10
        lines.append("## 2. 热门视频 TOP 10（按播放量）")
        lines.append("")
        top_videos = self.analyzer.top_videos('play_count', 10)
        if top_videos:
            lines.append("| 排名 | 标题 | UP主 | 播放量 | 点赞 |")
            lines.append("| --- | --- | --- | ---: | ---: |")
            for i, video in enumerate(top_videos, 1):
                title_short = video.get('title', '')[:30]
                if len(video.get('title', '')) > 30:
                    title_short += '...'
                lines.append(
                    f"| {i} | {title_short} | "
                    f"{video.get('nickname', '未知')} | "
                    f"{video.get('play_count', 0):,} | "
                    f"{video.get('liked_count', 0):,} |"
                )
            lines.append("")

        # 3. UP主分布
        lines.append("## 3. UP主分布 TOP 10")
        lines.append("")
        up_dist = self.analyzer.up_distribution(10)
        if up_dist:
            lines.append("| 排名 | UP主 | 视频数 |")
            lines.append("| --- | --- | ---: |")
            for i, (name, count) in enumerate(up_dist, 1):
                lines.append(f"| {i} | {name} | {count} |")
            lines.append("")

        # 4. 关键词分布
        keyword_dist = self.analyzer.keyword_distribution()
        if keyword_dist and len(keyword_dist) > 1:
            lines.append("## 4. 搜索关键词分布")
            lines.append("")
            lines.append("| 关键词 | 视频数 |")
            lines.append("| --- | ---: |")
            for keyword, count in sorted(
                keyword_dist.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                lines.append(f"| {keyword} | {count} |")
            lines.append("")

        # 5. 标题热词 TOP 20
        if HAS_JIEBA:
            lines.append("## 5. 标题热词 TOP 20")
            lines.append("")
            word_freq = self.analyzer.word_frequency('title', 20)
            if word_freq:
                lines.append("| 排名 | 词汇 | 频次 |")
                lines.append("| --- | --- | ---: |")
                for i, (word, count) in enumerate(word_freq, 1):
                    lines.append(f"| {i} | {word} | {count} |")
                lines.append("")

                # 生成词云
                if HAS_WORDCLOUD:
                    wordcloud_path = self.analyzer.generate_title_wordcloud(
                        font_path=font_path
                    )
                    if wordcloud_path:
                        lines.append("### 标题词云")
                        lines.append("")
                        lines.append("![标题词云](title_wordcloud.png)")
                        lines.append("")

        # 6. 数据样本
        lines.append("## 附录: 数据样本 (前5条)")
        lines.append("")
        sample_fields = ['bvid', 'title', 'nickname', 'play_count', 'liked_count']
        sample_data = self.analyzer.data[:5]
        if sample_data:
            lines.append("| " + " | ".join(sample_fields) + " |")
            lines.append("| " + " | ".join(["---"] * len(sample_fields)) + " |")
            for item in sample_data:
                row = []
                for f in sample_fields:
                    val = str(item.get(f, ''))[:40]
                    val = val.replace('|', '\\|').replace('\n', ' ')
                    row.append(val)
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")

        # 保存报告
        report_content = '\n'.join(lines)
        report_path = self.output_dir / "report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"报告已保存: {report_path}")
        return str(report_path)


# 便捷函数
def generate_report(
    videos: List[Union[Dict, "BilibiliVideo"]],
    output_dir: str = "./output",
    font_path: str = None
) -> str:
    """
    生成分析报告（便捷函数）

    Args:
        videos: 视频数据列表
        output_dir: 输出目录
        font_path: 字体路径

    Returns:
        报告文件路径
    """
    generator = ReportGenerator(videos, output_dir)
    return generator.generate(font_path=font_path)


if __name__ == '__main__':
    # 测试代码
    test_data = [
        {
            'bvid': 'BV1234567890',
            'title': 'Python 爬虫入门教程',
            'nickname': '技术UP主',
            'play_count': 10000,
            'liked_count': 500,
            'coin_count': 200,
            'favorite_count': 300,
            'share_count': 50,
            'danmaku_count': 100,
            'comment_count': 80,
            'source_keyword': 'Python教程',
        },
        {
            'bvid': 'BV0987654321',
            'title': 'Python 数据分析实战',
            'nickname': '数据分析师',
            'play_count': 8000,
            'liked_count': 400,
            'coin_count': 150,
            'favorite_count': 250,
            'share_count': 30,
            'danmaku_count': 80,
            'comment_count': 60,
            'source_keyword': 'Python教程',
        },
    ]

    report_path = generate_report(test_data, './test_output')
    print(f"报告已生成: {report_path}")
