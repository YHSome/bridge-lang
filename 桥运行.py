"""双击 `.bridge` 直接运行（窗口不会一闪就关）

    python 桥运行.py 你好.bridge
    python 桥运行.py 你好.bridge --不暂停

做的事：

1. **把工作目录切到 `.bridge` 所在目录** —— 双击时用户就在"那个文件夹"里，
   `读取("数据.csv")` 这类相对路径要按它解析，才符合直觉；
2. 用子进程调 `桥.py 运行`：`.bridge` 崩了也不影响本窗口把中文报错显示出来；
3. 结束时**停下来等你按回车**（双击时窗口才不会闪退）。

什么时候不暂停：

- 参数里加了 `--不暂停`；
- 环境变量 `BRIDGE_NO_PAUSE=1`；
- 不是终端（CI / 管道 / 重定向）时自动跳过，免得卡住自动化。

配合 `python 工具/关联.py --运行`，双击 `.bridge` 就等于运行它（像 `.py` 那样）。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

项目根 = Path(__file__).resolve().parent
桥入口 = 项目根 / '桥.py'


def _是终端() -> bool:
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except Exception:
        return False


def _停一下() -> None:
    if os.environ.get('BRIDGE_NO_PAUSE') == '1' or not _是终端():
        return
    try:
        input('\n按回车键关闭窗口…')
    except (EOFError, KeyboardInterrupt):
        pass


def main(参数: list[str]) -> int:
    不暂停 = '--不暂停' in 参数 or '--no-pause' in 参数
    路径们 = [段 for 段 in 参数 if not 段.startswith('-')]

    if not 路径们:
        print('用法：python 桥运行.py <文件.bridge> [--不暂停]')
        print('（想双击运行：先跑 python 工具/关联.py --运行）')
        if not 不暂停:
            _停一下()
        return 2

    文件 = Path(路径们[0])
    if not 文件.is_file():
        print(f'找不到文件：{文件}', file=sys.stderr)
        if not 不暂停:
            _停一下()
        return 2
    if not 桥入口.is_file():
        print(f'找不到 桥.py（应该和本文件同级）：{桥入口}', file=sys.stderr)
        if not 不暂停:
            _停一下()
        return 2

    # 相对路径按 .bridge 所在目录解析（双击的直觉）
    目录 = 文件.resolve().parent
    try:
        os.chdir(目录)
    except OSError as 错误:
        print(f'切不过去目录：{目录}（{错误}）', file=sys.stderr)

    命令 = [sys.executable, str(桥入口), '运行', 文件.name]
    环境 = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    try:
        完成 = subprocess.run(命令, cwd=str(目录), env=环境)
        码 = 完成.returncode
    except KeyboardInterrupt:
        码 = 130
    except Exception as 错误:                      # noqa: BLE001
        print(f'启动失败：{type(错误).__name__}: {错误}', file=sys.stderr)
        码 = 1

    if 码 != 0:
        print(f'\n（退出码 {码}）', file=sys.stderr)
    if not 不暂停:
        _停一下()
    return 码


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
