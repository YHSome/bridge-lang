"""命名检查：找出"名字撞了规则词"的地方

为什么需要它：桥语言的规则词（`输出`、`长度`、`删除`、`载入`、`现在`…）在词法层被
无条件替换。你要是把函数/变量名起成这些词，代码能写、一跑就变形，而且报错位置
离真正原因很远（这一轮就踩过 `定义 现在()`、`图书.添加()`）。

检查范围（保守，只报高置信度）：

1. `定义/类/def/class` 后面的名字；
2. 顶层与缩进层的 `名字 =` 赋值目标；
3. `对于 名字 在` / `for 名字 in` 的循环变量；
4. 函数参数里带规则词的；
5. 点号后带数字/字母的中文方法名（`以2为底对数` 这种永远匹配不上）。
"""

from __future__ import annotations

import re

from .主转译器 import 分段

_名字 = re.compile(r'[\u3400-\u9fffA-Za-z_][\u3400-\u9fffA-Za-z0-9_]*')
_定义 = re.compile(r'^\s*(?:定义|类|def|class)\s+([\u3400-\u9fffA-Za-z_][\w]*)')
_赋值 = re.compile(r'^\s*([\u3400-\u9fffA-Za-z_][\w]*)\s*=(?!=)')
_循环 = re.compile(r'^\s*(?:对于|for)\s+([^:：]+?)\s+(?:在|in)\s')
_参数 = re.compile(r'^\s*(?:定义|def)\s+[\w]+\s*[（(]([^)）]*)[)）]')
_点号名 = re.compile(r'\.([\u3400-\u9fff][\u3400-\u9fffA-Za-z0-9_]*)')


def _代码行(源码: str) -> list[tuple[int, str]]:
    """行号 + 只保留代码段（字符串/注释抹成空格，保持列位置）"""
    结果 = []
    行们 = 源码.splitlines()
    当前 = [[] for _ in 行们]
    段 = 分段(源码)
    行号 = 0
    for 类型, 文本 in 段:
        片 = 文本
        for 字 in 片:
            if 字 == '\n':
                行号 += 1
                continue
            if 行号 < len(当前):
                当前[行号].append(字 if 类型 == '代码' else ' ')
    for i, 字符们 in enumerate(当前, 1):
        结果.append((i, ''.join(字符们)))
    return 结果


def 检查命名(源码: str, 词表: dict[str, str], 方法表: dict[str, str],
             成员们: dict[str, dict[str, str]] | None = None,
             模块名们: dict[str, str] | None = None) -> list[tuple[int, str, str]]:
    """返回 [(行号, 名字, 说明)]

    - 词表：光着写就会被替换的词（关键字/内建/模块名）
    - 方法表：点号后才替换（定义成同名函数、别人用 `模块.名` 调用就会被拆）
    - 成员们：各模块的成员词（`现在` 这种，前缀回退时会被拆）
    """
    成员词 = {中 for 表 in (成员们 or {}).values() for 中 in 表}
    模块词 = set((模块名们 or {}).keys())
    问题: list[tuple[int, str, str]] = []
    已报: set[tuple[int, str]] = set()

    def 报(行: int, 名: str, 说明: str) -> None:
        if (行, 名) in 已报:
            return
        已报.add((行, 名))
        问题.append((行, 名, 说明))

    for 行, 文本 in _代码行(源码):
        去注释 = 文本.split('#', 1)[0]
        for 正则 in (_定义, _赋值):
            匹配 = 正则.match(去注释)
            if 匹配:
                名 = 匹配.group(1)
                if 名 in 词表:
                    报(行, 名, f'会被翻成 `{词表[名]}`，换个名字')
                elif 名 in 模块词:
                    报(行, 名, f'是模块别名（={模块名们[名]}）：`导入` 里会被翻，'
                              '拿来当变量名迟早搞混')
                elif 正则 is _定义 and 名 in 方法表:
                    报(行, 名, f'是方法表词：别人写 `.{名}` 会被翻成 `.{方法表[名]}`，换个名字')
                elif 名 in 成员词:
                    报(行, 名, '是某个模块的成员词（如 `日期.现在`），前缀回退时会被拆开，建议改名')
        for 匹配 in _循环.finditer(去注释):
            名 = 匹配.group(1).strip()
            if 名 in 词表:
                报(行, 名, f'循环变量会被翻成 `{词表[名]}`，换个名字')
        匹配 = _参数.match(去注释)
        if 匹配:
            for 名 in _名字.findall(匹配.group(1)):
                if 名 in 词表 and 名 not in ('self', 'cls'):
                    报(行, 名, f'参数名会被翻成 `{词表[名]}`，换个名字')
        for 匹配 in _点号名.finditer(去注释):
            名 = 匹配.group(1)
            if re.search(r'\d', 名) and 名 not in 方法表:
                报(行, 名, '点号后的中文名带字母/数字，规则表匹配不到（改成纯中文）')

    return 问题
