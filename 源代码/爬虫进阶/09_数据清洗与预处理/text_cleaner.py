# -*- coding: utf-8 -*-
# @Desc: 文本清洗工具

import re
import unicodedata
from typing import List
from loguru import logger

# 可选依赖
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False


class HTMLCleaner:
    """HTML 清洗器"""

    # 需要完全移除的标签（包括内容）
    REMOVE_TAGS = ['script', 'style', 'head', 'meta', 'link', 'noscript']

    @staticmethod
    def remove_tags(html: str) -> str:
        """
        移除所有 HTML 标签

        Args:
            html: HTML 文本

        Returns:
            纯文本
        """
        # 先移除特定标签及其内容
        for tag in HTMLCleaner.REMOVE_TAGS:
            pattern = f'<{tag}[^>]*>.*?</{tag}>'
            html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)

        # 移除所有标签
        html = re.sub(r'<[^>]+>', '', html)

        return html

    @staticmethod
    def remove_tags_keep_structure(html: str) -> str:
        """
        移除标签但保留结构（块级元素转换行）

        Args:
            html: HTML 文本

        Returns:
            保留换行结构的纯文本
        """
        # 处理块级元素，添加换行
        block_pattern = r'</(p|div|br|li|tr|h[1-6]|article|section)>'
        html = re.sub(block_pattern, '\n', html, flags=re.IGNORECASE)

        # 处理 <br> 标签
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)

        # 移除其他标签
        html = re.sub(r'<[^>]+>', '', html)

        return html

    @staticmethod
    def decode_entities(text: str) -> str:
        """
        解码 HTML 实体

        Args:
            text: 包含 HTML 实体的文本

        Returns:
            解码后的文本
        """
        import html
        return html.unescape(text)

    @staticmethod
    def clean_with_bs4(html: str) -> str:
        """
        使用 BeautifulSoup 清洗 HTML（推荐）

        Args:
            html: HTML 文本

        Returns:
            纯文本
        """
        if not HAS_BS4:
            logger.warning("BeautifulSoup 未安装，使用正则清洗")
            return HTMLCleaner.remove_tags(html)

        soup = BeautifulSoup(html, 'html.parser')

        # 移除脚本和样式
        for element in soup(['script', 'style', 'head', 'meta', 'link']):
            element.decompose()

        # 获取文本，使用换行分隔
        text = soup.get_text(separator='\n')

        return text


class WhitespaceCleaner:
    """空白字符清洗器"""

    @staticmethod
    def normalize(text: str) -> str:
        """
        标准化空白字符

        - 将制表符、回车等转为空格
        - 合并多个空格
        - 合并多个换行
        - 去除首尾空白

        Args:
            text: 输入文本

        Returns:
            标准化后的文本
        """
        # 将各种空白字符转为普通空格
        text = re.sub(r'[\t\r\f\v]', ' ', text)
        # 合并多个空格
        text = re.sub(r' +', ' ', text)
        # 合并多个换行
        text = re.sub(r'\n+', '\n', text)
        # 去除首尾空白
        return text.strip()

    @staticmethod
    def remove_all(text: str) -> str:
        """移除所有空白字符"""
        return re.sub(r'\s+', '', text)

    @staticmethod
    def trim_lines(text: str) -> str:
        """去除每行首尾空白"""
        lines = text.split('\n')
        return '\n'.join(line.strip() for line in lines)

    @staticmethod
    def remove_empty_lines(text: str) -> str:
        """移除空行"""
        lines = text.split('\n')
        return '\n'.join(line for line in lines if line.strip())

    @staticmethod
    def collapse_whitespace(text: str) -> str:
        """将所有连续空白合并为单个空格"""
        return re.sub(r'\s+', ' ', text).strip()


class SpecialCharCleaner:
    """特殊字符清洗器"""

    @staticmethod
    def remove_control_chars(text: str) -> str:
        """
        移除控制字符

        控制字符是 Unicode 类别为 'Cc' 的字符
        """
        return ''.join(
            char for char in text
            if unicodedata.category(char) != 'Cc'
        )

    @staticmethod
    def normalize_unicode(text: str, form: str = 'NFKC') -> str:
        """
        Unicode 标准化

        Args:
            text: 输入文本
            form: 标准化形式
                - NFC: 标准分解后标准合成
                - NFD: 标准分解
                - NFKC: 兼容分解后标准合成（推荐）
                - NFKD: 兼容分解

        Returns:
            标准化后的文本
        """
        return unicodedata.normalize(form, text)

    @staticmethod
    def remove_emojis(text: str) -> str:
        """移除 emoji 表情"""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 表情符号
            "\U0001F300-\U0001F5FF"  # 符号和象形文字
            "\U0001F680-\U0001F6FF"  # 交通和地图符号
            "\U0001F1E0-\U0001F1FF"  # 旗帜
            "\U00002702-\U000027B0"  # 装饰符号
            "\U000024C2-\U0001F251"  # 封闭字符
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', text)

    @staticmethod
    def to_halfwidth(text: str) -> str:
        """
        全角字符转半角

        将全角数字、字母、标点转为半角
        """
        result = []
        for char in text:
            code = ord(char)
            # 全角空格
            if code == 0x3000:
                result.append(' ')
            # 其他全角字符 (！到～)
            elif 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            else:
                result.append(char)
        return ''.join(result)

    @staticmethod
    def to_fullwidth(text: str) -> str:
        """
        半角字符转全角

        将半角数字、字母、标点转为全角
        """
        result = []
        for char in text:
            code = ord(char)
            # 空格
            if code == 0x20:
                result.append('\u3000')
            # 其他半角字符 (!到~)
            elif 0x21 <= code <= 0x7E:
                result.append(chr(code + 0xFEE0))
            else:
                result.append(char)
        return ''.join(result)

    @staticmethod
    def remove_punctuation(text: str, keep_chinese: bool = True) -> str:
        """
        移除标点符号

        Args:
            text: 输入文本
            keep_chinese: 是否保留中文标点

        Returns:
            移除标点后的文本
        """
        if keep_chinese:
            # 只移除英文标点
            return re.sub(r'[!"#$%&\'()*+,-./:;<=>?@\[\]\\^_`{|}~]', '', text)
        else:
            # 移除所有标点
            return re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)


class EncodingFixer:
    """编码问题修复器"""

    @staticmethod
    def detect_encoding(data: bytes) -> str:
        """
        检测字节数据的编码

        Args:
            data: 字节数据

        Returns:
            检测到的编码名称
        """
        if not HAS_CHARDET:
            logger.warning("chardet 未安装，默认使用 utf-8")
            return 'utf-8'

        result = chardet.detect(data)
        return result.get('encoding') or 'utf-8'

    @staticmethod
    def safe_decode(data: bytes, fallback: str = 'utf-8') -> str:
        """
        安全解码字节数据

        自动检测编码，解码失败则使用 fallback

        Args:
            data: 字节数据
            fallback: 备用编码

        Returns:
            解码后的字符串
        """
        detected = EncodingFixer.detect_encoding(data)
        try:
            return data.decode(detected)
        except (UnicodeDecodeError, TypeError, LookupError):
            return data.decode(fallback, errors='ignore')

    @staticmethod
    def fix_mojibake(text: str) -> str:
        """
        修复乱码（尝试常见编码）

        Args:
            text: 可能乱码的文本

        Returns:
            修复后的文本
        """
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']

        for encoding in encodings:
            try:
                # 尝试将文本按 latin1 编码，再用目标编码解码
                fixed = text.encode('latin1').decode(encoding)
                # 检查是否包含中文（简单验证）
                if re.search(r'[\u4e00-\u9fa5]', fixed):
                    return fixed
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue

        return text


class TextCleaner:
    """综合文本清洗器"""

    def __init__(
        self,
        remove_html: bool = True,
        normalize_whitespace: bool = True,
        normalize_unicode: bool = True,
        to_halfwidth: bool = True,
        remove_emojis: bool = False,
        remove_control_chars: bool = True
    ):
        """
        Args:
            remove_html: 是否移除 HTML 标签
            normalize_whitespace: 是否标准化空白
            normalize_unicode: 是否 Unicode 标准化
            to_halfwidth: 是否全角转半角
            remove_emojis: 是否移除 emoji
            remove_control_chars: 是否移除控制字符
        """
        self.remove_html = remove_html
        self.normalize_whitespace = normalize_whitespace
        self.normalize_unicode = normalize_unicode
        self.to_halfwidth = to_halfwidth
        self.remove_emojis = remove_emojis
        self.remove_control_chars = remove_control_chars

    def clean(self, text: str) -> str:
        """
        执行完整的文本清洗

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ''

        # 1. HTML 清洗
        if self.remove_html:
            text = HTMLCleaner.clean_with_bs4(text)
            text = HTMLCleaner.decode_entities(text)

        # 2. Unicode 标准化
        if self.normalize_unicode:
            text = SpecialCharCleaner.normalize_unicode(text, 'NFKC')

        # 3. 移除控制字符
        if self.remove_control_chars:
            text = SpecialCharCleaner.remove_control_chars(text)

        # 4. 全角转半角
        if self.to_halfwidth:
            text = SpecialCharCleaner.to_halfwidth(text)

        # 5. 移除 emoji
        if self.remove_emojis:
            text = SpecialCharCleaner.remove_emojis(text)

        # 6. 空白标准化
        if self.normalize_whitespace:
            text = WhitespaceCleaner.normalize(text)

        return text


def demo():
    """演示文本清洗功能"""
    print("=" * 50)
    print("文本清洗工具演示")
    print("=" * 50)

    # 测试数据
    test_html = """
    <html>
    <head><title>测试</title></head>
    <body>
        <script>alert('test');</script>
        <p>这是一段　　HTML　　文本。</p>
        <p>包含&amp;特殊&lt;字符&gt;。</p>
    </body>
    </html>
    """

    print("\n1. HTML 清洗:")
    print(f"   原始: {test_html[:50]}...")
    cleaned = HTMLCleaner.clean_with_bs4(test_html)
    print(f"   清洗后: {cleaned[:50]}...")

    print("\n2. 空白处理:")
    test_whitespace = "  多个   空格  \n\n\n多个换行  "
    print(f"   原始: '{test_whitespace}'")
    normalized = WhitespaceCleaner.normalize(test_whitespace)
    print(f"   标准化: '{normalized}'")

    print("\n3. 全角转半角:")
    test_fullwidth = "ＡＢＣ１２３　全角字符"
    print(f"   原始: '{test_fullwidth}'")
    halfwidth = SpecialCharCleaner.to_halfwidth(test_fullwidth)
    print(f"   半角: '{halfwidth}'")

    print("\n4. 综合清洗:")
    cleaner = TextCleaner()
    test_complex = "<p>　　复杂的　HTML&amp;文本　　</p>"
    print(f"   原始: '{test_complex}'")
    result = cleaner.clean(test_complex)
    print(f"   清洗: '{result}'")

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    demo()
