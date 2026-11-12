"""规则加载：扫描 `规则/` 目录下所有 `.py`，把里面导出的表合并成一份只读规则集

设计要点：

1. **零注册**：丢一个 `规则/xxx.py` 进去就生效，不需要改任何 `import`；
2. **冲突显式化**：两个规则文件给同一个方言词不同的 Python 值 → 直接抛 `规则冲突`，
   而不是后加载的静默覆盖（这种 bug 最难查）；
3. **缓存**：合并结果缓存在内存里，重复转译不再重复扫描磁盘。
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

# 规则文件里允许出现的表名。加新表 → 在这里登记 + 在 主转译器 里消费它
表名 = ('关键字', '内建', '异常', '标点', '模块', '成员', '方法', '值位置', '助词',
        '异常名', '消息', '语法糖')

# 这几张表是「列表」而不是「字典」，加载时追加合并
列表表 = ('消息', '语法糖')


class 规则冲突(Exception):
    """同一个方言词被两条规则映射成了不同的 Python 代码"""


_缓存: dict | None = None
_来源: dict[str, str] = {}


def _登记(表: dict, 键: str, 值, 文件: str, 类别: str) -> None:
    旧 = 表.get(键)
    if 旧 is not None and 旧 != 值:
        旧文件 = _来源.get(f'{类别}.{键}', '?')
        raise 规则冲突(
            f'{类别} 规则冲突：{键!r} 在 {旧文件} 里是 {旧!r}，在 {文件} 里是 {值!r}'
        )
    表[键] = 值
    _来源[f'{类别}.{键}'] = 文件


def 载入规则(强制: bool = False) -> dict:
    """扫描并合并全部规则文件，返回规则集字典"""
    global _缓存
    if _缓存 is not None and not 强制:
        return _缓存

    from . import 规则 as 规则包

    合并 = {名: ([] if 名 in 列表表 else {}) for 名 in 表名}
    来源表 = {}
    for 信息 in pkgutil.iter_modules(规则包.__path__):
        if 信息.name.startswith('_'):
            continue
        文件 = f'{信息.name}.py'
        模块 = importlib.import_module(f'{规则包.__name__}.{信息.name}')
        来源表[文件] = []
        for 名 in 表名:
            表 = getattr(模块, 名, None)
            if not 表:
                continue
            来源表[文件].append(f'{名}({sum(len(v) for v in 表.values())})' if 名 == '成员' else f'{名}({len(表)})')
            if 名 in 列表表:
                合并[名].extend(表)
                continue
            for 键, 值 in 表.items():
                if not isinstance(值, (str, dict)):
                    raise 规则冲突(f'{文件} 的 {名}[{键!r}] 必须是 str 或 dict，实际是 {type(值).__name__}')
                if 名 == '成员':
                    for 成员键, 成员值 in 值.items():
                        _登记(合并['成员'].setdefault(键, {}), 成员键, 成员值, 文件, f'成员.{键}')
                else:
                    _登记(合并[名], 键, 值, 文件, 名)

    # 模块别名 **不进** 通用词表：`数据库` 这种词只在 `导入` 行和点号前有意义，
    # 直接替换会把 `数据库 = 1` 改成 `sqlite3 = 1`（这个坑踩过）。
    合并['词表'] = {**合并['关键字'], **合并['内建'], **合并['异常']}
    合并['全角表'] = {ord(k): v for k, v in 合并['标点'].items()}
    合并['长键'] = sorted(合并['词表'], key=len, reverse=True)
    # 反查：真实模块名 → 中文别名。这样 `json.转字符串` 和 `JSON.转字符串` 都能认
    合并['模块反查'] = {英: 中 for 中, 英 in 合并['模块'].items()}
    合并['_来源'] = 来源表
    _缓存 = 合并
    return 合并


def 规则清单() -> dict[str, list[str]]:
    """返回 {规则文件: ['关键字(33)', '内建(24)', ...]}，给 `桥 规则` 命令用"""
    载入规则()
    return dict(_缓存['_来源'])


def 规则文件路径() -> Path:
    from . import 规则 as 规则包
    return Path(规则包.__path__[0])
