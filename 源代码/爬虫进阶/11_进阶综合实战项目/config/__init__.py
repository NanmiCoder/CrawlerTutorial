# -*- coding: utf-8 -*-
"""
配置模块
"""
from .settings import settings, Settings, StorageType, LoginType, CrawlerType
from . import bilibili_config

__all__ = [
    'settings',
    'Settings',
    'StorageType',
    'LoginType',
    'CrawlerType',
    'bilibili_config',
]
