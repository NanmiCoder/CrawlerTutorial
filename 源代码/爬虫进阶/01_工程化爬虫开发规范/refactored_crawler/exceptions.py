# -*- coding: utf-8 -*-
# @Desc: 自定义异常类

from typing import Optional


class CrawlerException(Exception):
    """爬虫基础异常类"""

    def __init__(self, message: str, url: Optional[str] = None):
        self.message = message
        self.url = url
        super().__init__(self.message)

    def __str__(self):
        if self.url:
            return f"{self.message} (URL: {self.url})"
        return self.message


class RequestException(CrawlerException):
    """HTTP 请求异常"""
    pass


class TimeoutException(RequestException):
    """请求超时异常"""
    pass


class HTTPStatusException(RequestException):
    """HTTP 状态码异常"""

    def __init__(self, message: str, status_code: int, url: Optional[str] = None):
        self.status_code = status_code
        super().__init__(message, url)


class ParseException(CrawlerException):
    """数据解析异常"""
    pass


class StorageException(CrawlerException):
    """数据存储异常"""
    pass
