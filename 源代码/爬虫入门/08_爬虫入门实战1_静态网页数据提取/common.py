# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/3/28 01:09
# @Desc    : 公共模型代码

from typing import List


class NoteContent:
    """
    帖子简介存储容器
    """
    title: str = ""  # 帖子标题
    author: str = ""  # 帖子作者
    publish_date: str = ""  # 帖子发表日期
    detail_link: str = ""  # 帖子详情

    def __str__(self):
        return f"""
            Title: {self.title}
            User: {self.author}
            Publish Date: {self.publish_date}
            Detail Link: {self.detail_link}        
        """


class NotePushComment:
    """
    推文存储容器
    """
    push_user_name: str = ""  # 推文人
    push_cotent: str = ""  # 推文内容
    push_time: str = ""  # 推文时间

    def __repr__(self):
        # 这里有用repr的原因是以为了NoteContentDetail的push_comment List结构方便打印
        return f"NotePushComment(push_user_name='{self.push_user_name}', push_cotent='{self.push_cotent}', push_time='{self.push_time}')"


class NoteContentDetail:
    """
    帖子
    """
    title: str = ""  # 帖子标题
    author: str = ""  # 帖子作者
    publish_datetime: str = ""  # 帖子发表日期
    detail_link: str = ""  # 帖子详情链接
    push_comment: List[NotePushComment] = []  # 帖子推文列表，相当于国内评论列表

    def __str__(self):
        return f"""
Title: {self.title}
User: {self.author}
Publish Datetime: {self.publish_datetime}
Detail Link: {self.detail_link}
Push Comments: {self.push_comment}        
"""
