# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/4/7 17:07
# @Desc    : https://finance.yahoo.com/crypto页面的加密货币表格数据
# @Desc    : 下面的代码请挂全局的科学上网工具再跑
import csv
import random
import time
from typing import List, Dict, Any

import requests

from common import SymbolContent, make_req_params_and_headers

HOST = "https://query1.finance.yahoo.com"
SYMBOL_QUERY_API_URI = "/v1/finance/screener"
PAGE_SIZE = 100  # 可选配置（25, 50, 100）


def parse_symbol_content(quote_item: Dict) -> SymbolContent:
    """
    数据提取
    :param quote_item:
    :return:
    """
    symbol_content = SymbolContent()
    symbol_content.symbol = quote_item["symbol"]
    symbol_content.name = quote_item["shortName"]
    symbol_content.price = quote_item["regularMarketPrice"]["fmt"]
    symbol_content.change_price = quote_item["regularMarketChange"]["fmt"]
    symbol_content.change_percent = quote_item["regularMarketChangePercent"]["fmt"]
    symbol_content.market_price = quote_item["marketCap"]["fmt"]
    return symbol_content


def fetch_currency_data_list(max_total_count: int) -> List[SymbolContent]:
    """
    通过最大币种数量计算爬取次数，解析数据存入数据容器
    :param max_total_count:
    :return:
    """
    symbol_data_list: List[SymbolContent] = []
    page_start = 0
    while page_start <= max_total_count:
        response_dict: Dict = send_request(page_start=page_start, page_size=PAGE_SIZE)
        for quote in response_dict["finance"]["result"][0]["quotes"]:
            parsed_content: SymbolContent = parse_symbol_content(quote)
            print(parsed_content)
            symbol_data_list.append(parsed_content)
        page_start += PAGE_SIZE
        time.sleep(random.Random().random())
    return symbol_data_list


def send_request(page_start: int, page_size: int) -> Dict[str, Any]:
    """
    公共的发送请求的函数
    :param page_start: 分页起始位置
    :param page_size: 每一页的长度
    :return:
    """
    print(f"[send_request] page_start:{page_start}")
    req_url = HOST + SYMBOL_QUERY_API_URI
    common_params, headers, common_payload_data = make_req_params_and_headers()
    # 修改分页变动参数
    common_payload_data["offset"] = page_start
    common_payload_data["size"] = page_size

    response = requests.post(url=req_url, params=common_params, json=common_payload_data, headers=headers)
    if response.status_code != 200:
        raise Exception("发起请求是发生异常，请求发生错误，原因:", response.text)
    try:
        response_dict: Dict = response.json()
        return response_dict
    except Exception as e:
        raise e


def get_max_total_count() -> int:
    """
    获取所有币种总数量
    :return:
    """
    print("开始获取最大的币种数量")
    try:
        response_dict: Dict = send_request(page_start=0, page_size=PAGE_SIZE)
        total_num: int = response_dict["finance"]["result"][0]["total"]
        print(f"获取到 {total_num} 种币种")
        return total_num
    except Exception as e:
        print("错误信息：", e)
        return 0


def save_data_to_csv(save_file_name: str, currency_data_list: List[SymbolContent]) -> None:
    """
    保存数据存储到CSV文件中
    :param save_file_name: 保存的文件名
    :param currency_data_list:
    :return:
    """
    with open(save_file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # 写入标题行
        writer.writerow(SymbolContent.get_fields())
        # 遍历数据列表，并将每个币种的名称写入CSV
        for symbol in currency_data_list:
            writer.writerow([symbol.symbol, symbol.name, symbol.price, symbol.change_price, symbol.change_percent,
                             symbol.market_price])


def run_crawler(save_file_name: str) -> None:
    """
    爬虫主流程
    :param save_file_name:
    :return:
    """
    # step1 获取最大数据总量
    max_total: int = get_max_total_count()
    # step2 遍历每一页数据并解析存储到数据容器中
    data_list: List[SymbolContent] = fetch_currency_data_list(max_total)
    # step3 将数据容器中的数据保存csv
    save_data_to_csv(save_file_name, data_list)


if __name__ == '__main__':
    timestamp = int(time.time())
    save_csv_file_name = f"symbol_data_{timestamp}.csv"
    run_crawler(save_csv_file_name)
