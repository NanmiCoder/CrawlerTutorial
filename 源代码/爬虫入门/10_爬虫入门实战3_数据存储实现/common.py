# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/7 15:46
# @Desc    : 公共代码，包含模型类定义、请求头参数构造

from pydantic import BaseModel, Field


class SymbolContent(BaseModel):
    symbol: str = Field(default="", title="Symbol")
    name: str = Field(default="", title="Name")
    price: str = Field(default="", title="价格盘中")
    change_price: str = Field(default="", title="跌涨价格")
    change_percent: str = Field(default="", title="跌涨幅")
    market_price: str = Field(default="", title="市值")


def make_req_params_and_headers():
    headers = {
        # cookies是必须的,并且和common_params的crumb参数绑定的。
        'cookie': 'axids=gam=y-lf5u4KlE2uJWDQYbXyUTkKMC2GVH7OUj~A&dv360=eS1XSElPM3l4RTJ1SHVVV3hNZVBDeG9aTDlDYXdaQ1dPNX5B&ydsp=y-_wiZU4RE2uIAxUbGalyjvJCoR6Le9iVT~A&tbla=y-gt2Wyc1E2uI4nvAYanhnPTMrhn4c3edZ~A; tbla_id=fde33964-c427-4b9c-b849-90a304938e21-tuctb84a272; GUCS=AT4NxRV-; GUC=AQEBCAFmZIhmlkIdcARM&s=AQAAALSYfqJT&g=ZmM4GA; A1=d=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGIZGaWZliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAqkyAfNzjKXHZrWdWvU1Rvo; A3=d=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGIZGaWZliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAqkyAfNzjKXHZrWdWvU1Rvo; A1S=d=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGIZGaWZliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAqkyAfNzjKXHZrWdWvU1Rvo; cmp=t=1717778449&j=0&u=1---; gpp=DBAA; gpp_sid=-1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    }
    common_params = {
        'crumb': 'UllRf10isbP',
        'lang': 'en-US',
        'region': 'US',
        'formatted': 'true',
        'corsDomain': 'finance.yahoo.com',
    }
    common_payload_data = {
        'offset': 0,  # 这个是分页其实位置
        'size': 25,  # 这个是分页数量
        'sortType': 'DESC',
        'sortField': 'intradaymarketcap',
        'quoteType': 'CRYPTOCURRENCY',
        'query': {
            'operator': 'and',
            'operands': [
                {
                    'operator': 'eq',
                    'operands': [
                        'currency',
                        'USD',
                    ],
                },
                {
                    'operator': 'eq',
                    'operands': [
                        'exchange',
                        'CCC',
                    ],
                },
            ],
        },
        'userId': '',
        'userIdType': 'guid',
    }
    return common_params, headers, common_payload_data
