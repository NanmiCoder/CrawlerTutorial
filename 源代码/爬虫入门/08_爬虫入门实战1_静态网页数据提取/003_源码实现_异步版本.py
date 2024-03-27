# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/3/27 23:50
# @Desc    : https://www.ptt.cc/bbs/Stock/index.html 前N页帖子数据获取 - 异步版本

from typing import List

import httpx
from parsel import Selector

from common import NoteContent, NoteContentDetail, NotePushComment

FIRST_N_PAGE = 10  # 前N页的论坛帖子数据
BASE_HOST = "https://www.ptt.cc"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}


async def parse_note_use_parsel(html_content: str) -> NoteContent:
    """
    使用parse提取帖子标题、作者、发布日期，基于css选择器提取
    需要注意的时，我们在提取帖子的时候，可能有些帖子状态不正常，会导致没有link之类的数据，所以我们在取值时最好判断一下元素长度
    :param html_content: html源代码内容
    :return:
    """
    note_content = NoteContent()
    selector = Selector(text=html_content)
    title_elements = selector.css("div.r-ent div.title a")
    author_elements = selector.css("div.r-ent div.meta div.author")
    date_elements = selector.css("div.r-ent div.meta div.date")

    note_content.title = title_elements[0].root.text.strip() if title_elements else ""
    note_content.author = author_elements[0].root.text.strip() if author_elements else ""
    note_content.publish_date = date_elements[0].root.text.strip() if date_elements else ""
    note_content.detail_link = title_elements[0].attrib['href'] if title_elements else ""
    return note_content


async def get_previous_page_number() -> int:
    """
    打开首页提取上一页的分页Number
    :return:
    """
    uri = "/bbs/Stock/index.html"
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_HOST + uri, headers=HEADERS)
        if response.status_code != 200:
            raise Exception("send request got error status code, reason：", response.text)
        selector = Selector(text=response.text)
        css_selector = "#action-bar-container > div > div.btn-group.btn-group-paging > a:nth-child(2)"
        pagination_link = selector.css(css_selector)[0].attrib['href'].strip()
        previous_page_number = int(pagination_link.replace("/bbs/Stock/index", "").replace(".html", ""))
        return previous_page_number


async def fetch_bbs_note_list(previous_number: int) -> List[NoteContent]:
    """
    获取前N页的帖子列表
    :param previous_number:
    :return:
    """
    notes_list: List[NoteContent] = []
    start_page_number = previous_number + 1
    end_page_number = start_page_number - FIRST_N_PAGE
    async with httpx.AsyncClient() as client:
        for page_number in range(start_page_number, end_page_number, -1):
            print(f"开始获取第 {page_number} 页的帖子列表 ...")
            uri = f"/bbs/Stock/index{page_number}.html"
            response = await client.get(BASE_HOST + uri, headers=HEADERS)
            if response.status_code != 200:
                print(f"第{page_number}页帖子获取异常,原因：{response.text}")
                continue
            selector = Selector(text=response.text)
            all_note_elements = selector.css("div.r-ent")
            for note_element_html in all_note_elements:
                note_content: NoteContent = await parse_note_use_parsel(note_element_html.get())
                notes_list.append(note_content)
            print(f"结束获取第 {page_number} 页的帖子列表，本次获取到:{len(all_note_elements)} 篇帖子...")
    return notes_list


async def fetch_bbs_note_detail(note_content: NoteContent) -> NoteContentDetail:
    """
    获取帖子详情页数据
    :param note_content:
    :return:
    """
    print(f"开始获取帖子 {note_content.detail_link} 详情页....")
    note_content_detail = NoteContentDetail()
    note_content_detail.title = note_content.title
    note_content_detail.author = note_content.author
    note_content_detail.detail_link = BASE_HOST + note_content.detail_link

    async with httpx.AsyncClient() as client:
        response = await client.get(note_content_detail.detail_link, headers=HEADERS)
        if response.status_code != 200:
            print(f"帖子：{note_content.title} 获取异常,原因：{response.text}")
            return note_content_detail
        selector = Selector(text=response.text)
        note_content_detail.publish_datetime = \
            selector.css("#main-content > div:nth-child(4) > span.article-meta-value")[0].root.text

        # 解析推文
        note_content_detail.push_comment = []
        all_push_elements = selector.css("#main-content > div.push")
        for push_element in all_push_elements:
            note_push_comment = NotePushComment()
            spans = push_element.css("span")
            if len(spans) < 3:
                continue
            note_push_comment.push_user_name = spans[1].root.text.strip()
            note_push_comment.push_cotent = spans[2].root.text.strip().replace(": ", "")
            note_push_comment.push_time = spans[3].root.text.strip()
            note_content_detail.push_comment.append(note_push_comment)
    print(note_content_detail)
    return note_content_detail


async def run_crawler(save_notes: List[NoteContentDetail]):
    previous_number = await get_previous_page_number()
    note_list = await fetch_bbs_note_list(previous_number)
    for note_content in note_list:
        if not note_content.detail_link:
            continue
        note_content_detail = await fetch_bbs_note_detail(note_content)
        save_notes.append(note_content_detail)
    print("任务爬取完成.......")


if __name__ == '__main__':
    import asyncio

    all_note_content_detail: List[NoteContentDetail] = []
    asyncio.run(run_crawler(all_note_content_detail))
