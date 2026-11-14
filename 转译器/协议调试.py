"""给编辑器用的协议调试：一行一步、变量回传

和 `调试运行`（命令行交互）共用 settrace 思路，区别是：

- 输出走 **JSON 行**（带 `@@桥调试@@` 前缀），编辑器读它来刷新"变量"面板；
- 命令也走 JSON（从 stdin 读）：`下一行` / `继续` / `停止`；
- 「上一行」由编辑器用历史快照回看实现（进程不能真倒着执行）。

协议格式（每行一个 JSON）：

    {"事件":"开始","文件":"…","行数":N}
    {"事件":"停","行":3,"源码":"…","变量":{"名":{"类型":"int","值":"1"}}}
    {"事件":"错误","文本":"…"}
    {"事件":"结束","退出码":0}
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

协议前缀 = '@@桥调试@@'


def _发协议(对象: dict) -> None:
    sys.stdout.write(协议前缀 + json.dumps(对象, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def _收协议() -> dict:
    行 = sys.stdin.readline()
    if not 行:
        return {'命令': '停止'}
    try:
        return json.loads(行)
    except json.JSONDecodeError:
        return {'命令': '下一行'}


def _值文本(值) -> str:
    try:
        文本 = repr(值)
    except Exception:
        文本 = f'<{type(值).__name__}>'
    return 文本 if len(文本) <= 160 else 文本[:157] + '…'


def _快照(帧) -> dict:
    """合并 globals/locals，跳过 dunder 和注入的运行时名字"""
    from .运行时 import 运行时名字

    跳过 = set(运行时名字()) | {'__builtins__'}
    结果 = {}
    for 来源 in (帧.f_globals, 帧.f_locals):
        for 名, 值 in 来源.items():
            if 名.startswith('__') or 名 in 跳过:
                continue
            结果[名] = {'类型': type(值).__name__, '值': _值文本(值)}
    return 结果


def 协议调试(路径, 断点=None, 参数: list[str] | None = None) -> int:
    from .主转译器 import 编译
    from .运行时 import 运行时名字

    断点行 = {int(n) for n in (断点 or ())}
    文件 = Path(路径)
    源码 = 文件.read_text(encoding='utf-8-sig')
    代码, _ = 编译(源码, str(文件))
    源码行们 = 源码.splitlines()

    def 源码行(行: int) -> str:
        return 源码行们[行 - 1].strip() if 0 < 行 <= len(源码行们) else ''

    状态 = {'单步': True, '退出': False}

    def trace(帧, 事件, 参数对象):
        if 状态['退出']:
            return None
        if str(Path(帧.f_code.co_filename).resolve()) != str(文件.resolve()):
            return trace
        if 事件 != 'line':
            return trace
        行 = 帧.f_lineno
        if not (状态['单步'] or 行 in 断点行):
            return trace
        状态['单步'] = False
        _发协议({'事件': '停', '行': 行, '源码': 源码行(行), '变量': _快照(帧)})
        while True:
            命令 = _收协议().get('命令', '下一行')
            if 命令 in ('下一行', '步入', 'n'):
                状态['单步'] = True
                return trace
            if 命令 in ('继续', 'c'):
                return trace
            if 命令 in ('停止', '退出', 'q'):
                状态['退出'] = True
                raise SystemExit(0)
            _发协议({'事件': '提示', '消息': f'不认识的命令：{命令}'})
        return trace

    旧参数 = sys.argv
    旧trace = sys.gettrace()
    sys.argv = [str(文件), *(参数 or [])]
    命名空间 = {'__name__': '__main__', '__builtins__': __builtins__}
    命名空间.update(运行时名字())
    退出码 = 0
    _发协议({'事件': '开始', '文件': str(文件), '行数': len(源码行们)})
    try:
        sys.settrace(trace)
        exec(代码, 命名空间)
    except SystemExit:
        退出码 = 0
    except BaseException as 错误:
        from .报错 import 格式化

        _发协议({'事件': '错误', '文本': 格式化(错误)})
        退出码 = 1
    finally:
        sys.settrace(旧trace)
        sys.argv = 旧参数
        _发协议({'事件': '结束', '退出码': 退出码})
    return 退出码
