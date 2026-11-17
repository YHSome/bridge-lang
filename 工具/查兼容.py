"""查兼容：扫出「只在更高版本 Python 上能跑」的写法

桥语言的 `pyproject.toml` 声明 `requires-python = ">=3.10"`，所以代码必须
在 3.10 上就能**解析**。但这类问题在本机（3.13）看不出来，只有 CI 的那一格会红
（2026-11 就踩过：`f'...{转译("?\\n")!r}'` 在 3.11 直接 SyntaxError）。

用法：

    python 工具/查兼容.py           # 有可疑写法就 exit 1
    python 工具/查兼容.py --全部     # 把每条命中都打出来

两类检查：

1. **f-string 里的反斜杠 / 同种引号**（3.12 才放开，PEP 701）；
2. **3.11+ 才有的 API**（tomllib / typing.Self / datetime.UTC / TaskGroup /
   ExceptionGroup / sys.exception …）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
跳过目录 = {'发布', '.git', '__pycache__', '.自检临时'}

_高版本接口 = (
    ('tomllib', '3.11 的 tomllib；3.10 用 tomli 或自己解析'),
    ('typing.Self', '3.11 的 typing.Self'),
    ('datetime.UTC', '3.11 的 datetime.UTC（3.10 用 timezone.utc）'),
    ('asyncio.TaskGroup', '3.11 的 TaskGroup'),
    ('ExceptionGroup', '3.11 的 ExceptionGroup'),
    ('except*', '3.11 的 except*'),
    ('sys.exception', '3.11 的 sys.exception'),
    ('itertools.batched', '3.12 的 itertools.batched'),
    ('typing.override', '3.12 的 typing.override'),
    ('Path.walk(', '3.12 的 Path.walk'),
)

_引号 = ('"', "'")


def _f字符串可疑(行: str) -> list[str]:
    """f-string 的 {} 里出现反斜杠或同种引号（3.12 之前非法）"""
    结果 = []
    for 引号 in _引号:
        模式 = re.compile(rf'(?P<前缀>[fF][rR]?|[rR][fF]){引号}'
                          rf'(?P<体>(?:[^{引号}]|\{{[^}}]*\}})*){引号}')
        for 命中 in 模式.finditer(行):
            for 花 in re.finditer(r'\{([^{}]*)\}', 命中.group('体')):
                内 = 花.group(1)
                if '\\' in 内:
                    结果.append(f'f-string 的 {{}} 里有反斜杠（3.12+ 才允许）：{内.strip()[:40]}')
                elif 引号 in 内:
                    结果.append(f'f-string 的 {{}} 里有同种引号（3.12+ 才允许）：{内.strip()[:40]}')
    return 结果


def 扫(文件: Path) -> list[tuple[int, str]]:
    问题: list[tuple[int, str]] = []
    try:
        行们 = 文件.read_text(encoding='utf-8-sig').splitlines()
    except OSError:
        return 问题
    for 号, 行 in enumerate(行们, 1):
        for 说明 in _f字符串可疑(行):
            问题.append((号, 说明))
        for 接口, 解释 in _高版本接口:
            if 接口 in 行:
                问题.append((号, f'用了 {接口}（{解释}）'))
    return 问题


def main(参数: list[str]) -> int:
    全打 = '--全部' in 参数
    命中 = 0
    文件们 = [f for f in 项目根.rglob('*.py')
              if not (跳过目录 & set(f.relative_to(项目根).parts)) and f.name != Path(__file__).name]
    for 文件 in sorted(文件们):
        问题 = 扫(文件)
        if not 问题:
            continue
        命中 += len(问题)
        相对 = 文件.relative_to(项目根).as_posix()
        print(f'{相对}：{len(问题)} 处')
        for 号, 说明 in (问题 if 全打 else 问题[:3]):
            print(f'  第 {号} 行  {说明}')
    if 命中:
        print(f'\n共 {命中} 处可能只在更高版本 Python 上能跑（声明是 >=3.10）')
        return 1
    print(f'兼容性扫描通过（{len(文件们)} 个文件，未发现 3.11+/3.12+ 专属写法）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
