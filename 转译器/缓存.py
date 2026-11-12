"""编译产物缓存：转译结果按「文件 + 规则指纹」缓存，命中就跳过扫描

为什么要缓存：转译本身是毫秒级，但编辑器里 F5 一下、脚本里循环调用时，
每次都重新扫描文件 + 重新算词表，属于纯浪费。缓存的判定键是：

    路径 + 大小 + mtime + 规则指纹 + 转译器版本

**规则指纹**是关键：你改了 `规则/` 里任何一张表（哪怕加一个词），指纹就变，
所有旧缓存自动失效——不会出现"改了规则但跑的还是老产物"这种鬼故事。

缓存文件放在源码旁边的 `__pycache__/桥缓存/`，存的是**转译后的标准 Python 源码**，
所以出问题时可以直接打开看（也能直接 `python` 跑），不会被泡成二进制黑盒。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .规则加载 import 载入规则
from .主转译器 import 版本, 编译

缓存目录名 = '桥缓存'
后缀 = '.bridgec'

_指纹缓存: str | None = None

# 参与指纹的表：改了这些表就必须让缓存失效
_指纹键 = ('关键字', '内建', '异常', '标点', '模块', '成员', '方法',
           '值位置', '助词', '语法糖', '异常名', '消息')


def 规则指纹(规则: dict | None = None, 强制: bool = False) -> str:
    """把所有规则表揉成一个短哈希"""
    global _指纹缓存
    if _指纹缓存 is not None and not 强制:
        return _指纹缓存
    规 = 规则 or 载入规则()
    材料 = {键: 规.get(键) for 键 in _指纹键}
    材料['版本'] = 版本
    原文 = json.dumps(材料, ensure_ascii=False, sort_keys=True, default=str)
    _指纹缓存 = hashlib.sha1(原文.encode('utf-8')).hexdigest()[:12]
    return _指纹缓存


def _缓存路径(源码路径: Path, 指纹: str) -> Path:
    统计 = 源码路径.stat()
    键 = f'{源码路径.name}|{统计.st_size}|{int(统计.st_mtime)}|{指纹}'
    短哈希 = hashlib.sha1(键.encode('utf-8')).hexdigest()[:16]
    return 源码路径.parent / '__pycache__' / 缓存目录名 / f'{源码路径.stem}.{短哈希}{后缀}'


def 编译文件(源码路径: str | Path, *, 规则: dict | None = None,
             使用缓存: bool = True) -> tuple[object, str, bool]:
    """编译一个 .bridge 文件

    返回 (code, 转译后的源码, 是否命中缓存)。
    """
    路径 = Path(源码路径)
    规 = 规则 or 载入规则()
    指纹 = 规则指纹(规)

    if 使用缓存:
        缓存文件 = _缓存路径(路径, 指纹)
        if 缓存文件.is_file():
            try:
                产物 = 缓存文件.read_text(encoding='utf-8')
                return compile(产物, str(路径), 'exec'), 产物, True
            except (OSError, SyntaxError):
                pass                      # 缓存坏了就当没命中，重新生成

    源码 = 路径.read_text(encoding='utf-8-sig')
    代码, 产物 = 编译(源码, str(路径), 规则=规)

    if 使用缓存:
        try:
            缓存文件.parent.mkdir(parents=True, exist_ok=True)
            缓存文件.write_text(产物, encoding='utf-8')
            _清理同源旧缓存(缓存文件)
        except OSError:
            pass                          # 缓存写不进去（只读目录）不影响运行
    return 代码, 产物, False


def _清理同源旧缓存(新缓存: Path) -> None:
    """同一个 .bridge 只留最新一份缓存，避免 __pycache__ 里越积越多"""
    前缀 = 新缓存.name.split('.')[0] + '.'
    for 旧 in 新缓存.parent.glob(f'{前缀}*{后缀}'):
        if 旧 != 新缓存:
            try:
                旧.unlink()
            except OSError:
                pass


def 缓存信息(根目录: str | Path | None = None) -> dict:
    """统计缓存文件数与占用字节"""
    根 = Path(根目录) if 根目录 else Path(__file__).resolve().parent.parent
    文件们 = [p for p in 根.rglob(f'*{后缀}')]
    return {
        '文件数': len(文件们),
        '字节数': sum(p.stat().st_size for p in 文件们),
        '指纹': 规则指纹(),
    }


def 清理缓存(根目录: str | Path | None = None) -> int:
    """删掉所有缓存文件，返回删掉的个数"""
    根 = Path(根目录) if 根目录 else Path(__file__).resolve().parent.parent
    个数 = 0
    for 目录 in 根.rglob(缓存目录名):
        if not 目录.is_dir():
            continue
        for 文件 in 目录.glob(f'*{后缀}'):
            try:
                文件.unlink()
                个数 += 1
            except OSError:
                pass
        try:
            目录.rmdir()
        except OSError:
            pass
    return 个数
