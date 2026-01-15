# -*- coding: utf-8 -*-
# @Desc: 存储后端模块

import json
import csv
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger


class BaseStorage(ABC):
    """存储基类"""

    @abstractmethod
    async def save(self, data: List[Dict]) -> bool:
        """保存数据"""
        pass

    @abstractmethod
    async def load(self) -> List[Dict]:
        """加载数据"""
        pass


class JSONStorage(BaseStorage):
    """JSON 存储"""

    def __init__(self, output_dir: str, filename: str = None):
        """
        初始化 JSON 存储

        Args:
            output_dir: 输出目录
            filename: 文件名（可选，默认按时间戳生成）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            self.filepath = self.output_dir / filename
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.filepath = self.output_dir / f"data_{timestamp}.json"

    async def save(self, data: List[Dict]) -> bool:
        """保存数据到 JSON 文件"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到: {self.filepath} ({len(data)} 条)")
            return True
        except Exception as e:
            logger.error(f"保存失败: {e}")
            return False

    async def load(self) -> List[Dict]:
        """从 JSON 文件加载数据"""
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载失败: {e}")
            return []

    async def append(self, data: Dict) -> bool:
        """追加单条数据"""
        existing = await self.load()
        existing.append(data)
        return await self.save(existing)

    async def append_batch(self, data: List[Dict]) -> bool:
        """追加多条数据"""
        existing = await self.load()
        existing.extend(data)
        return await self.save(existing)


class CSVStorage(BaseStorage):
    """CSV 存储"""

    def __init__(
        self,
        output_dir: str,
        filename: str = None,
        fields: List[str] = None
    ):
        """
        初始化 CSV 存储

        Args:
            output_dir: 输出目录
            filename: 文件名（可选）
            fields: 字段列表（可选，默认从数据推断）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            self.filepath = self.output_dir / filename
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.filepath = self.output_dir / f"data_{timestamp}.csv"

        self.fields = fields

    async def save(self, data: List[Dict]) -> bool:
        """保存数据到 CSV 文件"""
        if not data:
            logger.warning("没有数据需要保存")
            return True

        try:
            # 确定字段列表
            fields = self.fields or list(data[0].keys())

            with open(self.filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)

            logger.info(f"数据已保存到: {self.filepath} ({len(data)} 条)")
            return True
        except Exception as e:
            logger.error(f"保存失败: {e}")
            return False

    async def load(self) -> List[Dict]:
        """从 CSV 文件加载数据"""
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            logger.error(f"加载失败: {e}")
            return []


class StorageManager:
    """存储管理器"""

    def __init__(
        self,
        storage_type: str,
        output_dir: str,
        filename: str = None,
        **kwargs
    ):
        """
        初始化存储管理器

        Args:
            storage_type: 存储类型 ('json' 或 'csv')
            output_dir: 输出目录
            filename: 文件名（可选）
            **kwargs: 传递给具体存储类的参数
        """
        self.output_dir = output_dir

        if storage_type == 'json':
            self._storage = JSONStorage(output_dir, filename)
        elif storage_type == 'csv':
            self._storage = CSVStorage(output_dir, filename, **kwargs)
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")

        self.storage_type = storage_type
        logger.info(f"存储管理器初始化: {storage_type} -> {output_dir}")

    async def save(self, data: List[Dict]) -> bool:
        """保存数据"""
        return await self._storage.save(data)

    async def load(self) -> List[Dict]:
        """加载数据"""
        return await self._storage.load()

    @property
    def filepath(self) -> Path:
        """获取文件路径"""
        return self._storage.filepath
