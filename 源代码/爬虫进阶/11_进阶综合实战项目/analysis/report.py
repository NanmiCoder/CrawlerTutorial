# -*- coding: utf-8 -*-
# @Desc: 数据分析与报告生成模块

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter
from loguru import logger

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
    }

    def __init__(self, data: List[Dict], output_dir: str = "./output"):
        """
        初始化数据分析器

        Args:
            data: 数据列表
            output_dir: 输出目录
        """
        self.data = data
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        if HAS_PANDAS:
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

            output_path = os.path.join(self.output_dir, output_file)
            wc.to_file(output_path)
            logger.info(f"词云已保存: {output_path}")
            return output_path
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


class ReportGenerator:
    """报告生成器"""

    def __init__(self, data: List[Dict], output_dir: str = "./output"):
        """
        初始化报告生成器

        Args:
            data: 数据列表
            output_dir: 输出目录
        """
        self.data = data
        self.output_dir = output_dir
        self.analyzer = DataAnalyzer(data, output_dir)
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        text_field: str = None,
        font_path: str = None,
        title: str = "数据采集分析报告"
    ) -> str:
        """
        生成完整分析报告

        Args:
            text_field: 用于词频分析的文本字段
            font_path: 字体路径
            title: 报告标题

        Returns:
            报告文件路径
        """
        lines = []

        # 标题
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 数据来源: 自动采集")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 基础统计
        stats = self.analyzer.basic_stats()
        lines.append("## 1. 基础统计")
        lines.append("")
        lines.append(f"- **数据总量**: {stats['total_records']} 条")
        lines.append(f"- **字段列表**: {', '.join(stats['fields'])}")
        lines.append("")

        # 数值字段统计
        if 'numeric_fields' in stats:
            lines.append("### 数值字段统计")
            lines.append("")
            lines.append("| 字段 | 总和 | 平均 | 最大 | 最小 |")
            lines.append("| --- | --- | --- | --- | --- |")
            for col in stats['numeric_fields']:
                lines.append(
                    f"| {col} | "
                    f"{stats.get(f'{col}_sum', 0):.2f} | "
                    f"{stats.get(f'{col}_mean', 0):.2f} | "
                    f"{stats.get(f'{col}_max', 0):.2f} | "
                    f"{stats.get(f'{col}_min', 0):.2f} |"
                )
            lines.append("")

        # 词频分析
        if text_field and HAS_JIEBA:
            lines.append("## 2. 热门词汇 TOP 20")
            lines.append("")
            word_freq = self.analyzer.word_frequency(text_field, 20)
            if word_freq:
                lines.append("| 排名 | 词汇 | 频次 |")
                lines.append("| --- | --- | --- |")
                for i, (word, count) in enumerate(word_freq, 1):
                    lines.append(f"| {i} | {word} | {count} |")
                lines.append("")

                # 生成词云
                if HAS_WORDCLOUD:
                    wordcloud_path = self.analyzer.generate_wordcloud(
                        text_field, font_path=font_path
                    )
                    if wordcloud_path:
                        lines.append("## 3. 词云图")
                        lines.append("")
                        lines.append("![词云](wordcloud.png)")
                        lines.append("")

        # 数据样本
        lines.append("## 附录: 数据样本 (前5条)")
        lines.append("")
        sample_data = self.data[:5]
        if sample_data:
            fields = list(sample_data[0].keys())
            lines.append("| " + " | ".join(fields) + " |")
            lines.append("| " + " | ".join(["---"] * len(fields)) + " |")
            for item in sample_data:
                row = []
                for f in fields:
                    val = str(item.get(f, ''))[:50]  # 截断长文本
                    val = val.replace('|', '\\|').replace('\n', ' ')
                    row.append(val)
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")

        # 保存报告
        report_content = '\n'.join(lines)
        report_path = os.path.join(self.output_dir, "report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"报告已保存: {report_path}")
        return report_path
