# -*- coding: utf-8 -*-
# @Desc: 数据标准化工具

import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class DateTimeNormalizer:
    """日期时间标准化器"""

    # 常见日期格式
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y.%m.%d',
        '%Y年%m月%d日',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%m-%d-%Y',
        '%m/%d/%Y',
    ]

    # 常见日期时间格式
    DATETIME_FORMATS = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y年%m月%d日 %H:%M:%S',
        '%Y年%m月%d日 %H:%M',
        '%Y年%m月%d日 %H时%M分',
        '%Y年%m月%d日 %H时%M分%S秒',
        '%d/%m/%Y %H:%M:%S',
    ]

    @classmethod
    def parse(cls, text: str) -> Optional[datetime]:
        """
        解析日期时间字符串

        Args:
            text: 日期时间字符串

        Returns:
            datetime 对象，解析失败返回 None
        """
        text = text.strip()

        # 先尝试完整日期时间格式
        for fmt in cls.DATETIME_FORMATS:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        # 再尝试日期格式
        for fmt in cls.DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        # 尝试解析相对时间
        relative = cls.parse_relative(text)
        if relative:
            return relative

        return None

    @classmethod
    def parse_relative(cls, text: str) -> Optional[datetime]:
        """
        解析相对时间（如"3小时前"）

        Args:
            text: 相对时间字符串

        Returns:
            datetime 对象
        """
        now = datetime.now()
        text = text.strip()

        patterns = [
            (r'(\d+)\s*秒前', lambda m: now - timedelta(seconds=int(m.group(1)))),
            (r'(\d+)\s*分钟前', lambda m: now - timedelta(minutes=int(m.group(1)))),
            (r'(\d+)\s*小时前', lambda m: now - timedelta(hours=int(m.group(1)))),
            (r'(\d+)\s*天前', lambda m: now - timedelta(days=int(m.group(1)))),
            (r'(\d+)\s*周前', lambda m: now - timedelta(weeks=int(m.group(1)))),
            (r'(\d+)\s*月前', lambda m: now - timedelta(days=int(m.group(1)) * 30)),
            (r'(\d+)\s*年前', lambda m: now - timedelta(days=int(m.group(1)) * 365)),
            (r'刚刚', lambda m: now),
            (r'刚才', lambda m: now - timedelta(minutes=1)),
            (r'昨天', lambda m: now - timedelta(days=1)),
            (r'前天', lambda m: now - timedelta(days=2)),
            (r'上周', lambda m: now - timedelta(weeks=1)),
            (r'上个月', lambda m: now - timedelta(days=30)),
            (r'去年', lambda m: now - timedelta(days=365)),
        ]

        for pattern, handler in patterns:
            match = re.search(pattern, text)
            if match:
                return handler(match)

        return None

    @classmethod
    def normalize(
        cls,
        text: str,
        output_format: str = '%Y-%m-%d %H:%M:%S'
    ) -> str:
        """
        标准化日期时间格式

        Args:
            text: 日期时间字符串
            output_format: 输出格式

        Returns:
            标准化后的字符串，解析失败返回原字符串
        """
        dt = cls.parse(text)
        if dt:
            return dt.strftime(output_format)
        return text

    @classmethod
    def normalize_date(cls, text: str) -> str:
        """标准化为日期格式 (YYYY-MM-DD)"""
        return cls.normalize(text, '%Y-%m-%d')

    @classmethod
    def normalize_datetime(cls, text: str) -> str:
        """标准化为日期时间格式 (YYYY-MM-DD HH:MM:SS)"""
        return cls.normalize(text, '%Y-%m-%d %H:%M:%S')


class NumberNormalizer:
    """数值标准化器"""

    # 中文数字单位
    CHINESE_UNITS = {
        '万': 10000,
        '亿': 100000000,
        '兆': 1000000000000,
    }

    # 英文数字单位
    ENGLISH_UNITS = {
        'k': 1000,
        'K': 1000,
        'm': 1000000,
        'M': 1000000,
        'b': 1000000000,
        'B': 1000000000,
    }

    @classmethod
    def parse(cls, text: str) -> float:
        """
        解析数字字符串

        支持：
        - 逗号分隔：1,234,567
        - 中文单位：1.5万、3.2亿
        - 英文单位：1.5K、3.2M

        Args:
            text: 数字字符串

        Returns:
            数值
        """
        if not text:
            return 0.0

        text = str(text).strip()

        # 检查单位
        multiplier = 1

        # 中文单位
        for unit, value in cls.CHINESE_UNITS.items():
            if unit in text:
                multiplier = value
                text = text.replace(unit, '')
                break

        # 英文单位
        for unit, value in cls.ENGLISH_UNITS.items():
            if unit in text:
                multiplier = value
                text = text.replace(unit, '')
                break

        # 移除货币符号
        text = re.sub(r'[¥$￥€£]', '', text)

        # 移除逗号
        text = text.replace(',', '')

        # 移除空格
        text = text.replace(' ', '')

        # 提取数字
        match = re.search(r'-?\d+\.?\d*', text)
        if match:
            return float(match.group()) * multiplier

        return 0.0

    @classmethod
    def format(
        cls,
        value: float,
        precision: int = 2,
        use_units: bool = True,
        lang: str = 'zh'
    ) -> str:
        """
        格式化数字

        Args:
            value: 数值
            precision: 小数位数
            use_units: 是否使用单位
            lang: 语言 (zh/en)

        Returns:
            格式化后的字符串
        """
        if not use_units:
            return f'{value:.{precision}f}'

        if lang == 'zh':
            if abs(value) >= 100000000:
                return f'{value/100000000:.{precision}f}亿'
            elif abs(value) >= 10000:
                return f'{value/10000:.{precision}f}万'
        else:
            if abs(value) >= 1000000000:
                return f'{value/1000000000:.{precision}f}B'
            elif abs(value) >= 1000000:
                return f'{value/1000000:.{precision}f}M'
            elif abs(value) >= 1000:
                return f'{value/1000:.{precision}f}K'

        return f'{value:.{precision}f}'

    @classmethod
    def format_with_comma(cls, value: float, precision: int = 0) -> str:
        """
        使用逗号分隔的格式

        Args:
            value: 数值
            precision: 小数位数

        Returns:
            逗号分隔的数字字符串
        """
        if precision == 0:
            return f'{int(value):,}'
        return f'{value:,.{precision}f}'


class TextNormalizer:
    """文本标准化器"""

    @staticmethod
    def normalize_case(text: str, case: str = 'lower') -> str:
        """
        标准化大小写

        Args:
            text: 输入文本
            case: 大小写类型 (lower/upper/title/capitalize)

        Returns:
            标准化后的文本
        """
        if case == 'lower':
            return text.lower()
        elif case == 'upper':
            return text.upper()
        elif case == 'title':
            return text.title()
        elif case == 'capitalize':
            return text.capitalize()
        return text

    @staticmethod
    def normalize_punctuation(text: str, style: str = 'english') -> str:
        """
        标准化标点符号

        Args:
            text: 输入文本
            style: 标点风格 (chinese/english)

        Returns:
            标准化后的文本
        """
        if style == 'english':
            # 中文标点转英文
            mapping = {
                '，': ', ',
                '。': '. ',
                '！': '! ',
                '？': '? ',
                '；': '; ',
                '：': ': ',
                '"': '"',
                '"': '"',
                ''': "'",
                ''': "'",
                '（': '(',
                '）': ')',
                '【': '[',
                '】': ']',
            }
        else:
            # 英文标点转中文
            mapping = {
                ',': '，',
                '.': '。',
                '!': '！',
                '?': '？',
                ';': '；',
                ':': '：',
                '"': '"',
                "'": "'",
                '(': '（',
                ')': '）',
                '[': '【',
                ']': '】',
            }

        for old, new in mapping.items():
            text = text.replace(old, new)

        return text


class DataNormalizer:
    """综合数据标准化器"""

    def __init__(self):
        self.date_normalizer = DateTimeNormalizer()
        self.number_normalizer = NumberNormalizer()
        self.text_normalizer = TextNormalizer()

    def normalize_record(
        self,
        record: Dict[str, Any],
        date_fields: List[str] = None,
        number_fields: List[str] = None,
        text_fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        标准化数据记录

        Args:
            record: 数据记录
            date_fields: 需要标准化的日期字段
            number_fields: 需要标准化的数值字段
            text_fields: 需要标准化的文本字段

        Returns:
            标准化后的记录
        """
        result = record.copy()

        # 日期标准化
        if date_fields:
            for field in date_fields:
                if field in result and result[field]:
                    result[field] = DateTimeNormalizer.normalize_datetime(
                        str(result[field])
                    )

        # 数值标准化
        if number_fields:
            for field in number_fields:
                if field in result:
                    result[f'{field}_normalized'] = NumberNormalizer.parse(
                        str(result[field])
                    )

        # 文本标准化
        if text_fields:
            for field in text_fields:
                if field in result and result[field]:
                    result[field] = TextNormalizer.normalize_case(
                        str(result[field]).strip()
                    )

        return result

    def normalize_batch(
        self,
        records: List[Dict],
        **kwargs
    ) -> List[Dict]:
        """批量标准化"""
        return [self.normalize_record(r, **kwargs) for r in records]


def demo():
    """数据标准化演示"""
    print("=" * 50)
    print("数据标准化工具演示")
    print("=" * 50)

    # 1. 日期标准化
    print("\n1. 日期时间标准化:")
    date_tests = [
        "2024年1月15日",
        "2024/01/15",
        "15-01-2024",
        "3小时前",
        "昨天",
    ]
    for dt in date_tests:
        normalized = DateTimeNormalizer.normalize_datetime(dt)
        print(f"   '{dt}' -> '{normalized}'")

    # 2. 数值标准化
    print("\n2. 数值标准化:")
    number_tests = [
        "1,234,567",
        "1.5万",
        "3.2亿",
        "1.5K",
        "￥99.00",
        "2.5M"
    ]
    for num in number_tests:
        parsed = NumberNormalizer.parse(num)
        formatted = NumberNormalizer.format(parsed)
        print(f"   '{num}' -> {parsed} -> '{formatted}'")

    # 3. 文本标准化
    print("\n3. 文本标准化:")
    text = "HELLO world"
    print(f"   原始: '{text}'")
    print(f"   lower: '{TextNormalizer.normalize_case(text, 'lower')}'")
    print(f"   upper: '{TextNormalizer.normalize_case(text, 'upper')}'")
    print(f"   title: '{TextNormalizer.normalize_case(text, 'title')}'")

    # 4. 综合标准化
    print("\n4. 综合数据标准化:")
    test_record = {
        "title": "  Python 教程  ",
        "date": "2024年1月15日",
        "views": "1.5万",
        "price": "￥99.00"
    }
    print(f"   原始: {test_record}")

    normalizer = DataNormalizer()
    normalized = normalizer.normalize_record(
        test_record,
        date_fields=["date"],
        number_fields=["views", "price"],
        text_fields=["title"]
    )
    print(f"   标准化: {normalized}")

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    demo()
