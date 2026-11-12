"""简易调试器：断点 + 单步 + 看变量

    python 桥.py 调试 示例/示例1.bridge --断点 3,7
    python 桥.py 调试 某文件.bridge --断点 5 -- p1 p2

进入断点后可以敲：

    n / 下一步   c / 继续   l / 看源码   p 变量名 / 打印   w / 看所有变量
    b / 看断点   q / 退出

实现上就是 `sys.settrace`：只跟踪**用户 .bridge 文件**的帧（转译器自己的帧不管），
行号与源码一一对应，所以断点写第几行就停第几行。
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path


class 调试会话:
    def __init__(self, 文件名: str, 断点: dict[int, str | None], *,
                 读=input, 写=print) -> None:
        self.文件名 = str(Path(文件名).resolve())
        self.断点 = dict(断点)          # {行号: 条件表达式 or None}
        self.断点行 = set(self.断点)
        self.读 = 读
        self.写 = 写
        self.单步 = False          # 先进去跑到第一个断点，不一开始就停
        self.单步模式 = ''         # 'in'（步入）/ 'over'（步过）
        self.基准深度 = 0
        self.退出 = False
        self.停在 = None          # (文件, 行号)
        self.源码行: list[str] = []
        self.文件路径 = Path(文件名)

    # ---------------- trace 回调 ----------------
    def _是用户帧(self, 帧) -> bool:
        return str(Path(帧.f_code.co_filename).resolve()) == self.文件名

    @staticmethod
    def _深度(帧) -> int:
        深 = 0
        while 帧 is not None:
            深 += 1
            帧 = 帧.f_back
        return 深

    def _条件成立(self, 帧, 条件: str | None) -> bool:
        if not 条件:
            return True
        try:
            return bool(eval(条件, 帧.f_globals, 帧.f_locals))
        except Exception:          # 条件写错就当成立，别把调试卡死
            return True

    def trace(self, 帧, 事件, 参数):
        if not self._是用户帧(帧):
            return self.trace
        if 事件 == 'line':
            行 = 帧.f_lineno
            该停 = False
            if self.单步:
                if self.单步模式 == 'over':
                    该停 = self._深度(帧) <= self.基准深度
                else:
                    该停 = True
            if not 该停 and 行 in self.断点行:
                该停 = self._条件成立(帧, self.断点.get(行))
            if 该停:
                self.单步 = False
                self.单步模式 = ''
                self._交互(帧)
        return self.trace

    # ---------------- 交互 ----------------
    def _源码(self) -> list[str]:
        if not self.源码行:
            try:
                self.源码行 = self.文件路径.read_text(
                    encoding='utf-8-sig').splitlines()
            except OSError:
                self.源码行 = []
        return self.源码行

    def _显示当前位置(self) -> None:
        行 = self.停在[1]
        行们 = self._源码()
        片段 = 行们[行 - 1].strip() if 0 < 行 <= len(行们) else ''
        标记 = '●' if 行 in self.断点 else ' '
        self.写(f'{标记} 第 {行} 行 │ {片段}')

    def _交互(self, 帧) -> None:
        self.停在 = (self.文件名, 帧.f_lineno)
        self._显示当前位置()
        while True:
            try:
                命令 = self.读('(桥调试) ').strip()
            except EOFError:
                self.单步 = False
                return
            if not 命令:
                命令 = 'n'
            动作, _, 其余 = 命令.partition(' ')
            动作 = 动作.lower()
            if 动作 in ('n', 'next', '下一步', 's', 'step', '步入'):
                self.单步 = True
                self.单步模式 = 'in'
                self.基准深度 = self._深度(帧)
                return
            if 动作 in ('o', 'over', '步过'):
                self.单步 = True
                self.单步模式 = 'over'
                self.基准深度 = self._深度(帧)
                return
            if 动作 in ('e', 'eval', '求值'):
                if not 其余:
                    self.写('用法：e 表达式')
                    continue
                try:
                    self.写(repr(eval(其余, 帧.f_globals, 帧.f_locals)))
                except Exception as 错误:        # noqa: BLE001
                    self.写(f'算不出来：{错误}')
                continue
            if 动作 in ('c', 'cont', 'continue', '继续'):
                return
            if 动作 in ('l', 'list', '看源码'):
                self._列源码(帧.f_lineno)
                continue
            if 动作 in ('p', 'print', '打印'):
                if not 其余:
                    self.写('用法：p 变量名')
                    continue
                try:
                    self.写(repr(eval(其余, 帧.f_globals, 帧.f_locals)))
                except Exception as 错误:      # noqa: BLE001
                    self.写(f'取不到：{错误}')
                continue
            if 动作 in ('w', 'where', '变量'):
                for 名, 值 in list(帧.f_locals.items())[:40]:
                    self.写(f'  {名} = {值!r}')
                continue
            if 动作 in ('b', 'break', '断点'):
                描述 = []
                for 行 in sorted(self.断点):
                    条件 = self.断点[行]
                    描述.append(f'{行}（{条件}）' if 条件 else str(行))
                self.写('断点行：' + ('、'.join(描述) or '（无）'))
                continue
            if 动作 in ('h', 'help', '帮助'):
                self.写('n 步入 / o 步过 / c 继续 / l 源码 / p 变量 / e 表达式 / w 变量表 / b 断点 / q 退出')
                continue
            if 动作 in ('q', 'quit', '退出'):
                self.退出 = True
                raise SystemExit(0)
            self.写(f'不认识的命令：{动作}（h 看帮助）')

    def _列源码(self, 中心: int) -> None:
        行们 = self._源码()
        起 = max(1, 中心 - 3)
        止 = min(len(行们), 中心 + 3)
        for 号 in range(起, 止 + 1):
            箭头 = '→' if 号 == 中心 else ' '
            断 = '●' if 号 in self.断点 else ' '
            self.写(f'{断}{箭头} {号:>4} │ {行们[号 - 1]}')


def 调试运行(路径, 断点, 参数: list[str] | None = None) -> int:
    if isinstance(断点, (set, frozenset, list, tuple)):
        断点 = {int(n): None for n in 断点}
    """按断点跑一个 .bridge；返回退出码"""
    from .主转译器 import 编译

    文件 = Path(路径)
    源码 = 文件.read_text(encoding='utf-8-sig')
    代码, _ = 编译(源码, str(文件))
    会话 = 调试会话(文件, 断点)

    旧参数 = sys.argv
    旧trace = sys.gettrace()
    sys.argv = [str(文件), *(参数 or [])]
    命名空间 = {'__name__': '__main__', '__builtins__': __builtins__}
    from .运行时 import 运行时名字

    命名空间.update(运行时名字())
    try:
        sys.settrace(会话.trace)
        exec(代码, 命名空间)
    except SystemExit:
        return 0
    except BaseException:
        traceback.print_exc()
        return 1
    finally:
        sys.settrace(旧trace)
        sys.argv = 旧参数
    return 0
