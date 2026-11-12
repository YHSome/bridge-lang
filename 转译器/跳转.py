"""`标记` / `跳转到` 的落地实现（goto）

Python 没有 goto，所以这一步在**桥语言源码层面**做改写：把带标记的代码块
改成一个"状态机 + 派发循环"，`跳转到 X` 变成 `raise 桥跳转("X")`，
派发循环接住信号、改状态、继续下一轮。

改写前后对比（模块顶层）：

    # 改写前
    输出（"你好"）
    标记 标记1
    输出（"世界")
    跳转到 标记2

    # 改写后（缩进略）
    _桥标记表 = {"标记1": 1, "标记2": 2}
    _桥状态 = 0
    while True:
        try:
            if _桥状态 == 0:
                print("你好")
                _桥状态 = 1
                continue
            if _桥状态 == 1:
                print("世界")
                raise 桥跳转("标记2")
            raise NameError("该标记不存在")
        except 桥跳转 as _桥信号:
            _桥状态 = _桥标记表.get(_桥信号.标记)
            if _桥状态 is None:
                raise NameError(f"该标记不存在：{_桥信号.标记}")
            continue

为什么要包在 try 里：`跳转到` 可能写在 if / for 里面，直接 `continue` 会被内层
循环抢走；用异常跳出来，嵌套多深都可靠。变量本来就在同一个作用域，跳过去还在。
"""

from __future__ import annotations

import re

_标记行 = re.compile(r'^(?P<缩进>[ \t]*)(?:标记|标签|label)\s+(?P<名>[^\s:：]+)\s*[:：]?\s*$')
_跳转行 = re.compile(
    r'^(?P<缩进>[ \t]*)(?:跳转(?:到)?|goto|jump)\s+(?P<名>[^\s:：]+)\s*[:：]?\s*$')
_块头 = re.compile(r'[:：]\s*$')


def _缩进(行: str) -> int:
    return len(行) - len(行.lstrip(' \t'))


def 有标记(源码: str) -> bool:
    return any(_标记行.match(行) for 行 in 源码.splitlines())


def 有跳转(源码: str) -> bool:
    return any(_跳转行.match(行) for 行 in 源码.splitlines())


def 第一个跳转名(源码: str) -> str:
    for 行 in 源码.splitlines():
        匹配 = _跳转行.match(行)
        if 匹配:
            return 匹配.group('名')
    return '?'


def _找块(行们: list[str], 标号: int, 缩进: int) -> tuple[int, int, int] | None:
    """找某个标号所在块的 (块头行号, 块体开始, 块体结束)"""
    头 = None
    for i in range(标号 - 1, -1, -1):
        行 = 行们[i]
        if not 行.strip():
            continue
        if _缩进(行) < 缩进:
            头 = i
            break
    if 头 is None:
        return None
    if not _块头.search(行们[头].rstrip()):
        return None                        # 不是块头，说明标记悬空
    块头缩进 = _缩进(行们[头])
    尾 = len(行们)
    for j in range(头 + 1, len(行们)):
        if not 行们[j].strip():
            continue
        if _缩进(行们[j]) <= 块头缩进:
            尾 = j
            break
    return 头, 头 + 1, 尾


def _改一段(行们: list[str], 起: int, 止: int, 缩进: int) -> list[str]:
    """把 [起, 止) 这一段（块体）改写成派发循环"""
    标签们: list[tuple[int, str]] = []
    for i in range(起, 止):
        匹配 = _标记行.match(行们[i])
        if 匹配 and len(匹配.group('缩进')) == 缩进:
            标签们.append((i, 匹配.group('名')))
    if not 标签们:
        return 行们[起:止]

    表名 = '_桥标记表'
    状态名 = '_桥状态'
    表项 = '、'.join(f'"{名}": {k + 1}' for k, (_, 名) in enumerate(标签们))

    出: list[str] = []
    空格 = ' ' * 缩进
    出.append(f'{空格}{表名} = {{{表项}}}')
    出.append(f'{空格}{状态名} = 0')
    出.append(f'{空格}while True:')
    出.append(f'{空格}    try:')

    段们: list[tuple[int, int]] = []
    起段 = 起
    for 行号, _ in 标签们:
        段们.append((起段, 行号))
        起段 = 行号 + 1
    段们.append((起段, 止))

    体缩进 = 缩进 + 12
    for k, (段起, 段止) in enumerate(段们):
        出.append(f'{空格}        if {状态名} == {k}:')
        有内容 = False
        for i in range(段起, 段止):
            行 = 行们[i]
            if not 行.strip():
                出.append('')
                continue
            有内容 = True
            相对 = max(0, _缩进(行) - 缩进)
            正文 = 行.lstrip(' \t')
            跳 = _跳转行.match(正文)
            if 跳:
                出.append(' ' * (体缩进 + 相对) + f'raise 桥跳转("{跳.group("名")}")')
            else:
                出.append(' ' * (体缩进 + 相对) + 正文)
        if not 有内容:
            出.append(' ' * 体缩进 + '通过')
        if k + 1 < len(段们):
            出.append(' ' * 体缩进 + f'{状态名} = {k + 1}')
            出.append(' ' * 体缩进 + 'continue')
        else:
            出.append(' ' * 体缩进 + 'break')

    出.append(f'{空格}        raise NameError("该标记不存在")')
    出.append(f'{空格}    except 桥跳转 as _桥信号:')
    出.append(f'{空格}        {状态名} = {表名}.get(_桥信号.标记)')
    出.append(f'{空格}        if {状态名} is None:')
    出.append(f'{空格}            raise NameError(f"该标记不存在：{{_桥信号.标记}}")')
    出.append(f'{空格}        continue')

    新的 = 行们[:起] + 出 + 行们[止:]
    return 新的


def 转换(源码: str) -> str:
    """把源码里的 标记/跳转到 改写成状态机；没有标记就原样返回

    只有 `标记` 没有 `跳转到`（比如 REPL 里单独喂了一行标签）时，把标签行抹成空行：
    行号不变，也不需要背一个用不上的状态机。
    """
    if not 有标记(源码):
        return 源码
    if not 有跳转(源码):
        return '\n'.join('' if _标记行.match(行) else 行
                         for 行 in 源码.splitlines()) + ('\n' if 源码.endswith('\n') else '')
    行们 = 源码.splitlines()
    终止 = 0
    while 有标记('\n'.join(行们)) and 终止 < 20:
        终止 += 1
        改过 = False
        # 从最深的缩进开始处理
        组: dict[int, list[int]] = {}
        for i, 行 in enumerate(行们):
            匹配 = _标记行.match(行)
            if 匹配:
                组.setdefault(len(匹配.group('缩进')), []).append(i)
        for 缩进 in sorted(组, reverse=True):
            for 标号 in sorted(组[缩进], reverse=True):
                if 缩进 == 0:
                    范围 = (0, len(行们))          # 模块顶层：整份文件就是一个作用域
                else:
                    块 = _找块(行们, 标号, 缩进)
                    if 块 is None:
                        raise ValueError(f'标记写在了不认识的层级：{行们[标号].strip()}')
                    头号, _, _ = 块
                    头行 = 行们[头号].lstrip()
                    if not 头行.startswith(('定义', '类', 'def', 'class')):
                        raise ValueError(
                            f'「标记 {行们[标号].strip().split()[-1]}」写在 if/for/while 里面了：'
                            '标记只能写在模块顶层或函数/类的第一层')
                    范围 = 块[1:]
                起, 止 = 范围
                行们 = _改一段(行们, 起, 止, 缩进)
                改过 = True
                break
            if 改过:
                break
        if not 改过:
            break
    结果 = '\n'.join(行们) + ('\n' if 源码.endswith('\n') else '')

    # 收尾自检：还剩下的标签/跳转说明它们写在了套不进去的地方（if/for/while 里面，
    # 或者从一个函数往外面的标签跳）。这种情况与其生成非法代码，不如直接说清楚。
    for 行 in 结果.splitlines():
        匹配 = _标记行.match(行)
        if 匹配:
            raise ValueError(
                f'「标记 {匹配.group("名")}」写在 if/for/while 里面了：'
                '标记只能写在模块顶层或函数/类的第一层')
        匹配 = _跳转行.match(行)
        if 匹配:
            raise ValueError(
                f'「跳转到 {匹配.group("名")}」没找到同一段代码里的标记：'
                '跳转不能跨函数（也不能从函数里跳到外面）')
    return 结果


def 缺失目标(源码: str) -> str | None:
    """返回第一个"跳了但没声明"的标记名；全都有声明就返回 None"""
    标记们 = {匹配.group('名') for 行 in 源码.splitlines()
              if (匹配 := _标记行.match(行))}
    for 行 in 源码.splitlines():
        匹配 = _跳转行.match(行)
        if 匹配 and 匹配.group('名') not in 标记们:
            return 匹配.group('名')
    return None
