# -*- coding: utf-8 -*-
import csv
import time
from typing import Any, Dict, List
from multiprocessing import Pool, cpu_count

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


def send_request(page_start: int, page_size: int) -> Dict[str, Any]:
    """
    公共的发送请求的函数
    :param page_start: 分页起始位置
    :param page_size: 每一页的长度
    :return:
    """
    # print(f"[send_request] page_start:{page_start}")
    req_url = HOST + SYMBOL_QUERY_API_URI
    common_params, headers, common_payload_data = make_req_params_and_headers()
    # 修改分页变动参数
    common_payload_data["offset"] = page_start
    common_payload_data["size"] = page_size

    response = requests.post(url=req_url, params=common_params, json=common_payload_data, headers=headers)
    if response.status_code != 200:
        raise Exception("发起请求时发生异常，请求发生错误，原因:", response.text)
    try:
        response_dict: Dict = response.json()
        return response_dict
    except Exception as e:
        raise e


def fetch_currency_data_single(page_start: int) -> List[SymbolContent]:
    """
    Fetch currency data for a single page.
    :param page_start: Page start index.
    :return: List of SymbolContent for the page.
    """
    try:
        response_dict: Dict = send_request(page_start=page_start, page_size=PAGE_SIZE)
        symbol_data_list: List[SymbolContent] = [
            parse_symbol_content(quote) for quote in response_dict["finance"]["result"][0]["quotes"]
        ]
        return symbol_data_list
    except Exception as e:
        print(f"Error fetching data for page_start={page_start}: {e}")
        return []


def fetch_currency_data_list(max_total_count: int) -> List[SymbolContent]:
    """
    Fetch currency data using multiprocessing.
    :param max_total_count: Maximum total count of currencies.
    :return: List of all SymbolContent.
    """
    with Pool(processes=cpu_count()) as pool:
        page_starts = list(range(0, max_total_count, PAGE_SIZE))
        print(f"总共发起: {len(page_starts)} 次网络请求")
        results = pool.map(fetch_currency_data_single, page_starts)

        # Flatten the list of lists into a single list
    return [item for sublist in results for item in sublist]


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


def run_crawler_mp(save_file_name: str) -> None:
    """
    爬虫主流程(多进程版本)
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
    start_time = time.time()
    save_csv_file_name = f"symbol_data_{int(start_time)}.csv"
    run_crawler_mp(save_csv_file_name)
    end_time = time.time()
    print(f"多进程执行程序耗时: {end_time - start_time} 秒")