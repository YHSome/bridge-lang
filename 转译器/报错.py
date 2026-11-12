"""报错翻译：把 Python 的英文异常变成人话

`运行()` 抛出的异常经过这里格式化，输出形如：

    运行出错 · 除零错误：除数不能是 0
      第 4 行 │     出问题()
      第 11 行 │ 出问题()
      （英文原文：ZeroDivisionError: division by zero）

三条原则：

1. **能翻的翻，翻不了的保留英文**——翻错的报错比英文原报错更坑人；
2. **行号指向 .bridge 源码**，并且把那一行的中文原文打出来，不用你去数第几行；
3. **保留英文原文**（括注在最后），方便直接搜索或贴给 AI。
"""

from __future__ import annotations

import re
import traceback
from pathlib import Path

from .规则加载 import 载入规则

_最大帧数 = 4


class 运行失败(Exception):
    """用户代码跑挂了。`文本` 是已经排版好的中文报错，CLI 直接打印。"""

    def __init__(self, 文本: str, 原始: BaseException | None = None) -> None:
        super().__init__(文本)
        self.文本 = 文本
        self.原始 = 原始


def 中文异常名(异常: BaseException, 规则: dict | None = None) -> str:
    规 = 规则 or 载入规则()
    表 = 规.get('异常名') or {}
    类 = type(异常)
    for 基 in 类.__mro__:
        if 基.__name__ in 表:
            return 表[基.__name__]
    return 表.get('Exception', '异常')


def 中文消息(异常: BaseException, 规则: dict | None = None) -> str:
    """把英文消息换成中文；换不了就原样返回"""
    规 = 规则 or 载入规则()
    原文 = str(异常)
    if not 原文:
        return ''
    for 模式, 模板 in 规.get('消息') or []:
        if not re.search(模式, 原文, re.I):
            continue
        try:
            # 模板里的 {1} {2} → 正则的 \g<1> \g<2>；{0} 表示整段匹配
            换成 = re.sub(r'\{(\d+)\}', r'\\g<\1>', 模板)
            return re.sub(模式, 换成, 原文, count=1, flags=re.I)
        except (re.error, IndexError):
            continue
    return 原文


def _是用户帧(帧: traceback.FrameSummary) -> bool:
    """过滤掉桥语言自己的执行帧，只留用户 .bridge 里的行

    判据是"这个文件在不在本包目录里"，而不是列文件名——不然以后新增模块
    （比如 REPL.py）又会漏一个，报错里冒出 `第 112 行 │ exec(...)`。
    """
    包目录 = Path(__file__).resolve().parent.as_posix() + '/'
    名 = Path(帧.filename).resolve().as_posix() if 帧.filename else ''
    if 名.startswith(包目录):
        return False
    return not 名.endswith(('主转译器.py', '报错.py'))


def _源码行(文件名: str, 行号: int | None) -> str:
    if not 行号:
        return ''
    try:
        with open(文件名, encoding='utf-8-sig') as f:
            行们 = f.read().splitlines()
    except OSError:
        return ''
    if 0 < 行号 <= len(行们):
        return 行们[行号 - 1].strip()
    return ''


def _名字提示(异常: BaseException, 规则: dict) -> str:
    """`name '求长肚' is not defined` 这种，猜一下是不是内建名打错了"""
    if not isinstance(异常, NameError):
        return ''
    名字 = getattr(异常, 'name', None)
    if not isinstance(名字, str) or not 名字:
        匹配 = re.search(r"name '(.+?)' is not defined", str(异常))
        名字 = 匹配.group(1) if 匹配 else ''
    if not 名字 or not re.search(r'[\u3400-\u9fff]', 名字):
        return ''
    from .诊断 import 找近似

    命中 = 找近似(名字, 规则)
    if not 命中:
        return ''
    备选, 目标 = 命中
    return f'\n  提示：「{名字}」不在规则表里，是不是想写「{备选}」（= {目标}）？'


def 格式化(异常: BaseException, 规则: dict | None = None) -> str:
    """把异常排版成中文报错（多行字符串）"""
    规 = 规则 or 载入规则()
    中文名 = 中文异常名(异常, 规)
    中文消息文本 = 中文消息(异常, 规)
    原英文 = f'{type(异常).__name__}: {异常}'

    头 = f'运行出错 · {中文名}'
    if 中文消息文本 and 中文消息文本 != 原英文:
        头 += f'：{中文消息文本}'

    帧们 = [帧 for 帧 in traceback.extract_tb(异常.__traceback__) if _是用户帧(帧)]
    帧们 = 帧们[-_最大帧数:]
    行们 = [头]
    for 帧 in 帧们:
        源 = _源码行(帧.filename, 帧.lineno) or (帧.line or '').strip()
        位置 = f'第 {帧.lineno} 行' if 帧.lineno else '（未知行）'
        行们.append(f'  {位置} │ {源}')
    提示 = _名字提示(异常, 规)
    if 提示:
        行们.append(提示)
    行们.append(f'  （英文原文：{原英文}）')
    return '\n'.join(行们)


def 打印(异常: BaseException, 规则: dict | None = None) -> str:
    """排版并返回；调用方负责输出（CLI 打 stderr，编辑器走管道）"""
    return 格式化(异常, 规则)
