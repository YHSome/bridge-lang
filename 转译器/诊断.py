"""反向查错：编译不过时，猜一下「你是不是把词写错了」

用户写 `如过 条件:` 时，Python 只会说 `invalid syntax`——没用。这里用**编辑距离**
在规则表里找最近的词，给出「第 3 行：「如过」→ 是不是想写「如果」？」。

三条克制原则（防止变成噪音制造机）：

1. **只在编译失败时跑**，成功时不打扰；
2. **只看报错行前后各一行**，不要全文乱猜；
3. **只报距离足够近的**（短词容错 1 个字），并且最多 3 条，按距离排序。

顺手还做一件事：把「这一行里有几个词完全不认识」列出来（比如 `求长肚` 这种），
因为这些往往就是手滑打错、而不是语法结构问题。
"""

from __future__ import annotations

import re
from collections import Counter

汉字 = re.compile(r'[\u3400-\u9fff]+')


def _编辑距离(甲: str, 乙: str) -> int:
    if 甲 == 乙:
        return 0
    if abs(len(甲) - len(乙)) > 3:
        return 99
    上 = list(range(len(乙) + 1))
    for i, 字甲 in enumerate(甲, 1):
        当 = [i]
        for j, 字乙 in enumerate(乙, 1):
            当.append(min(上[j] + 1, 当[j - 1] + 1, 上[j - 1] + (字甲 != 字乙)))
        上 = 当
    return 上[-1]


def _容错(词: str) -> int:
    """词短就只容 1 个字，词长放宽一点"""
    if len(词) <= 3:
        return 1
    return 2


def _已知表(规则: dict) -> dict[str, str]:
    """中文词 → 它会被翻成什么（用来给建议加一句"= if"）"""
    表: dict[str, str] = {}
    for 类别 in ('关键字', '内建', '异常', '模块'):
        for 中, 英 in (规则.get(类别) or {}).items():
            表[中] = 英
    for 中, 英 in (规则.get('方法') or {}).items():
        表.setdefault(中, f'{英}()')
    for 模块, 成员 in (规则.get('成员') or {}).items():
        for 中, 英 in 成员.items():
            表.setdefault(中, f'{模块}.{英}')
    return 表


def 建议(源码: str, 行号: int | None, 规则: dict, *, 上下文行数: int = 1,
         最多: int = 3) -> list[str]:
    """给编译失败的行找"可能是错字"的词，返回人类可读的建议行"""
    已知 = _已知表(规则)
    if not 已知:
        return []

    行们 = 源码.splitlines()
    检查行: list[int] = []
    if 行号:
        for 偏移 in range(-上下文行数, 上下文行数 + 1):
            号 = 行号 + 偏移
            if 1 <= 号 <= len(行们):
                检查行.append(号)
    else:
        检查行 = list(range(1, min(len(行们), 5) + 1))

    from .主转译器 import 分段

    候选: list[tuple[int, int, str, str, str]] = []   # (距离, 行号, 词, 建议, 目标)
    for 号 in 检查行:
        行文 = 行们[号 - 1]
        for 种类, 文本 in 分段(行文):
            if 种类 != '代码':
                continue
            for 匹配 in 汉字.finditer(文本):
                词 = 匹配.group(0)
                if 词 in 已知 or len(词) < 2:
                    continue
                最好 = None
                for 备选 in 已知:
                    if abs(len(备选) - len(词)) > 2:
                        continue
                    距离 = _编辑距离(词, 备选)
                    if 距离 <= _容错(词) and (最好 is None or 距离 < 最好[0]):
                        最好 = (距离, 备选)
                if 最好:
                    候选.append((最好[0], 号, 词, 最好[1], 已知[最好[1]]))

    if not 候选:
        return []
    候选.sort(key=lambda x: (x[0], x[1]))
    出: list[str] = []
    见过: Counter[str] = Counter()
    for 距离, 号, 词, 备选, 目标 in 候选:
        if 见过[(号, 词)]:
            continue
        见过[(号, 词)] += 1
        出.append(f'第 {号} 行：「{词}」是不是想写「{备选}」（= {目标}）？')
        if len(出) >= 最多:
            break
    return 出


def 未认识词(源码: str, 规则: dict, *, 最多: int = 5) -> list[str]:
    """列出源码里"完全没在规则表出现过、也不像标识符用法"的中文词（可选诊断）"""
    已知 = _已知表(规则)
    计数: Counter[str] = Counter()
    for 种类, 文本 in 分段(源码):
        if 种类 != '代码':
            continue
        for 匹配 in 汉字.finditer(文本):
            词 = 匹配.group(0)
            if 词 not in 已知:
                计数[词] += 1
    return [词 for 词, _ in 计数.most_common(最多)]


def 找近似(词: str, 规则: dict) -> tuple[str, str] | None:
    """给一个中文词，找规则表里最接近的写法，返回 (备选, 目标) 或 None

    运行期报错（`name '求长肚' is not defined`）也用它——那多半是内建名打错了。
    """
    已知 = _已知表(规则)
    if not 已知 or 词 in 已知 or len(词) < 2:
        return None
    最好: tuple[int, str] | None = None
    for 备选 in 已知:
        if abs(len(备选) - len(词)) > 2:
            continue
        距离 = _编辑距离(词, 备选)
        if 距离 <= _容错(词) and (最好 is None or 距离 < 最好[0]):
            最好 = (距离, 备选)
    if not 最好:
        return None
    return 最好[1], 已知[最好[1]]


def 编译建议(源码: str, 行号: int | None, 规则: dict) -> str:
    """给 方言错误 用的整段建议文本（没有建议就返回空串）"""
    行们 = 建议(源码, 行号, 规则)
    if not 行们:
        return ''
    return '\n可能的原因：\n' + '\n'.join(f'  · {行}' for 行 in 行们)
