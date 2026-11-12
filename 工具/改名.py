"""把 Python 源码里的英文标识符改成中文（`反向译 --译名` 的实现）

分两步：**先全局收集、再逐文件改**。因为变量要跨文件一致：`db.py` 里定义的
`verify_password` 和 `web.py` 里 `from .db import verify_password` 导入的，
必须改成同一个中文名。

安全边界（宁可不翻，也不能改坏）：

- **模块名不动**：`import 程序.db`、`from . import db` 里的 `db` 是文件名，改名要连文件一起改；
- **三方 API 的属性不动**：`self.headers`、`cur.execute`、`self.wfile`；
- **框架钩子不动**：`do_GET`、`log_message`、`server_version` 由框架调用；
- **关键字参数不动**：`connect(..., check_same_thread=False)` 是 API 契约；
- **内置名不动**：`sorted`、`len`、`print`；
- **翻出来会撞规则表的词不要**（否则正向转译会把变量名当关键字翻掉）；
- **双下划线不动**：`__init__`、`__name__`。
"""

from __future__ import annotations

import builtins
import io
import keyword
import tokenize

# 由框架调用的名字：改了就等于关掉功能
框架钩子 = {
    'do_GET', 'do_POST', 'do_PUT', 'do_DELETE', 'do_HEAD', 'do_OPTIONS', 'do_PATCH',
    'log_message', 'log_request', 'log_error', 'server_version', 'protocol_version',
    'version_string', 'date_time_string', 'address_string',
    'setup', 'finish', 'send_response', 'send_header', 'end_headers', 'send_error',
    'daemon_threads', 'allow_reuse_address', 'server_bind', 'server_activate',
    'server_close', 'fileno',
}

内置名 = set(dir(builtins))


def _有效令牌(源码: str):
    令牌们 = list(tokenize.generate_tokens(io.StringIO(源码).readline))
    return [t for t in 令牌们
            if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                              tokenize.DEDENT, tokenize.COMMENT, tokenize.ENCODING)]


def _语句结束(令牌们, j: int, 起始行: int) -> int:
    """找一条 import 语句到哪儿结束

    `_有效令牌` 把换行符过滤掉了，所以只能按**行号**判语句边界；
    括号里的续行（`from x import (a, b)`）和反斜杠续行要放行。
    """
    深度 = 0
    n = len(令牌们)
    while j < n:
        件 = 令牌们[j]
        if 件.string in ('(', '[', '{'):
            深度 += 1
        elif 件.string in (')', ']', '}'):
            深度 = max(0, 深度 - 1)
        elif 件.string == ';':
            return j
        elif 件.start[0] > 起始行 and 深度 == 0:
            return j
        j += 1
    return n


def 分析导入(源码: str, 项目模块: set[str] | None = None) -> tuple[set[int], set[int], set[int]]:
    """返回 (模块路径令牌下标, 导入符号令牌下标, 别名令牌下标)"""
    模块位: set[int] = set()
    符号位: set[int] = set()
    别名位: set[int] = set()
    try:
        令牌们 = _有效令牌(源码)
    except tokenize.TokenError:
        return 模块位, 符号位, 别名位

    i = 0
    n = len(令牌们)
    while i < n:
        文 = 令牌们[i].string
        # 只有语句开头的 import/from 才是导入：
        # （`raise X from exc` 里的 from 不算导入）
        前一件 = 令牌们[i - 1] if i else None
        语句头 = 前一件 is None or 前一件.end[0] < 令牌们[i].start[0] or 前一件.string == ';'
        if not 语句头:
            i += 1
            continue
        if 文 == 'import':
            结束 = _语句结束(令牌们, i + 1, 令牌们[i].start[0])
            j = i + 1
            while j < 结束:
                if 令牌们[j].string == 'as':
                    if j + 1 < 结束:
                        别名位.add(j + 1)
                    j += 2
                    continue
                if 令牌们[j].type == tokenize.NAME:
                    模块位.add(j)
                j += 1
            i = 结束
            continue
        if 文 == 'from':
            起始行 = 令牌们[i].start[0]
            结束 = _语句结束(令牌们, i + 1, 起始行)
            j = i + 1
            包段: list[str] = []
            while j < 结束 and 令牌们[j].string != 'import':
                if 令牌们[j].type == tokenize.NAME:
                    模块位.add(j)
                    包段.append(令牌们[j].string)
                j += 1
            外部 = len(包段) >= 2          # `http.server`、`concurrent.futures` 这种是三方库
            j += 1                        # 跳过 import
            while j < 结束:
                if 令牌们[j].string == 'as':
                    if j + 1 < 结束:
                        别名位.add(j + 1)
                    j += 2
                    continue
                if 令牌们[j].type == tokenize.NAME:
                    # `from . import db` 里 db 是**子模块**（文件名），不是符号，不能改名；
                    # 三方库导入进来的符号（BaseHTTPRequestHandler 之类）也不能改
                    if 外部 or (项目模块 and 令牌们[j].string in 项目模块):
                        模块位.add(j)
                    else:
                        符号位.add(j)
                j += 1
            i = 结束
            continue
        i += 1
    return 模块位, 符号位, 别名位


def _括号种类(令牌们, i: int) -> str:
    """判断第 i 个 `(` 是"定义参数"、"调用"还是"其它"

    必需区分，否则 `who, logout = "", ""` 这种**元组赋值**会被误判成关键字参数
    （前面是逗号、后面是等号），整行就不改名了，于是 f-string 里的引用对不上。
    """
    前 = 令牌们[i - 1].string if i else ''
    前前 = 令牌们[i - 2].string if i >= 2 else ''
    if 前前 in ('def', 'class'):
        return '定义'
    if 前 and (前[-1].isalnum() or 前 in (')', ']', '}')):
        return '调用'
    return '其它'


def 收集(源码: str, 项目模块: set[str] | None = None) -> dict:
    """收集这个文件里各类名字（给全局建表用）"""
    模块位, _符号位, 别名位 = 分析导入(源码, 项目模块)
    try:
        令牌们 = _有效令牌(源码)
    except tokenize.TokenError:
        return {'模块': set(), '别名': set(), '定义': set(), '可改': set(), '属性': set()}

    模块名 = {令牌们[i].string for i in 模块位}
    别名 = {令牌们[i].string for i in 别名位}
    定义: set[str] = set()
    类名: set[str] = set()
    参数表: dict[str, set[str]] = {}
    可改: set[str] = set()
    属性: set[str] = set()

    for i, 件 in enumerate(令牌们):
        if 件.type == tokenize.NAME and 件.string in ('def', 'class') and i + 1 < len(令牌们):
            后 = 令牌们[i + 1]
            if 后.type == tokenize.NAME:
                定义.add(后.string)
                if 件.string == 'class':
                    类名.add(后.string)
                else:
                    # 记下参数名：调用点写 self._send(..., headers=…) 时要用
                    j = i + 2
                    if j < len(令牌们) and 令牌们[j].string == '(':
                        名们 = set()
                        j += 1
                        while j < len(令牌们) and 令牌们[j].string != ')':
                            if (令牌们[j].type == tokenize.NAME
                                    and 令牌们[j].string not in ('自',)):
                                名们.add(令牌们[j].string)
                            j += 1
                        参数表.setdefault(后.string, set()).update(名们)
        # 模块级常量（列 0 的赋值）也算"项目定义"——别的文件会写成 `模块.常量`
        if (件.type == tokenize.NAME and 件.start[1] == 0 and i + 1 < len(令牌们)
                and 令牌们[i + 1].string in ('=', ':')):
            定义.add(件.string)
        if (i + 3 < len(令牌们) and 件.string in ('self', 'cls')
                and 令牌们[i + 1].string == '.' and 令牌们[i + 2].type == tokenize.NAME
                and 令牌们[i + 3].string == '='):
            属性.add(令牌们[i + 2].string)

    括号栈: list[str] = []
    for i, 件 in enumerate(令牌们):
        if 件.string == '(':
            括号栈.append(_括号种类(令牌们, i))
            continue
        if 件.string == ')':
            if 括号栈:
                括号栈.pop()
            continue
        if 件.type != tokenize.NAME or keyword.iskeyword(件.string):
            continue
        文 = 件.string
        if (文 in 内置名 or 文 in 框架钩子 or 文 in 模块名 or 文 in 别名
                or (文.startswith('__') and 文.endswith('__'))):
            continue
        if i in 模块位:
            continue                      # 模块名（文件名）不动
        前 = 令牌们[i - 1].string if i else ''
        后 = 令牌们[i + 1].string if i + 1 < len(令牌们) else ''
        if 前 == '.':
            continue                      # 属性单独判
        if 后 == '=' and 前 in ('(', ',', '**') and 括号栈 and 括号栈[-1] == '调用':
            continue                      # 调用里的关键字参数（API 契约，不动）
        可改.add(文)

    return {'模块': 模块名, '别名': 别名, '定义': 定义, '类': 类名,
            '参数表': 参数表, '可改': 可改, '属性': 属性}


def 改名(源码: str, 映射: dict[str, str], 模块别名: set[str],
         项目定义: set[str], 项目属性: set[str],
         项目模块: set[str] | None = None,
         项目类: set[str] | None = None,
         参数表: dict[str, set[str]] | None = None) -> tuple[str, int]:
    """按映射改标识符，返回 (新源码, 改了几处)"""
    行们 = 源码.splitlines(keepends=True)
    编辑: list[tuple[tuple[int, int], tuple[int, int], str]] = []
    改数 = 0
    模块位, _符号位, 别名位 = 分析导入(源码, 项目模块)
    try:
        令牌们 = _有效令牌(源码)
    except tokenize.TokenError:
        return 源码, 0

    自身别名 = {令牌们[i].string for i in range(len(令牌们) - 2)
               if (令牌们[i].type == tokenize.NAME and 令牌们[i + 1].string == '='
                   and 令牌们[i + 2].string in ('self', 'cls'))}
    # 回调约定：`def 视图(h: 处理器, **kw)` 里的 h 就是 self（参数带项目类的类型标注）
    if 项目类:
        for i in range(len(令牌们) - 5):
            if (令牌们[i].string == 'def' and 令牌们[i + 2].string == '('
                    and 令牌们[i + 4].string == ':' and 令牌们[i + 3].type == tokenize.NAME
                    and 令牌们[i + 5].string in 项目类):
                自身别名.add(令牌们[i + 3].string)

    括号栈: list[tuple[str, int]] = []
    for i, 件 in enumerate(令牌们):
        if 件.string == '(':
            括号栈.append((_括号种类(令牌们, i), i))
            continue
        if 件.string == ')':
            if 括号栈:
                括号栈.pop()
            continue
        if 件.type != tokenize.NAME:
            continue
        if i in 模块位 or i in 别名位:
            continue                       # 模块名/导入别名不翻
        文 = 件.string
        if 文 in 框架钩子 or 文 in 内置名 or (文.startswith('__') and 文.endswith('__')):
            continue
        if 文 in ('self', 'cls') or 文 in 模块别名:
            continue                       # 模块名/导入别名不动
        前 = 令牌们[i - 1].string if i else ''
        后 = 令牌们[i + 1].string if i + 1 < len(令牌们) else ''

        if 前 == '!':
            continue                       # f-string 的转换符（!r / !s / !a）不是变量
        if 前 == '.':
            # 属性：只改「self.X（X 在项目里被赋值过）」和「项目模块.X（X 是项目定义的）」
            主 = 令牌们[i - 2].string if i >= 2 else ''
            if 主 in {'self', 'cls'} | 自身别名 and (文 in 项目属性 or 文 in 项目定义):
                中文 = 映射.get(文)
            elif 主 in 模块别名 and 文 in 项目定义:
                中文 = 映射.get(文)
            else:
                中文 = None
            if 中文 and 中文 != 文:
                编辑.append((件.start, 件.end, 中文))
            continue

        if 后 == '=' and 前 in ('(', ',', '**') and 括号栈 and 括号栈[-1][0] == '调用':
            # 调用里的关键字参数：只有当**被调的函数也是项目自己的**、且这个参数名
            # 确实在它的形参表里，才改名（`self._send(..., headers=…)` 就是这种情况）
            调用位置 = 括号栈[-1][1]
            被调 = 令牌们[调用位置 - 1].string if 调用位置 >= 1 else ''
            if 参数表 and 被调 in 项目定义 and 文 in 参数表.get(被调, set()):
                中文 = 映射.get(文)
                if 中文 and 中文 != 文:
                    编辑.append((件.start, 件.end, 中文))
            continue
        中文 = 映射.get(文)
        if 中文 and 中文 != 文:
            编辑.append((件.start, 件.end, 中文))

    for (行, 列), (_, 末列), 新 in sorted(编辑, key=lambda x: (x[0][0], x[0][1]), reverse=True):
        原文 = 行们[行 - 1]
        行们[行 - 1] = 原文[:列] + 新 + 原文[末列:]
        改数 += 1
    return ''.join(行们), 改数


def 反向映射(映射: dict[str, str]) -> dict[str, str]:
    return {中: 英 for 英, 中 in 映射.items()}


def 校验(原文: str, 产物: str, 映射: dict[str, str]) -> str:
    """产物里的中文名换回英文后，应与原始 Python **逐字节相同**"""
    回 = 反向映射(映射)
    行们 = 产物.splitlines(keepends=True)
    编辑: list[tuple[tuple[int, int], tuple[int, int], str]] = []
    try:
        令牌们 = _有效令牌(产物)
    except tokenize.TokenError:
        return '产物无法 tokenize'
    for 件 in 令牌们:
        if 件.type != tokenize.NAME:
            continue
        英 = 回.get(件.string)
        if 英:
            编辑.append((件.start, 件.end, 英))
    for (行, 列), (_, 末列), 新 in sorted(编辑, key=lambda x: (x[0][0], x[0][1]), reverse=True):
        原文行 = 行们[行 - 1]
        行们[行 - 1] = 原文行[:列] + 新 + 原文行[末列:]
    回来 = ''.join(行们)
    if 回来 == 原文:
        return ''
    for 行号, (甲, 乙) in enumerate(zip(回来.splitlines(), 原文.splitlines()), 1):
        if 甲 != 乙:
            return f'第 {行号} 行\n  还原: {甲!r}\n  原文: {乙!r}'
    return f'行数不同：还原 {len(回来.splitlines())} / 原文 {len(原文.splitlines())}'
