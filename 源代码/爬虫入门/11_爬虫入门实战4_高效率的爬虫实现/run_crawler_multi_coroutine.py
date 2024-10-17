# -*- coding: utf-8 -*-
import asyncio
import csv
import time
from typing import Any, Dict, List

import aiofiles
import httpx
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


async def send_request(page_start: int, page_size: int) -> Dict[str, Any]:
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

    async with httpx.AsyncClient() as client:
        response = await client.post(url=req_url, params=common_params, json=common_payload_data, headers=headers,
                                     timeout=30)
    if response.status_code != 200:
        raise Exception("发起请求时发生异常，请求发生错误，原因:", response.text)
    try:
        response_dict: Dict = response.json()
        return response_dict
    except Exception as e:
        raise e


async def fetch_currency_data_single(page_start: int) -> List[SymbolContent]:
    """
    Fetch currency data for a single page.
    :param page_start: Page start index.
    :return: List of SymbolContent for the page.
    """
    try:
        response_dict: Dict = await send_request(page_start=page_start, page_size=PAGE_SIZE)
        return [
            parse_symbol_content(quote) for quote in response_dict["finance"]["result"][0]["quotes"]
        ]
    except Exception as e:
        print(f"Error fetching data for page_start={page_start}: {e}")
        return []


async def fetch_currency_data_list(max_total_count: int) -> List[SymbolContent]:
    """
    Fetch currency data using asyncio.
    :param max_total_count: Maximum total count of currencies.
    :return: List of all SymbolContent.
    """
    page_starts = list(range(0, max_total_count, PAGE_SIZE))
    print(f"总共发起: {len(page_starts)} 次网络请求")

    tasks = [fetch_currency_data_single(page_start) for page_start in page_starts]
    results = await asyncio.gather(*tasks)

    # 扁平化结果列表
    return [item for sublist in results for item in sublist]


async def get_max_total_count() -> int:
    """
    获取所有币种总数量
    :return:
    """
    print("开始获取最大的币种数量")
    try:
        response_dict: Dict = await send_request(page_start=0, page_size=PAGE_SIZE)
        total_num: int = response_dict["finance"]["result"][0]["total"]
        print(f"获取到 {total_num} 种币种")
        return total_num
    except Exception as e:
        print("错误信息：", e)
        return 0


async def save_data_to_csv(save_file_name: str, currency_data_list: List[SymbolContent]) -> None:
    """
    保存数据存储到CSV文件中
    :param save_file_name: 保存的文件名
    :param currency_data_list:
    :return:
    """
    async with aiofiles.open(save_file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # 写入标题行
        await file.write(','.join(SymbolContent.get_fields()) + '\n')
        # 遍历数据列表，并将每个币种的名称写入CSV
        for symbol in currency_data_list:
            await file.write(f"{symbol.symbol},{symbol.name},{symbol.price},{symbol.change_price},{symbol.change_percent},{symbol.market_price}\n")


async def run_crawler_async(save_file_name: str) -> None:
    """
    爬虫主流程(异步并发版本)
    :param save_file_name:
    :return:
    """
    # step1 获取最大数据总量
    max_total: int = await get_max_total_count()
    # step2 遍历每一页数据并解析存储到数据容器中
    data_list: List[SymbolContent] = await fetch_currency_data_list(max_total)
    # step3 将数据容器中的数据保存csv
    await save_data_to_csv(save_file_name, data_list)

async def main():
    """
    主函数
    :return:
    """
    start_time = time.time()
    save_csv_file_name = f"symbol_data_{int(start_time)}.csv"
    await run_crawler_async(save_csv_file_name)
    end_time = time.time()
    print(f"asyncio调度协程执行程序耗时: {end_time - start_time} 秒")


if __name__ == '__main__':
    asyncio.run(main())

