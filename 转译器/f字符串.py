r"""f-string 支持：让 `f"{长度(数据)}"` 里的中文也能被翻译

f-string 是「字符串里嵌表达式」，桥语言原来把它整段当字符串跳过（安全但没用）。
这个模块负责把 `{...}` 里的**表达式部分**挖出来交给转译器，其余照抄。

只做三件事：

1. `是f字符串(字面量)` —— 判断 `f"..."` / `rf'''...'''` 这类；
2. `加工(字面量, 回调)` —— 把每个 `{表达式}` 交给回调，拼回新字面量；
3. `找字段(字面量)` / `定位(源码)` —— 给反向译和编辑器用（要的是位置）。

不碰的东西：`{{` `}}`（转义的大括号）、格式说明符 `:.2f`、`!r` 转换符、
表达式里的字符串字面量（那是数据）。

**不做**的是：不解析语义、不算 AST。跳字符串、数字段边界靠一个小状态机，
遇到嵌套大括号/嵌套引号就按规则配平——够用，而且跟转译器"只做词法"的定位一致。
"""

from __future__ import annotations

from .主转译器 import 分段

_引号们 = ('"""', "'''", '"', "'")


def _拆前缀(字面量: str) -> tuple[str, str, str] | None:
    """拆成 (前缀, 引号, 正文)；不是字符串字面量就返回 None"""
    i = 0
    while i < len(字面量) and 字面量[i].isalpha():
        i += 1
    前缀 = 字面量[:i]
    余下 = 字面量[i:]
    for 引号 in _引号们:
        if 余下.startswith(引号) and 余下.endswith(引号) and len(余下) >= 2 * len(引号):
            return 前缀, 引号, 余下[len(引号):-len(引号)]
    return None


def 是f字符串(字面量: str) -> bool:
    拆 = _拆前缀(字面量)
    if not 拆:
        return False
    前缀, _, _ = 拆
    return 'f' in 前缀.lower()


def _跳字符串(文本: str, i: int) -> int:
    """从 i（引号处）跳到字符串之后；找不到闭合就跳到末尾"""
    引号 = 文本[i]
    j = i + 1
    while j < len(文本):
        if 文本[j] == '\\':
            j += 2
            continue
        if 文本[j] == 引号:
            return j + 1
        j += 1
    return j


def _字段结束(正文: str, 起: int) -> int:
    """从 `{` 的位置开始，找到配对的 `}`（处理嵌套括号/引号）"""
    深度 = 0
    i = 起
    while i < len(正文):
        c = 正文[i]
        if c in '"\'':
            i = _跳字符串(正文, i)
            continue
        if c == '{':
            深度 += 1
        elif c == '}':
            深度 -= 1
            if 深度 == 0:
                return i
        i += 1
    return -1


def _拆表达式与格式(字段: str) -> tuple[str, str]:
    """把 `x!r:>10` 拆成 (表达式, '!r:>10')；只按括号深度 0 的 `!` `:` 切"""
    深度 = 0
    i = 0
    while i < len(字段):
        c = 字段[i]
        if c in '"\'':
            i = _跳字符串(字段, i)
            continue
        if c in '([{':
            深度 += 1
        elif c in ')]}':
            深度 -= 1
        elif c in '!:' and 深度 == 0:
            return 字段[:i], 字段[i:]
        i += 1
    return 字段, ''


def 加工(字面量: str, 回调) -> tuple[str, int]:
    """把每个 `{表达式}` 交给回调重写，返回 (新字面量, 处理了几个字段)"""
    拆 = _拆前缀(字面量)
    if not 拆:
        return 字面量, 0
    前缀, 引号, 正文 = 拆
    出: list[str] = []
    i = 0
    个数 = 0
    while i < len(正文):
        c = 正文[i]
        if c == '{' and i + 1 < len(正文) and 正文[i + 1] == '{':
            出.append('{{')
            i += 2
            continue
        if c == '}' and i + 1 < len(正文) and 正文[i + 1] == '}':
            出.append('}}')
            i += 2
            continue
        if c == '{':
            止 = _字段结束(正文, i)
            if 止 < 0:
                出.append(正文[i:])
                break
            字段 = 正文[i + 1:止]
            表达式, 尾巴 = _拆表达式与格式(字段)
            新 = 回调(表达式)
            出.append('{' + 新 + 尾巴 + '}')
            个数 += 1
            i = 止 + 1
            continue
        出.append(c)
        i += 1
    return 前缀 + 引号 + ''.join(出) + 引号, 个数


def 定位(源码: str) -> list[tuple[int, int]]:
    """给出一份源码里所有 f-string 字面量的 (起, 止) 偏移（供反向译/编辑器用）"""
    结果: list[tuple[int, int]] = []
    偏移 = 0
    for 种类, 文本 in 分段(源码):
        if 种类 == '字符串' and 是f字符串(文本):
            结果.append((偏移, 偏移 + len(文本)))
        偏移 += len(文本)
    return 结果
