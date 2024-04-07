# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/3/27 23:50
# @Desc    : https://www.ptt.cc/bbs/Stock/index.html 前N页帖子数据+推文数据获取 - 同步版本

from typing import List

import requests
from bs4 import BeautifulSoup

from common import NoteContent, NoteContentDetail, NotePushComment

FIRST_N_PAGE = 10  # 前N页的论坛帖子数据
BASE_HOST = "https://www.ptt.cc"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}


def parse_note_use_bs(html_content: str) -> NoteContent:
    """
    使用BeautifulSoup提取帖子标题、作者、发布日期，基于css选择器提取
    需要注意的时，我们在提取帖子的时候，可能有些帖子状态不正常，会导致没有link之类的数据，所以我们在取值时最好判断一下元素长度
    :param html_content: html源代码内容
    :return:
    """
    # 初始化一个帖子保存容器
    note_content = NoteContent()

    soup = BeautifulSoup(html_content, "lxml")
    # 提取标题并去左右除换行空格字符
    note_content.title = soup.select("div.r-ent div.title a")[0].text.strip() if len(
        soup.select("div.r-ent div.title a")) > 0 else ""

    # 提取作者
    note_content.author = soup.select("div.r-ent div.meta div.author")[0].text.strip() if len(
        soup.select("div.r-ent div.meta div.author")) > 0 else ""

    # 提取发布日期
    note_content.publish_date = soup.select("div.r-ent div.meta div.date")[0].text.strip() if len(
        soup.select("div.r-ent div.meta div.date")) > 0 else ""

    # 提取帖子链接
    note_content.detail_link = soup.select("div.r-ent div.title a")[0]["href"] if len(
        soup.select("div.r-ent div.title a")) > 0 else ""
    return note_content


def get_previos_page_number() -> int:
    """
    打开首页提取上一页的分页Number
    :return:
    """
    uri = "/bbs/Stock/index.html"
    reponse = requests.get(url=BASE_HOST + uri, headers=HEADERS)
    if reponse.status_code != 200:
        raise Exception("send request got error status code, reason：", reponse.text)
    soup = BeautifulSoup(reponse.text, "lxml")

    # 下面这一串css选择器获取的最好的办法是使用chrom工具，进入F12控制台，选中'上页'按钮, 右键，点击 Copy -> Copy Css Selector就自动生成了。
    css_selector = "#action-bar-container > div > div.btn-group.btn-group-paging > a:nth-child(2)"
    pagination_link = soup.select(css_selector)[0]["href"].strip()

    # pagination_link: /bbs/Stock/index7084.html 提取数字部分，可以使用正则表达式，也可以使用字符串替换，我这里就使用字符串替换暴力解决了
    previos_page_number = int(pagination_link.replace("/bbs/Stock/index", "").replace(".html", ""))

    return previos_page_number


def fetch_bbs_note_list(previos_number: int) -> List[NoteContent]:
    """
    获取前N页的帖子列表
    :return:
    """
    notes_list: List[NoteContent] = []

    # 计算分页的其实位置和终止位置，由于我们也是要爬首页的，所以得到上一页的分页Number之后，应该还要加1才是我们的起始位置
    start_page_number = previos_number + 1
    end_page_number = start_page_number - FIRST_N_PAGE
    for page_number in range(start_page_number, end_page_number, -1):
        print(f"开始获取第 {page_number} 页的帖子列表 ...")

        # 根据分页Number拼接帖子列表的URL
        uri = f"/bbs/Stock/index{page_number}.html"
        response = requests.get(url=BASE_HOST + uri, headers=HEADERS)
        if response.status_code != 200:
            print(f"第{page_number}页帖子获取异常,原因：{response.text}")
            continue

        # 使BeautifulSoup的CSS选择器解析数据，div.r-ent 是帖子列表html页面中每一个帖子都有的css class
        soup = BeautifulSoup(response.text, "lxml")
        all_note_elements = soup.select("div.r-ent")
        for note_element in all_note_elements:
            # 调用prettify()方法可以获取整个div元素的HTML内容
            note_content: NoteContent = parse_note_use_bs(note_element.prettify())
            notes_list.append(note_content)
        print(f"结束获取第 {page_number} 页的帖子列表，本次获取到:{len(all_note_elements)} 篇帖子...")
    return notes_list


def fetch_bbs_note_detail(note_content: NoteContent) -> NoteContentDetail:
    """
    获取帖子详情页数据
    :param note_content:
    :return:
    """
    print(f"开始获取帖子 {note_content.detail_link} 详情页....")
    note_content_detail = NoteContentDetail()

    # note_content有值的, 我们直接赋值，就不要去网页提取了，能偷懒就偷懒（初学者还是要老老实实的都去提取一下数据）
    note_content_detail.title = note_content.title
    note_content_detail.author = note_content.author
    note_content_detail.detail_link = BASE_HOST + note_content.detail_link

    response = requests.get(url=BASE_HOST + note_content.detail_link, headers=HEADERS)
    if response.status_code != 200:
        print(f"帖子：{note_content.title} 获取异常,原因：{response.text}")
        return note_content_detail

    soup = BeautifulSoup(response.text, "lxml")
    note_content_detail.publish_datetime = soup.select("#main-content > div:nth-child(4) > span.article-meta-value")[
        0].text

    # 处理推文
    note_content_detail.push_comment = []
    all_push_elements = soup.select("#main-content > div.push")
    for push_element in all_push_elements:
        note_push_comment = NotePushComment()
        if len(push_element.select("span")) < 3:
            continue

        note_push_comment.push_user_name = push_element.select("span")[1].text.strip()
        note_push_comment.push_cotent = push_element.select("span")[2].text.strip().replace(": ", "")
        note_push_comment.push_time = push_element.select("span")[3].text.strip()
        note_content_detail.push_comment.append(note_push_comment)

    print(note_content_detail)
    return note_content_detail


def run_crawler(save_notes: List[NoteContentDetail]):
    """
    爬虫主程序
    :param save_notes: 数据保存容器
    :return:
    """
    # step1 获取分页number
    previos_number: int = get_previos_page_number()

    # step2 获取前N页帖子集合列表
    note_list: List[NoteContent] = fetch_bbs_note_list(previos_number)

    # step3 获取帖子详情+推文
    for note_content in note_list:
        if not note_content.detail_link:
            continue
        note_content_detail = fetch_bbs_note_detail(note_content)
        save_notes.append(note_content_detail)

    print("任务爬取完成.......")


if __name__ == '__main__':
    all_note_content_detail: List[NoteContentDetail] = []
    run_crawler(all_note_content_detail)
