# -*- coding: utf-8 -*-
# @Desc: 数据去重工具

import hashlib
from typing import List, Dict, Any, Callable, Set
from loguru import logger


class ExactDeduplicator:
    """精确去重器"""

    @staticmethod
    def dedupe_list(items: List[str]) -> List[str]:
        """
        列表去重（保持顺序）

        Args:
            items: 字符串列表

        Returns:
            去重后的列表
        """
        seen: Set[str] = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def dedupe_dicts_by_field(
        items: List[Dict],
        key_field: str
    ) -> List[Dict]:
        """
        根据单个字段去重

        Args:
            items: 字典列表
            key_field: 用于去重的字段名

        Returns:
            去重后的列表
        """
        seen: Set[Any] = set()
        result = []
        for item in items:
            key = item.get(key_field)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def dedupe_by_hash(
        items: List[Dict],
        fields: List[str]
    ) -> List[Dict]:
        """
        根据多个字段计算哈希去重

        Args:
            items: 数据列表
            fields: 用于计算哈希的字段列表

        Returns:
            去重后的列表
        """
        seen: Set[str] = set()
        result = []

        for item in items:
            # 构建哈希键
            key_parts = [str(item.get(f, '')) for f in fields]
            key_str = '|'.join(key_parts)
            key_hash = hashlib.md5(key_str.encode()).hexdigest()

            if key_hash not in seen:
                seen.add(key_hash)
                result.append(item)

        return result

    @staticmethod
    def dedupe_by_callback(
        items: List[Any],
        key_func: Callable[[Any], Any]
    ) -> List[Any]:
        """
        使用自定义函数生成键进行去重

        Args:
            items: 数据列表
            key_func: 生成去重键的函数

        Returns:
            去重后的列表
        """
        seen: Set[Any] = set()
        result = []

        for item in items:
            key = key_func(item)
            if key not in seen:
                seen.add(key)
                result.append(item)

        return result


class FuzzyDeduplicator:
    """模糊去重器（基于相似度）"""

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        计算编辑距离（Levenshtein Distance）

        编辑距离是将一个字符串转换为另一个所需的最少操作数

        Args:
            s1: 字符串1
            s2: 字符串2

        Returns:
            编辑距离
        """
        if len(s1) < len(s2):
            return FuzzyDeduplicator.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))

        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # 插入、删除、替换的代价
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def similarity(s1: str, s2: str) -> float:
        """
        计算两个字符串的相似度

        相似度 = 1 - (编辑距离 / 最大长度)

        Args:
            s1: 字符串1
            s2: 字符串2

        Returns:
            相似度 (0.0 - 1.0)
        """
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        distance = FuzzyDeduplicator.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        return 1 - distance / max_len

    @staticmethod
    def jaccard_similarity(s1: str, s2: str) -> float:
        """
        计算 Jaccard 相似度（基于字符集合）

        Jaccard = |A ∩ B| / |A ∪ B|

        Args:
            s1: 字符串1
            s2: 字符串2

        Returns:
            Jaccard 相似度 (0.0 - 1.0)
        """
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        set1 = set(s1)
        set2 = set(s2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def dedupe_fuzzy(
        items: List[str],
        threshold: float = 0.8,
        similarity_func: str = "levenshtein"
    ) -> List[str]:
        """
        模糊去重

        Args:
            items: 字符串列表
            threshold: 相似度阈值 (0.0 - 1.0)
            similarity_func: 相似度算法 (levenshtein/jaccard)

        Returns:
            去重后的列表
        """
        if not items:
            return []

        # 选择相似度函数
        if similarity_func == "jaccard":
            sim_func = FuzzyDeduplicator.jaccard_similarity
        else:
            sim_func = FuzzyDeduplicator.similarity

        result = [items[0]]

        for item in items[1:]:
            is_duplicate = False
            for existing in result:
                if sim_func(item, existing) >= threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                result.append(item)

        return result

    @staticmethod
    def dedupe_dicts_fuzzy(
        items: List[Dict],
        text_field: str,
        threshold: float = 0.8
    ) -> List[Dict]:
        """
        根据文本字段进行模糊去重

        Args:
            items: 字典列表
            text_field: 用于比较的文本字段
            threshold: 相似度阈值

        Returns:
            去重后的列表
        """
        if not items:
            return []

        result = [items[0]]

        for item in items[1:]:
            item_text = item.get(text_field, '')
            is_duplicate = False

            for existing in result:
                existing_text = existing.get(text_field, '')
                if FuzzyDeduplicator.similarity(item_text, existing_text) >= threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                result.append(item)

        return result


class ContentDeduplicator:
    """基于内容特征的去重器"""

    @staticmethod
    def get_content_hash(text: str, normalize: bool = True) -> str:
        """
        计算内容哈希

        Args:
            text: 文本内容
            normalize: 是否标准化（去除空白等）

        Returns:
            MD5 哈希值
        """
        if normalize:
            # 移除空白字符
            text = ''.join(text.split())
            # 转小写
            text = text.lower()

        return hashlib.md5(text.encode()).hexdigest()

    @staticmethod
    def get_simhash(text: str, bits: int = 64) -> int:
        """
        计算 SimHash（用于大规模去重）

        SimHash 是一种局部敏感哈希，相似文本的哈希值相近

        Args:
            text: 文本内容
            bits: 哈希位数

        Returns:
            SimHash 值
        """
        # 分词（简单按字符）
        features = list(text)

        # 计算每个特征的哈希
        v = [0] * bits
        for feature in features:
            h = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            for i in range(bits):
                bitmask = 1 << i
                if h & bitmask:
                    v[i] += 1
                else:
                    v[i] -= 1

        # 生成最终哈希
        fingerprint = 0
        for i in range(bits):
            if v[i] >= 0:
                fingerprint |= (1 << i)

        return fingerprint

    @staticmethod
    def hamming_distance(hash1: int, hash2: int) -> int:
        """
        计算汉明距离

        Args:
            hash1: 哈希值1
            hash2: 哈希值2

        Returns:
            汉明距离（不同位的数量）
        """
        x = hash1 ^ hash2
        distance = 0
        while x:
            distance += 1
            x &= x - 1
        return distance

    @staticmethod
    def dedupe_by_simhash(
        items: List[Dict],
        text_field: str,
        threshold: int = 3
    ) -> List[Dict]:
        """
        使用 SimHash 去重

        适用于大规模文本去重

        Args:
            items: 字典列表
            text_field: 文本字段名
            threshold: 汉明距离阈值（小于此值视为重复）

        Returns:
            去重后的列表
        """
        if not items:
            return []

        result = []
        hashes = []

        for item in items:
            text = item.get(text_field, '')
            item_hash = ContentDeduplicator.get_simhash(text)

            is_duplicate = False
            for existing_hash in hashes:
                if ContentDeduplicator.hamming_distance(item_hash, existing_hash) <= threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                result.append(item)
                hashes.append(item_hash)

        return result


def demo():
    """去重工具演示"""
    print("=" * 50)
    print("数据去重工具演示")
    print("=" * 50)

    # 1. 精确去重
    print("\n1. 精确去重:")
    test_list = ["apple", "banana", "apple", "cherry", "banana"]
    print(f"   原始: {test_list}")
    deduped = ExactDeduplicator.dedupe_list(test_list)
    print(f"   去重: {deduped}")

    # 2. 字典列表去重
    print("\n2. 字典列表去重:")
    test_dicts = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 1, "name": "Alice Copy"},  # 重复 ID
    ]
    print(f"   原始: {test_dicts}")
    deduped_dicts = ExactDeduplicator.dedupe_dicts_by_field(test_dicts, "id")
    print(f"   去重: {deduped_dicts}")

    # 3. 模糊去重
    print("\n3. 模糊去重:")
    similar_items = [
        "Python 爬虫教程",
        "Python 爬虫入门教程",  # 相似
        "Java 编程指南",
        "Java 编程入门指南"  # 相似
    ]
    print(f"   原始: {similar_items}")
    fuzzy_deduped = FuzzyDeduplicator.dedupe_fuzzy(similar_items, threshold=0.7)
    print(f"   去重(阈值0.7): {fuzzy_deduped}")

    # 4. 相似度计算
    print("\n4. 相似度计算:")
    s1 = "Hello World"
    s2 = "Hello World!"
    s3 = "Goodbye World"
    print(f"   '{s1}' vs '{s2}': {FuzzyDeduplicator.similarity(s1, s2):.2f}")
    print(f"   '{s1}' vs '{s3}': {FuzzyDeduplicator.similarity(s1, s3):.2f}")

    # 5. SimHash
    print("\n5. SimHash 去重:")
    text1 = "这是一篇关于 Python 的文章"
    text2 = "这是一篇关于 Python 的教程"  # 相似
    text3 = "Java 是一门编程语言"
    hash1 = ContentDeduplicator.get_simhash(text1)
    hash2 = ContentDeduplicator.get_simhash(text2)
    hash3 = ContentDeduplicator.get_simhash(text3)
    print(f"   text1-text2 汉明距离: {ContentDeduplicator.hamming_distance(hash1, hash2)}")
    print(f"   text1-text3 汉明距离: {ContentDeduplicator.hamming_distance(hash1, hash3)}")

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    demo()
