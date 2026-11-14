"""桥语言 MCP 服务：给 AI 编码工具直接调编译器

    python 桥.py mcp

走 stdio，一行一个 JSON-RPC 2.0 消息（MCP 的 stdio 传输）。提供四个工具：

    桥_查词   {"词": "长度"}
    桥_检查   {"源码": "输出（1）"} 或 {"文件": "x.bridge"}
    桥_查看   {"源码": "…"} 或 {"文件": "…"}
    桥_规则   {}

这样 AI 不用先贴一大段规则，也能让桥语言自己说"这行能不能编译"。
"""

from __future__ import annotations

import io
import json
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

版本 = '0.2.0'


def _抓输出(动作) -> str:
    缓冲 = io.StringIO()
    with redirect_stdout(缓冲):
        动作()
    return 缓冲.getvalue()


def _工具表() -> list[dict]:
    return [
        {
            'name': '桥_查词',
            'description': '查一个中文词在桥语言里对应什么 Python 写法',
            'inputSchema': {
                'type': 'object',
                'properties': {'词': {'type': 'string'}},
                'required': ['词'],
            },
        },
        {
            'name': '桥_检查',
            'description': '只转译不执行，检查 .bridge 源码/文件有没有语法错误',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    '源码': {'type': 'string'},
                    '文件': {'type': 'string'},
                },
            },
        },
        {
            'name': '桥_查看',
            'description': '把 .bridge 源码/文件翻成标准 Python 并返回',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    '源码': {'type': 'string'},
                    '文件': {'type': 'string'},
                },
            },
        },
        {
            'name': '桥_规则',
            'description': '列出当前关键字/内建/方法/模块数量与前几个词',
            'inputSchema': {'type': 'object', 'properties': {}},
        },
    ]


def _取源码(参数: dict) -> str:
    if 参数.get('源码'):
        return str(参数['源码'])
    文件 = 参数.get('文件')
    if not 文件:
        raise ValueError('要传「源码」或者「文件」')
    return Path(文件).read_text(encoding='utf-8-sig')


def _查词(词: str) -> str:
    from .规则加载 import 载入规则

    规则 = 载入规则()
    词 = 词.strip()

    def 动作():
        表们 = [('关键字', 规则.get('关键字') or {}), ('内建', 规则.get('内建') or {}),
                ('异常', 规则.get('异常') or {}), ('模块', 规则.get('模块') or {}),
                ('方法', 规则.get('方法') or {})]
        for 名, 表 in 表们:
            if 词 in 表:
                print(f'{名}：{词} → {表[词]}')
                if 名 == '方法':
                    print('（只在点号后生效）')
                return
        for 模块, 成员 in (规则.get('成员') or {}).items():
            if 词 in 成员:
                print(f'成员.{模块}：{词} → {成员[词]}')
                return
        print(f'规则表里没有「{词}」')

    return _抓输出(动作)


def _检查(参数: dict) -> str:
    from .主转译器 import 编译, 方言错误

    源码 = _取源码(参数)
    try:
        编译(源码, 参数.get('文件') or '<mcp>')
    except 方言错误 as 错误:
        return f'❌ 编译失败：{错误}'
    except Exception as 错误:      # noqa: BLE001
        return f'❌ {type(错误).__name__}: {错误}'
    return '✅ 检查通过'


def _查看(参数: dict) -> str:
    from .主转译器 import 转译

    return 转译(_取源码(参数), 规则=None)


def _规则() -> str:
    from .规则加载 import 载入规则

    规则 = 载入规则()
    return (f"关键字 {len(规则['关键字'])} · 内建 {len(规则['内建'])} · "
            f"异常 {len(规则['异常'])} · 方法 {len(规则['方法'])} · "
            f"模块 {len(规则['模块'])} · 句式糖 {len(规则['语法糖'])}\n"
            "模块：" + '、'.join(规则['模块']))


def _调用工具(名: str, 参数: dict) -> tuple[str, bool]:
    try:
        if 名 == '桥_查词':
            return _查词(str(参数.get('词', ''))), False
        if 名 == '桥_检查':
            return _检查(参数), False
        if 名 == '桥_查看':
            return _查看(参数), False
        if 名 == '桥_规则':
            return _规则(), False
        return f'没有这个工具：{名}', True
    except Exception as 错误:      # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        return f'{type(错误).__name__}: {错误}', True


def _回(标识, 结果=None, 错误=None) -> dict:
    体 = {'jsonrpc': '2.0', 'id': 标识}
    if 错误 is not None:
        体['error'] = 错误
    else:
        体['result'] = 结果
    return 体


def 处理消息(消息: dict) -> dict | None:
    方法 = 消息.get('method')
    标识 = 消息.get('id')
    if 方法 == 'initialize':
        return _回(标识, {
            'protocolVersion': '2024-11-05',
            'capabilities': {'tools': {}},
            'serverInfo': {'name': '桥语言', 'version': 版本},
        })
    if 方法 in ('notifications/initialized', 'notifications/cancelled'):
        return None
    if 方法 == 'ping':
        return _回(标识, {})
    if 方法 == 'tools/list':
        return _回(标识, {'tools': _工具表()})
    if 方法 == 'tools/call':
        参数 = 消息.get('params') or {}
        名 = 参数.get('name', '')
        结果, 是错 = _调用工具(名, 参数.get('arguments') or {})
        return _回(标识, {'content': [{'type': 'text', 'text': 结果}], 'isError': 是错})
    return _回(标识, 错误={'code': -32601, 'message': f'不认识的方法：{方法}'})


def main(参数: list[str] | None = None) -> int:
    for 行 in sys.stdin:
        行 = 行.strip()
        if not 行:
            continue
        try:
            消息 = json.loads(行)
        except json.JSONDecodeError:
            continue
        回 = 处理消息(消息)
        if 回 is not None:
            print(json.dumps(回, ensure_ascii=False), flush=True)
    return 0
