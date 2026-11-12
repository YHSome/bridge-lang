"""把运行时塞进编译产物，让 `桥.py 编译 --自包含` 出来的 .py 少依赖

原理很笨但可靠：把 `转译器/运行时.py` 的源码改写成"绝对导入版"，
直接贴在产物开头执行。这样跳转/文件/文档/JSON/表格都能脱离 `from 转译器.运行时 import …`。

`运行` / `并行` 仍然需要转译器本体（要现场编译目标 .bridge），所以这两个函数
在产物里会额外补一句 sys.path —— 那是唯一的外部依赖。
"""

from __future__ import annotations

from pathlib import Path

_缓存: str | None = None


def 生成前缀() -> str:
    """返回可以直接贴在编译产物开头的自包含运行时（含必要 import）"""
    global _缓存
    if _缓存 is not None:
        return _缓存

    源 = (Path(__file__).with_name('运行时.py')).read_text(encoding='utf-8')
    # 去掉模块 docstring（第一段三引号），产物会变得很吵
    起 = 源.find('"""')
    if 起 != -1:
        止 = 源.find('"""', 起 + 3)
        if 止 != -1:
            源 = 源[止 + 3:]
    # 相对导入 → 绝对导入（产物不在 转译器 包里）
    源 = 源.replace('from __future__ import annotations', '# (future import 已去掉：产物不在文件开头)')
    源 = 源.replace('from .主转译器 import 编译', 'from 转译器.主转译器 import 编译')
    源 = 源.replace('from .运行时 import 运行时名字', 'pass  # 已在同一命名空间')

    _缓存 = (
        '# ==== 桥语言自包含运行时（由 桥.py 编译 --自包含 生成）====\n'
        + 源.strip('\n')
        + '\n# ==== 自包含运行时结束 ====\n'
    )
    return _缓存
