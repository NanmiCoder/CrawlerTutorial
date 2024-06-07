# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/4/7 15:18
# @Desc    : 下面代码是通过从chrom浏览器复制请求的curl命令转成python的代码，转换地址：https://hasdata.com/curl-to-python-converter
# @Desc    : 今日的目标站点是雅虎财经的国外站点，他们已经关闭了中国大陆访问，所以需要开启全局VPN（科学上网工具）才能获得目标数据。

import pprint

import requests

cookies = {
    'GUC': 'AQEBCAFmDYVmOUIdcARM&s=AQAAANxlE2ny&g=Zgw0yA',
    'A1': 'd=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGFDWY5Zliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAgF-nCWw8AxSZ-gyIaeg4aI',
    'A3': 'd=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGFDWY5Zliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAgF-nCWw8AxSZ-gyIaeg4aI',
    'axids': 'gam=y-lf5u4KlE2uJWDQYbXyUTkKMC2GVH7OUj~A&dv360=eS1XSElPM3l4RTJ1SHVVV3hNZVBDeG9aTDlDYXdaQ1dPNX5B&ydsp=y-_wiZU4RE2uIAxUbGalyjvJCoR6Le9iVT~A&tbla=y-gt2Wyc1E2uI4nvAYanhnPTMrhn4c3edZ~A',
    'tbla_id': 'fde33964-c427-4b9c-b849-90a304938e21-tuctb84a272',
    'A1S': 'd=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGFDWY5Zliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAgF-nCWw8AxSZ-gyIaeg4aI',
    'cmp': 't=1712472060&j=0&u=1YNN',
    'gpp': 'DBABBg~BVoIgACA.QA',
    'gpp_sid': '8',
}

headers = {
    'accept': '*/*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json',
    # 'cookie': 'GUC=AQEBCAFmDYVmOUIdcARM&s=AQAAANxlE2ny&g=Zgw0yA; A1=d=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGFDWY5Zliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAgF-nCWw8AxSZ-gyIaeg4aI; A3=d=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGFDWY5Zliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAgF-nCWw8AxSZ-gyIaeg4aI; axids=gam=y-lf5u4KlE2uJWDQYbXyUTkKMC2GVH7OUj~A&dv360=eS1XSElPM3l4RTJ1SHVVV3hNZVBDeG9aTDlDYXdaQ1dPNX5B&ydsp=y-_wiZU4RE2uIAxUbGalyjvJCoR6Le9iVT~A&tbla=y-gt2Wyc1E2uI4nvAYanhnPTMrhn4c3edZ~A; tbla_id=fde33964-c427-4b9c-b849-90a304938e21-tuctb84a272; A1S=d=AQABBBB0fGQCEKnzzPnIHq8Lm4HEj-GCp50FEgEBCAGFDWY5Zliia3sB_eMBAAcIEHR8ZOGCp50&S=AQAAAgF-nCWw8AxSZ-gyIaeg4aI; cmp=t=1712472060&j=0&u=1YNN; gpp=DBABBg~BVoIgACA.QA; gpp_sid=8',
    'origin': 'https://finance.yahoo.com',
    'referer': 'https://finance.yahoo.com/crypto?count=25&offset=0',
    'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
}

params = {
    'crumb': 'UllRf10isbP',
    'lang': 'en-US',
    'region': 'US',
    'formatted': 'true',
    'corsDomain': 'finance.yahoo.com',
}

json_data = {
    'offset': 0,
    'size': 25,
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

response = requests.post(
    'https://query1.finance.yahoo.com/v1/finance/screener',
    params=params,
    cookies=cookies,
    headers=headers,
    json=json_data,
)

pprint.pprint(response.json())