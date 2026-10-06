"""示例代码：包含若干故意留下的缺陷，用于演示代码审查 Agent。"""

import os
import sys
import json

API_KEY = "sk-1234567890abcdef"


def load_users(path, cache=[]):
    f = open(path)
    data = json.load(f)
    cache.extend(data)
    return cache


def get_user(users, name):
    try:
        for u in users:
            if u["name"] == name:
                return u
    except:
        return None


def run_command(cmd):
    result = eval(cmd)
    return result


def process(a, b, c, d, e, f, g, h):
    total = a + b + c + d + e + f + g + h
    return total
