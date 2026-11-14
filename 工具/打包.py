"""打「桥」便携包：解压到项目根目录就能用，不装 pip、不配环境变量

    python 工具/打包.py                 # 精简包（只留运行时+示例+AI 文档）
    python 工具/打包.py --完整          # 完整包（加教程/工具/自检/对照用例/文档）
    python 工具/打包.py --版本 0.2      # 指定版本

设计原则（跟“重装环境”那一套反着来）：

1. **零安装**：包内自带 桥.py / 转译器 / 规则表，`python 桥/桥.py 运行 x.bridge` 直接跑；
2. **零配置**：不读注册表、不读 HOME 下的配置，所有路径都从 `__file__` 推出来；
3. **不污染项目**：解压出来只有一个 `桥/` 目录，你的 `.bridge` 放项目根，跟它平级；
4. **可搬运**：整个 `桥/` 拷到 U 盘、换台电脑（有 Python 3.10+）照样跑；
5. **可校验**：同时生成 `校验.txt`（SHA-256），发出去能对账。

打进包里的东西是白名单，`实验-oj转桥/`、缓存、测试数据、`发布/` 本身都不进。
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
发布目录 = 项目根 / '发布'

# 包内保留的文件（相对项目根）
# 精简包（默认）：只留"能跑起来 + 看示例 + 喂 AI"的东西
包含文件 = [
    '桥.py',
    'bridge.py',
    '命令.py',
    '桥编辑器.pyw',
    '桥编辑器.bat',
    '快速开始.md',
    'AI参考.md',
    'AI速查.txt',
    'AGENTS.md',
    'LICENSE',
    '版本.txt',
]

包含目录 = [
    '转译器',
]

# 精简包只放 3 个"给 AI 看写法"的示例；其余示例在文档页/GitHub 上看
示例文件 = [
    '示例/示例1.bridge',
    '示例/混写演示.bridge',
    '示例/标准库.bridge',
]

# --完整：把教程、工具、自检、对照用例、文档也带上（开发和教学用）
完整文件 = [
    '自检.py',
    'README.md',
    '架构.md',
    '交付说明.md',
]
完整目录 = [
    'vscode-桥语言',
    '示例',
    '工具',
    '金标准',
    '教程',
    '特性清单',
    'docs',
]

# 不进包的东西
排除目录名 = {'__pycache__', '发布', '实验-oj转桥', '.git', '.github', '.运行临时'}
排除文件后缀 = {'.pyc', '.bridgec'}
排除文件名 = {'图书数据.json', '.DS_Store', 'Thumbs.db'}


def _要包含(路径: Path) -> bool:
    if 路径.name in 排除目录名:
        return False
    if 路径.suffix in 排除文件后缀 or 路径.suffix == '.bak':
        return False
    if 路径.name in 排除文件名 or 路径.name.startswith('图书数据.json.'):
        return False
    return True


def 收集(完整: bool = False) -> list[tuple[Path, str]]:
    """返回 [(磁盘路径, 包内相对路径)]"""
    结果: list[tuple[Path, str]] = []
    for 名 in 包含文件 + 示例文件 + (完整文件 if 完整 else []):
        文件 = 项目根 / 名
        if 文件.is_file():
            结果.append((文件, 名))
    for 目录名 in 包含目录 + (完整目录 if 完整 else []):
        目录 = 项目根 / 目录名
        if not 目录.is_dir():
            continue
        for 文件 in sorted(目录.rglob('*')):
            if not 文件.is_file() or not _要包含(文件):
                continue
            结果.append((文件, 文件.relative_to(项目根).as_posix()))
    return 结果


def 生成目录(包目录: Path, 文件们: list[tuple[Path, str]]) -> None:
    shutil.rmtree(包目录, ignore_errors=True)
    for 源, 相对 in 文件们:
        目标 = 包目录 / 相对
        目标.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(源, 目标)


def 生成启动脚本(包目录: Path) -> None:
    """桥.bat：双击就能用（ASCII-only，避免 cmd 的 OEM 代码页乱码）"""
    (包目录 / '桥.bat').write_text(
        '@echo off\r\n'
        'rem Portable launcher: ASCII-only, so the cmd code page never matters.\r\n'
        'setlocal\r\n'
        'python "%~dp0bridge.py" %*\r\n',
        encoding='ascii', newline='',
    )
    (包目录 / '桥.sh').write_text(
        '#!/bin/sh\n'
        '# Portable launcher for macOS / Linux (chmod +x this file)\n'
        'exec python3 "$(dirname "$0")/bridge.py" "$@"\n',
        encoding='ascii', newline='',
    )


def 生成校验(包目录: Path, 版本: str) -> Path:
    行们 = [f'桥语言便携包 v{版本}', f'文件数：{sum(1 for _ in 包目录.rglob("*") if _.is_file())}', '']
    for 文件 in sorted(包目录.rglob('*')):
        if not 文件.is_file():
            continue
        摘要 = hashlib.sha256(文件.read_bytes()).hexdigest()
        行们.append(f'{摘要}  {文件.relative_to(包目录).as_posix()}')
    校验文件 = 包目录 / '校验.txt'
    校验文件.write_text('\n'.join(行们) + '\n', encoding='utf-8')
    return 校验文件


def 打包(版本: str, 只留目录: bool, 完整: bool = False) -> int:
    文件们 = 收集(完整)
    看过的: set[str] = set()
    去重们 = []
    for 对 in 文件们:
        if 对[1] in 看过的:
            continue
        看过的.add(对[1])
        去重们.append(对)
    文件们 = 去重们
    包目录 = 发布目录 / '桥'
    发布目录.mkdir(parents=True, exist_ok=True)

    生成目录(包目录, 文件们)
    生成启动脚本(包目录)
    if (项目根 / '快速开始.md').is_file():
        shutil.copy2(项目根 / '快速开始.md', 包目录 / '快速开始.md')
    生成校验(包目录, 版本)

    if not 只留目录:
        压缩包 = 发布目录 / f'桥-{版本}{"-完整" if 完整 else ""}.zip'
        压缩包.unlink(missing_ok=True)
        with zipfile.ZipFile(压缩包, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as 包:
            for 文件 in sorted(包目录.rglob('*')):
                if not 文件.is_file():
                    continue
                相对 = (Path('桥') / 文件.relative_to(包目录)).as_posix()
                信息 = zipfile.ZipInfo(相对, date_time=(2026, 1, 1, 0, 0, 0))
                信息.compress_type = zipfile.ZIP_DEFLATED
                信息.external_attr = 0o644 << 16
                包.writestr(信息, 文件.read_bytes())
        摘要 = hashlib.sha256(压缩包.read_bytes()).hexdigest()
        大小 = 压缩包.stat().st_size / 1024 / 1024
        print(f'压缩包：{压缩包}')
        print(f'大小：{大小:.2f} MB')
        print(f'SHA-256：{摘要}')
        print(f'校验清单：{包目录 / "校验.txt"}')
    else:
        print(f'目录：{包目录}')

    总大小 = sum(f.stat().st_size for f in 包目录.rglob('*') if f.is_file())
    print(f'文件数：{sum(1 for f in 包目录.rglob("*") if f.is_file())}，'
          f'解压后 {总大小 / 1024 / 1024:.2f} MB')
    print()
    print('用法（解压到任意项目根目录后）：')
    print('  python 桥/桥.py 运行 你的程序.bridge')
    print('  python 桥/桥.py 体检')
    print('  python 桥/自检.py            # 可选：验一下包是好的')
    return 0


def main(参数: list[str]) -> int:
    版本 = '0.2.0'
    for i, 段 in enumerate(参数):
        if 段 in ('--版本', '-v') and i + 1 < len(参数):
            版本 = 参数[i + 1]
    return 打包(版本, 只留目录='--只目录' in 参数, 完整='--完整' in 参数)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
