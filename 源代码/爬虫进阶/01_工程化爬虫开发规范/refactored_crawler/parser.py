# -*- coding: utf-8 -*-
# @Desc: 页面解析器

from typing import List, Optional
from parsel import Selector
from loguru import logger

from .models import NoteItem, NoteDetail, PushComment
from .exceptions import ParseException


class BBSParser:
    """BBS 页面解析器"""

    @staticmethod
    def parse_previous_page_number(html: str) -> int:
        """
        解析首页获取上一页的分页号

        Args:
            html: 页面 HTML 内容

        Returns:
            分页号
        """
        try:
            selector = Selector(text=html)
            css_selector = "#action-bar-container > div > div.btn-group.btn-group-paging > a:nth-child(2)"
            pagination_link = selector.css(css_selector).attrib.get("href", "")

            if not pagination_link:
                raise ParseException("无法找到分页链接")

            # 从 /bbs/Stock/index7084.html 提取数字
            page_number = int(
                pagination_link
                .replace("/bbs/Stock/index", "")
                .replace(".html", "")
            )

            logger.debug(f"解析到上一页分页号: {page_number}")
            return page_number

        except Exception as e:
            logger.error(f"解析分页号失败: {e}")
            raise ParseException(f"解析分页号失败: {e}")

    @staticmethod
    def parse_note_list(html: str) -> List[NoteItem]:
        """
        解析帖子列表页

        Args:
            html: 页面 HTML 内容

        Returns:
            帖子列表
        """
        notes = []
        selector = Selector(text=html)

        try:
            note_elements = selector.css("div.r-ent")

            for element in note_elements:
                title_el = element.css("div.title a")
                author_el = element.css("div.meta div.author")
                date_el = element.css("div.meta div.date")

                note = NoteItem(
                    title=title_el.css("::text").get("").strip() if title_el else "",
                    author=author_el.css("::text").get("").strip() if author_el else "",
                    publish_date=date_el.css("::text").get("").strip() if date_el else "",
                    detail_link=title_el.attrib.get("href", "") if title_el else ""
                )

                # 跳过无链接的帖子（可能已删除）
                if note.detail_link:
                    notes.append(note)

            logger.debug(f"解析到 {len(notes)} 个帖子")
            return notes

        except Exception as e:
            logger.error(f"解析帖子列表失败: {e}")
            raise ParseException(f"解析帖子列表失败: {e}")

    @staticmethod
    def parse_note_detail(html: str, note_item: NoteItem) -> NoteDetail:
        """
        解析帖子详情页

        Args:
            html: 页面 HTML 内容
            note_item: 帖子基本信息

        Returns:
            帖子详情
        """
        selector = Selector(text=html)

        try:
            # 基本信息从列表项复制
            detail = NoteDetail(
                title=note_item.title,
                author=note_item.author,
                detail_link=note_item.detail_link
            )

            # 解析发布时间
            time_el = selector.css(
                "#main-content > div:nth-child(4) > span.article-meta-value"
            )
            if time_el:
                detail.publish_datetime = time_el.css("::text").get("").strip()

            # 解析正文内容
            # 获取 main-content 的全部文本，排除元信息和评论部分
            main_content = selector.css("#main-content")
            if main_content:
                # 提取正文：获取所有文本节点，过滤掉元信息和评论
                content_parts = []
                for text_node in main_content.xpath("text()"):
                    text = text_node.get().strip()
                    if text and not text.startswith("--"):  # 排除签名分隔线
                        content_parts.append(text)
                detail.content = "\n".join(content_parts)

            # 解析评论
            comments = []
            push_elements = selector.css("#main-content > div.push")

            for push_el in push_elements:
                spans = push_el.css("span")
                if len(spans) >= 4:
                    comment = PushComment(
                        user_name=spans[1].css("::text").get("").strip(),
                        content=spans[2].css("::text").get("").strip().lstrip(": "),
                        push_time=spans[3].css("::text").get("").strip()
                    )
                    comments.append(comment)

            detail.comments = comments
            logger.debug(f"解析帖子详情完成: {detail.title}, 评论数: {len(comments)}")

            return detail

        except Exception as e:
            logger.error(f"解析帖子详情失败: {e}")
            raise ParseException(f"解析帖子详情失败: {e}")
