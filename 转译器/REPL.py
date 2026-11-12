"""桥语言 REPL：一句一句试，不用建文件

    $ python 桥.py repl
    桥> 名字 = "爸爸"
    桥> 输出（f"你好{名字}"）
    你好爸爸
    桥> 如果 名字 等于 "爸爸":
    ...     输出（"对上了"）
    对上了

设计要点：

- **每一行都走完整转译管线**（语法糖、词表、f-string、报错中文化全都生效），
  所以你在这里试出来的行为，和你写进 `.bridge` 文件跑出来的行为一致；
- 「还没写完」的判定交给标准库 `codeop`：它说 `None` 就继续要下一行（`...` 提示符），
  说报错就是真报错，说 OK 就执行——不自己造一套"括号配平"的土办法；
- 表达式自动打印值（`single` 编译模式，和官方 REPL 一样）；
- 出错时给中文报错 + 反向查错建议，命名空间保留，方便边改边试。

命令：`帮助` / `退出`（或 `quit` `exit`）/ `清空`（重置命名空间）/ `查看`（上次转译成什么）/ `查 词`
"""

from __future__ import annotations

import codeop
import sys

from .主转译器 import 版本, 方言错误, 转译
from .规则加载 import 载入规则
from .报错 import 格式化 as 报错文本, 运行失败

提示符 = '桥> '
续行符 = '...> '
_退出词 = {'退出', 'quit', 'exit', 'q', ':q'}


class 交互环境:
    """可以喂行的 REPL 核心（`喂()` 返回该打印的行，便于测试）"""

    def __init__(self) -> None:
        from .运行时 import 运行时名字

        self.命名空间: dict = {'__name__': '__main__', '__builtins__': __builtins__}
        self.命名空间.update(运行时名字())
        self.缓冲: list[str] = []
        self.上次转译: str = ''
        self.编译器 = codeop.CommandCompiler()
        self.规则 = 载入规则()
        self.历史: list[str] = []
        self.块模式 = False

    # ---------------------------------------------------------------- 状态
    @property
    def 待续(self) -> bool:
        return bool(self.缓冲)

    def 提示符(self) -> str:
        return 续行符 if self.待续 else 提示符

    def 清空(self) -> None:
        self.缓冲.clear()

    # ---------------------------------------------------------------- 核心
    def 喂(self, 行: str) -> list[str]:
        """喂一行，返回要打印的内容（空列表 = 继续输入下一行）"""
        出: list[str] = []
        原文 = 行.rstrip('\n')
        命令 = 原文.strip()

        # 粘贴进来的多行：逐行喂，交给同一套缓冲/块模式处理
        if '\n' in 原文:
            汇总: list[str] = []
            for 片 in 原文.splitlines():
                汇总.extend(self.喂(片))
            return 汇总

        if not self.待续:
            if not 命令:
                return 出
            if 命令 in _退出词:
                return ['__退出__']
            if 命令 in ('帮助', 'help', '?'):
                return [
                    '命令：帮助 · 退出 · 清空 · 查看 · 查 <词> · 补 <前缀> · 历史',
                    '其它内容按桥语言执行；没写完的行会用 ...> 继续要输入。',
                ]
            if 命令 in ('查看', 'show'):
                if not self.上次转译:
                    return ['（还没有执行过任何代码）']
                return ['== 上次转译（标准 Python）==', *self.上次转译.splitlines()]
            if 命令 in ('清空', 'reset'):
                from .运行时 import 运行时名字

                self.命名空间 = {'__name__': '__main__', '__builtins__': __builtins__}
                self.命名空间.update(运行时名字())
                return ['（已清空命名空间）']
            if 命令.startswith('查 '):
                from .诊断 import 找近似

                词 = 命令[2:].strip()
                已知: dict[str, str] = {}
                for 表名 in ('关键字', '内建', '异常', '模块'):
                    已知.update(self.规则.get(表名) or {})
                已知.update(self.规则.get('方法') or {})
                for 模块名, 成员表 in (self.规则.get('成员') or {}).items():
                    for 中, 英 in 成员表.items():
                        已知.setdefault(f'{模块名}.{中}', 英)
                        已知.setdefault(中, f'{模块名}.{英}')
                if 词 in 已知:
                    return [f'{词} → {已知[词]}']
                近似 = 找近似(词, self.规则)
                if 近似:
                    return [f'规则表里没有「{词}」，是不是想写「{近似[0]}」（= {近似[1]}）？']
                return [f'规则表里没有「{词}」']
            if 命令.startswith('补 '):
                候选 = self.补全(命令[2:].strip())
                if not 候选:
                    return ['没有以这个词开头的东西']
                return ['  '.join(候选[:40]) + (' …' if len(候选) > 40 else '')]
            if 命令 in ('历史', 'history'):
                if not self.历史:
                    return ['（还没有输入过）']
                return [f'{i + 1:>3}  {行}' for i, 行 in
                        enumerate(self.历史[-20:], max(1, len(self.历史) - 19))]

        if not 命令 and not self.待续 and not self.块模式:
            return 出
        if 命令.startswith(('标记 ', '标签 ', '跳转到 ', '跳转 ')):
            self.块模式 = True
        if 命令:
            self.历史.append(命令)
        self.缓冲.append(原文)
        源码 = '\n'.join(self.缓冲)

        if self.块模式:
            if 原文.strip():
                return 出                       # 继续攒，等空行
            self.块模式 = False
            self.缓冲.clear()
            try:
                转译源码 = 转译(源码, 规则=self.规则)
                self.上次转译 = 转译源码
                代码 = compile(转译源码, '<repl>', 'exec')
            except 方言错误 as 错误:
                return [f'方言错误：{错误}']
            except SyntaxError as 错误:
                return [f'语法错误：{错误.msg}']
            try:
                exec(代码, self.命名空间)
            except SystemExit:
                return ['__退出__']
            except BaseException as 异常:
                出.append(报错文本(异常, self.规则))
            return 出

        try:
            转译源码 = 转译(源码, 规则=self.规则)
            self.上次转译 = 转译源码
        except 方言错误 as 错误:
            self.缓冲.clear()
            return [f'方言错误：{错误}']

        try:
            代码 = self.编译器(转译源码, '<repl>', 'single')
        except (SyntaxError, OverflowError, ValueError) as 错误:
            self.缓冲.clear()
            from .诊断 import 编译建议

            行号 = getattr(错误, 'lineno', None)
            建议 = 编译建议(源码, 行号, self.规则)
            消息 = getattr(错误, 'msg', None) or str(错误)
            return [f'语法错误：{消息}{建议}']

        if 代码 is None:                 # 还没写完，继续要下一行
            return 出

        self.缓冲.clear()
        # 注册进 linecache：报错时能打出你写的那一行桥语言源码
        import linecache

        源码行们 = 源码.splitlines(keepends=True)
        linecache.cache['<repl>'] = (sum(len(l) for l in 源码行们), None, 源码行们, '<repl>')
        try:
            exec(代码, self.命名空间)
        except SystemExit:
            return ['__退出__']
        except BaseException as 异常:
            出.append(报错文本(异常, self.规则))
        return 出

    def 补全(self, 前缀: str) -> list[str]:
        """按词表/方法/模块给候选（Tab 补全和 `补 前缀` 共用）"""
        候选: set[str] = set()
        for 表名 in ('关键字', '内建', '异常', '模块'):
            候选.update((self.规则.get(表名) or {}).keys())
        候选.update((self.规则.get('方法') or {}).keys())
        for 模块名, 成员表 in (self.规则.get('成员') or {}).items():
            候选.update(成员表.keys())
            候选.update(f'{模块名}.{中}' for 中 in 成员表)
        return sorted(名 for 名 in 候选 if 名.startswith(前缀))

    # 短别名，方便测试
    输入 = 喂


def _装_readline(环境: '交互环境') -> bool:
    """有 readline 就装上：Tab 补全 + 上下翻历史（Windows 装 pyreadline3 才有效）"""
    try:
        import readline
    except ImportError:
        return False

    def 补全器(文本, 状态):
        候选 = _补全缓存.get(文本)
        if 候选 is None:
            候选 = 环境.补全(文本)
            _补全缓存[文本] = 候选
        return 候选[状态] if 状态 < len(候选) else None

    _补全缓存.clear()
    readline.set_completer(补全器)
    readline.parse_and_bind('tab: complete')
    return True


_补全缓存: dict[str, list[str]] = {}


def 主循环(say=print, 读=input) -> int:
    say(f'桥语言 {版本} REPL —— 输入「帮助」看命令，「退出」离开')
    环境 = 交互环境()
    if _装_readline(环境):
        say('（Tab 补全 / 上下翻历史已开启；Windows 要装 pyreadline3）')
    while True:
        try:
            行 = 读(环境.提示符())
        except KeyboardInterrupt:
            环境.清空()
            环境.块模式 = False
            say('')
            say('（已清空当前输入，继续）')
            continue
        except EOFError:
            say('')
            return 0
        for 输出 in 环境.喂(行):
            if 输出 == '__退出__':
                return 0
            say(输出)


def main(argv: list[str] | None = None) -> int:
    环境 = 交互环境()
    一行 = ' '.join(argv or [])
    if 一行:                              # 支持 `桥 repl 输出（1）` 这种一次性执行
        for 输出 in 环境.喂(一行):
            if 输出 != '__退出__':
                print(输出)
        return 0
    if not sys.stdin.isatty():           # 管道输入：逐行喂，适合脚本/测试
        for 行 in sys.stdin:
            for 输出 in 环境.喂(行.rstrip('\n')):
                if 输出 == '__退出__':
                    return 0
                print(输出)
        return 0
    return 主循环()
