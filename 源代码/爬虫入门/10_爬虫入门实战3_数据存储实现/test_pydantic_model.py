# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/8 01:21
# @Desc    : pydantic模型基本使用

# 导入Pydantic库的BaseModel基类
from pydantic import BaseModel

# 定义你的模型类
class User(BaseModel):
    id: int
    name: str
    age: int

# 实例化你的模型类
user = User(id=1, name="小明", age=18)
# 将模型类转换成dict
user_dict = user.model_dump()
print(type(user_dict), user_dict) # <class 'dict'> {'id': 1, 'name': '小明', 'age': 18}

# 将模型类转换成json
user_json = user.model_dump_json()
print(type(user_json), user_json) # <class 'str'> {"id": 1, "name": "小明", "age": 18}