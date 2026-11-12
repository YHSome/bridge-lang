"""把整个 Python 项目翻成桥语言，**连模块文件名和变量名一起中文化**

    python 工具/译项目.py <源码目录> -o <输出目录>

比 `反向译 --译名` 多做两步：

1. **模块文件名**：`ui.py` → `界面.py`、`db.py` → `数据库.py`……；
2. **导入语句**：`from . import ui, db` → `from . import 界面, 数据库`
   （`from .sandbox import run` 这种也换）。

然后才调 `反向译 --译名` 做逐文件转换。模块名必须连文件一起改，否则 `导入 界面`
根本找不到模块——这也是为什么这一步单独抽出来。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(项目根))
sys.path.insert(0, str(项目根 / '工具'))

import 译名  # noqa: E402

_导入行 = re.compile(
    r'^(?P<缩进>\s*)from\s+(?P<包>\.{1,2}|[A-Za-z_\u3400-\u9fff][\w.]*)\s+import\s+(?P<名>.+?)\s*(?P<注释>#.*)?$')


def _模块改名(文件们: list[Path], 根: Path) -> dict[str, str]:
    名字 = {p.stem for p in 文件们 if p.stem != '__init__'}
    映射, 冲突 = 译名.分配(名字)
    if 冲突:
        print('模块撞名：', 冲突)
    # 模块名不能撞规则表：像 paths → 路径，而「路径」是 os.path 的中文别名，导入 路径 会被翻成 import os.path
    from 转译器.规则加载 import 载入规则

    规则 = 载入规则()
    禁用 = set(规则['词表']) | set(规则['方法']) | set(规则['模块'])
    for 表 in (规则['成员'] or {}).values():
        禁用 |= set(表)
    改后: dict[str, str] = {}
    for 英, 中 in 映射.items():
        if 中 in 禁用:
            中 = '项目' + 中
        # 模块名统一带「模块」后缀：避免和普通变量撞中文名（p→题目 与模块 题目 会打架）
        改后[英] = 中 + '模块'
    return 改后


def _换名(件: str, 映射: dict[str, str]) -> str:
    """换一个导入项：`ui` / `ui as x` / `ui.x`"""
    段 = 件.split(' as ')
    头 = 段[0].strip()
    if 头 in 映射:
        头 = 映射[头]
    尾 = (' as ' + 段[1]) if len(段) > 1 else ''
    return 头 + 尾


def _改写引用(源码: str, 映射: dict[str, str]) -> str:
    """把源码里所有等于"旧模块名"的标识符换成新模块名

    比只改 import 行可靠：`judge.LANGUAGES` 这种用法也得跟着换，否则模块名改了、
    调用点还指着英文名，一跑就 NameError。
    """
    import io as _io
    import tokenize as _tk

    行们 = 源码.splitlines(keepends=True)
    编辑: list[tuple[tuple[int, int], tuple[int, int], str]] = []
    try:
        令牌们 = list(_tk.generate_tokens(_io.StringIO(源码).readline))
    except _tk.TokenError:
        return 源码
    for 件 in 令牌们:
        if 件.type == _tk.NAME and 件.string in 映射:
            编辑.append((件.start, 件.end, 映射[件.string]))
    for (行, 列), (_, 末列), 新 in sorted(编辑, key=lambda x: (x[0][0], x[0][1]), reverse=True):
        原文 = 行们[行 - 1]
        行们[行 - 1] = 原文[:列] + 新 + 原文[末列:]
    return ''.join(行们)


def _改写导入(源码: str, 映射: dict[str, str]) -> str:
    出: list[str] = []
    for 行 in 源码.splitlines(keepends=True):
        纯 = 行.rstrip('\n')
        匹配 = _导入行.match(纯)
        if not 匹配:
            出.append(行)
            continue
        包 = 匹配.group('包')
        名 = 匹配.group('名')
        # 包名里最后一段若是模块（`from .sandbox import …`）就换
        前缀 = ''
        包头 = 包
        if '.' in 包:
            头们 = 包.rsplit('.', 1)
            包头 = 头们[0] + '.' + 映射.get(头们[1], 头们[1])
        项们 = [_换名(件.strip(), 映射) for 件 in 名.split(',')]
        新行 = f"{匹配.group('缩进')}from {包头} import {', '.join(项们)}"
        if 匹配.group('注释'):
            新行 += '  ' + 匹配.group('注释')
        出.append(新行 + '\n')
    return ''.join(出)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print('用法：python 工具/译项目.py <源码目录> -o <输出目录>')
        return 2
    源 = Path(argv[1])
    出 = Path(argv[argv.index('-o') + 1]) if '-o' in argv else 源.parent / (源.name + '-译名')
    中间 = 项目根 / '.tmp' / '译项目_中间'
    shutil.rmtree(中间, ignore_errors=True)
    shutil.rmtree(出, ignore_errors=True)

    文件们 = sorted(源.rglob('*.py'))
    映射 = _模块改名(文件们, 源)
    print(f'模块改名 {len(映射)} 个：' + '、'.join(f'{k}→{v}' for k, v in list(映射.items())[:8]) + ' …')

    for 文件 in 文件们:
        相对 = 文件.relative_to(源)
        新相对 = 相对.with_name(映射.get(文件.stem, 文件.stem) + '.py')
        目标 = 中间 / 新相对
        目标.parent.mkdir(parents=True, exist_ok=True)
        源码 = 文件.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
        目标.write_text(_改写引用(源码, 映射), encoding='utf-8', newline='\n')

    完成 = subprocess.run(
        [sys.executable, str(项目根 / '工具' / '反向译.py'), str(中间), '--译名',
         '-o', str(出)],
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    尾巴 = [行 for 行 in 完成.stdout.splitlines() if 行.strip()]
    print('\n'.join(尾巴[-4:]))
    if 完成.returncode != 0:
        print(完成.stderr[-800:])
    # 自己再验一遍：把中文标识符与模块名都换回英文，应与**原始 .py** 逐字节一致
    import 反向译 as 反向
    from 改名 import 校验
    from 转译器 import 转译

    标识映射, _环境 = 反向._准备改名环境(中间, 译名)
    合并 = {**标识映射, **映射}
    坏: list[str] = []
    for 文件 in 文件们:
        相对 = 文件.relative_to(源)
        产物路径 = (出 / 相对).with_name(映射.get(文件.stem, 文件.stem) + '.bridge')
        if not 产物路径.is_file():
            坏.append(f'{相对}: 没生成 .bridge')
            continue
        问题 = 校验(文件.read_text(encoding='utf-8-sig').replace('\r\n', '\n'),
                    转译(产物路径.read_text(encoding='utf-8', newline='').replace('\r\n', '\n')), 合并)
        if 问题:
            坏.append(f'{相对}: {问题}')
    print(f'最终校验：{len(文件们) - len(坏)}/{len(文件们)} 一致')
    for 项 in 坏[:4]:
        print('  ✗', 项)
    shutil.rmtree(中间, ignore_errors=True)
    return 0 if not 坏 else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
