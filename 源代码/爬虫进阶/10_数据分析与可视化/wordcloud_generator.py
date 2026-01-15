# -*- coding: utf-8 -*-
# @Desc: 词云生成工具
from __future__ import annotations

import os
from typing import List, Dict, Tuple, Optional
from collections import Counter
from loguru import logger

# 可选依赖
try:
    import jieba
    import jieba.analyse
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False
    logger.warning("jieba 未安装，中文分词功能不可用")

try:
    from wordcloud import WordCloud, ImageColorGenerator
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False
    logger.warning("wordcloud 未安装，词云生成功能不可用")

try:
    import numpy as np
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ChineseTokenizer:
    """中文分词器"""

    # 默认停用词
    DEFAULT_STOPWORDS = {
        '的', '是', '在', '了', '和', '与', '或', '有', '个', '人',
        '这', '那', '就', '都', '也', '为', '对', '到', '从', '把',
        '被', '让', '给', '向', '往', '于', '及', '以', '等', '不',
        '很', '会', '能', '可', '要', '我', '你', '他', '她', '它',
        '啊', '吧', '呢', '呀', '哦', '嗯', '哈', '嘿', '么', '吗',
        '什么', '怎么', '这样', '那样', '如何', '为什么', '怎样',
        '没有', '已经', '可以', '一个', '一些', '有些', '还是',
        '但是', '然后', '如果', '因为', '所以', '虽然', '而且',
        '或者', '并且', '只是', '只有', '就是', '还有', '这个',
        '那个', '自己', '什么', '这里', '那里', '这些', '那些',
    }

    def __init__(self, stopwords: set = None, user_dict: str = None):
        """
        初始化分词器

        Args:
            stopwords: 自定义停用词集合
            user_dict: 用户词典路径
        """
        if not HAS_JIEBA:
            raise ImportError("请安装 jieba: pip install jieba")

        self.stopwords = stopwords or self.DEFAULT_STOPWORDS

        if user_dict and os.path.exists(user_dict):
            jieba.load_userdict(user_dict)
            logger.info(f"加载用户词典: {user_dict}")

    def add_stopwords(self, words: List[str]):
        """添加停用词"""
        self.stopwords.update(words)

    def tokenize(self, text: str, min_length: int = 2) -> List[str]:
        """
        分词

        Args:
            text: 输入文本
            min_length: 最小词长度

        Returns:
            词语列表
        """
        words = jieba.lcut(text)
        return [
            w for w in words
            if w not in self.stopwords
            and len(w) >= min_length
            and not w.isspace()
        ]

    def extract_keywords(
        self,
        text: str,
        top_k: int = 20,
        method: str = 'tfidf'
    ) -> List[Tuple[str, float]]:
        """
        提取关键词

        Args:
            text: 输入文本
            top_k: 返回关键词数量
            method: 提取方法 ('tfidf' 或 'textrank')

        Returns:
            (关键词, 权重) 列表
        """
        if method == 'tfidf':
            return jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
        elif method == 'textrank':
            return jieba.analyse.textrank(text, topK=top_k, withWeight=True)
        else:
            raise ValueError(f"Unknown method: {method}")

    def word_frequency(
        self,
        texts: List[str],
        top_n: int = 100
    ) -> List[Tuple[str, int]]:
        """
        统计词频

        Args:
            texts: 文本列表
            top_n: 返回 Top N

        Returns:
            (词语, 频次) 列表
        """
        all_words = []
        for text in texts:
            words = self.tokenize(text)
            all_words.extend(words)

        return Counter(all_words).most_common(top_n)


class WordCloudGenerator:
    """词云生成器"""

    # 默认配色方案
    COLOR_SCHEMES = {
        'default': None,
        'viridis': 'viridis',
        'plasma': 'plasma',
        'inferno': 'inferno',
        'magma': 'magma',
        'cool': 'cool',
        'hot': 'hot',
    }

    def __init__(
        self,
        font_path: str = None,
        width: int = 800,
        height: int = 600,
        background_color: str = 'white',
        max_words: int = 200,
        max_font_size: int = 100,
        min_font_size: int = 10,
        colormap: str = None
    ):
        """
        初始化词云生成器

        Args:
            font_path: 字体路径（中文需要指定）
            width: 图片宽度
            height: 图片高度
            background_color: 背景颜色
            max_words: 最大词数
            max_font_size: 最大字体大小
            min_font_size: 最小字体大小
            colormap: matplotlib 色彩映射名称
        """
        if not HAS_WORDCLOUD:
            raise ImportError("请安装 wordcloud: pip install wordcloud")

        self.font_path = font_path
        self.width = width
        self.height = height
        self.background_color = background_color
        self.max_words = max_words
        self.max_font_size = max_font_size
        self.min_font_size = min_font_size
        self.colormap = colormap

    def _create_wordcloud(self, **kwargs) -> WordCloud:
        """创建 WordCloud 对象"""
        params = {
            'font_path': self.font_path,
            'width': self.width,
            'height': self.height,
            'background_color': self.background_color,
            'max_words': self.max_words,
            'max_font_size': self.max_font_size,
            'min_font_size': self.min_font_size,
            'colormap': self.colormap,
            'random_state': 42,
        }
        params.update(kwargs)
        return WordCloud(**params)

    def generate_from_text(self, text: str, output_path: str) -> str:
        """
        从文本生成词云

        Args:
            text: 空格分隔的词语文本
            output_path: 输出路径

        Returns:
            输出文件路径
        """
        wc = self._create_wordcloud()
        wc.generate(text)
        wc.to_file(output_path)
        logger.info(f"词云已保存: {output_path}")
        return output_path

    def generate_from_frequencies(
        self,
        frequencies: Dict[str, int],
        output_path: str
    ) -> str:
        """
        从词频字典生成词云

        Args:
            frequencies: {词语: 频次} 字典
            output_path: 输出路径

        Returns:
            输出文件路径
        """
        wc = self._create_wordcloud()
        wc.generate_from_frequencies(frequencies)
        wc.to_file(output_path)
        logger.info(f"词云已保存: {output_path}")
        return output_path

    def generate_shaped(
        self,
        text: str,
        mask_image_path: str,
        output_path: str,
        use_mask_colors: bool = True
    ) -> str:
        """
        生成自定义形状的词云

        Args:
            text: 词语文本
            mask_image_path: 形状蒙版图片路径
            output_path: 输出路径
            use_mask_colors: 是否使用蒙版图片的颜色

        Returns:
            输出文件路径
        """
        if not HAS_PIL:
            raise ImportError("请安装 pillow 和 numpy")

        # 读取蒙版
        mask = np.array(Image.open(mask_image_path))

        wc = self._create_wordcloud(
            mask=mask,
            contour_width=1,
            contour_color='steelblue'
        )

        wc.generate(text)

        # 使用蒙版颜色
        if use_mask_colors:
            image_colors = ImageColorGenerator(mask)
            wc.recolor(color_func=image_colors)

        wc.to_file(output_path)
        logger.info(f"形状词云已保存: {output_path}")
        return output_path


class TextToWordCloud:
    """从原始文本到词云的完整流程"""

    def __init__(
        self,
        font_path: str = None,
        stopwords: set = None,
        user_dict: str = None
    ):
        """
        初始化

        Args:
            font_path: 字体路径
            stopwords: 停用词
            user_dict: 用户词典
        """
        self.tokenizer = ChineseTokenizer(stopwords, user_dict)
        self.generator = WordCloudGenerator(font_path)

    def process(
        self,
        texts: List[str],
        output_path: str,
        top_words: int = 200
    ) -> str:
        """
        处理文本并生成词云

        Args:
            texts: 文本列表
            output_path: 输出路径
            top_words: 使用的词数量

        Returns:
            输出文件路径
        """
        # 1. 统计词频
        word_freq = self.tokenizer.word_frequency(texts, top_words)
        logger.info(f"统计完成: {len(word_freq)} 个词")

        # 2. 转换为字典
        freq_dict = dict(word_freq)

        # 3. 生成词云
        return self.generator.generate_from_frequencies(freq_dict, output_path)

    def get_word_stats(self, texts: List[str], top_n: int = 20) -> List[Tuple[str, int]]:
        """
        获取词频统计

        Args:
            texts: 文本列表
            top_n: 返回数量

        Returns:
            (词语, 频次) 列表
        """
        return self.tokenizer.word_frequency(texts, top_n)


def demo():
    """演示词云生成功能"""
    print("=" * 50)
    print("词云生成工具演示")
    print("=" * 50)

    if not HAS_JIEBA:
        print("请安装 jieba: pip install jieba")
        return

    if not HAS_WORDCLOUD:
        print("请安装 wordcloud: pip install wordcloud")
        return

    # 测试文本
    texts = [
        "Python是一门优雅的编程语言，适合数据分析和机器学习",
        "爬虫技术可以帮助我们获取互联网上的数据",
        "数据分析是数据科学的重要组成部分",
        "机器学习和深度学习是人工智能的核心技术",
        "Python在数据科学领域有广泛的应用",
        "爬虫需要注意遵守网站的规则和法律法规",
        "数据可视化可以帮助我们更好地理解数据",
        "编程是一项需要不断学习和实践的技能",
    ]

    # 分词
    tokenizer = ChineseTokenizer()
    print("\n1. 分词示例:")
    sample_words = tokenizer.tokenize(texts[0])
    print(f"   原文: {texts[0]}")
    print(f"   分词: {sample_words}")

    # 词频统计
    print("\n2. 词频统计 Top 10:")
    word_freq = tokenizer.word_frequency(texts, 10)
    for word, freq in word_freq:
        print(f"   {word}: {freq}")

    # 生成词云（仅打印说明，不实际生成文件）
    print("\n3. 词云生成:")
    print("   词云生成需要指定中文字体路径")
    print("   示例代码:")
    print("   generator = WordCloudGenerator(font_path='/path/to/font.ttf')")
    print("   generator.generate_from_frequencies(dict(word_freq), 'wordcloud.png')")

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    demo()
