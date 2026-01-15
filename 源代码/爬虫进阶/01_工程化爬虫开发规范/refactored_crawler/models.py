# -*- coding: utf-8 -*-
# @Desc: 数据模型定义

from typing import List, Optional
from pydantic import BaseModel, Field


class NoteItem(BaseModel):
    """帖子列表项"""
    title: str = Field(default="", description="帖子标题")
    author: str = Field(default="", description="作者")
    publish_date: str = Field(default="", description="发布日期")
    detail_link: str = Field(default="", description="详情链接")


class PushComment(BaseModel):
    """推文/评论"""
    user_name: str = Field(default="", description="用户名")
    content: str = Field(default="", description="评论内容")
    push_time: str = Field(default="", description="评论时间")


class NoteDetail(BaseModel):
    """帖子详情"""
    title: str = Field(default="", description="帖子标题")
    author: str = Field(default="", description="作者")
    detail_link: str = Field(default="", description="详情链接")
    publish_datetime: str = Field(default="", description="发布时间")
    content: str = Field(default="", description="正文内容")
    comments: List[PushComment] = Field(default_factory=list, description="评论列表")


class CrawlResult(BaseModel):
    """爬取结果"""
    total_pages: int = Field(default=0, description="爬取的页数")
    total_notes: int = Field(default=0, description="帖子总数")
    success_count: int = Field(default=0, description="成功数")
    fail_count: int = Field(default=0, description="失败数")
    notes: List[NoteDetail] = Field(default_factory=list, description="帖子详情列表")
