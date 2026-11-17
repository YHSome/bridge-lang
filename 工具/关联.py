"""把 `.bridge` 关联到「运行」或「编辑器」（只写 HKCU，不需要管理员）

    python 工具/关联.py              # 只看会写什么（默认安全模式）
    python 工具/关联.py --运行        # 双击 .bridge = 运行它（像 .py 一样，会弹控制台）
    python 工具/关联.py --编辑器      # 双击 .bridge = 打开编辑器
    python 工具/关联.py --卸载

写的位置：

    HKCU\\Software\\Classes\\.bridge                                → BridgeLangFile
    HKCU\\Software\\Classes\\BridgeLangFile                         → "桥语言源文件"
    HKCU\\Software\\Classes\\BridgeLangFile\\DefaultIcon            → python.exe
    HKCU\\Software\\Classes\\BridgeLangFile\\shell\\open\\command   → 双击（按模式）
    HKCU\\Software\\Classes\\BridgeLangFile\\shell\\edit\\command   → 右键「编辑」

两种模式都保留 `编辑` 这个右键动词，所以：
选「运行」之后，想改代码仍然可以右键 → 编辑。
"""

from __future__ import annotations

import sys
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
编辑器 = 项目根 / '桥编辑器.pyw'
运行器 = 项目根 / '桥运行.py'
python = Path(sys.executable)
pythonw = python.with_name('pythonw.exe')

ProgID = 'BridgeLangFile'
根 = r'Software\Classes'


def 计划(模式: str = '运行') -> list[tuple[str, str, str]]:
    """(键路径, 值名, 值)；值名为空串表示默认值"""
    用python = python if python.exists() else pythonw
    if 模式 == '编辑器':
        打开 = f'"{pythonw if pythonw.exists() else python}" "{编辑器}" "%1"'
    else:
        打开 = f'"{用python}" "{运行器}" "%1"'
    编辑 = f'"{pythonw if pythonw.exists() else 用python}" "{编辑器}" "%1"'
    return [
        (rf'{根}\.bridge', '', ProgID),
        (rf'{根}\.bridge', 'Content Type', 'text/x-bridge'),
        (rf'{根}\{ProgID}', '', '桥语言源文件'),
        (rf'{根}\{ProgID}\DefaultIcon', '', f'"{用python}",0'),
        (rf'{根}\{ProgID}\shell\open\command', '', 打开),
        (rf'{根}\{ProgID}\shell\edit', '', '编辑'),
        (rf'{根}\{ProgID}\shell\edit\command', '', 编辑),
    ]


def _当前() -> str:
    """读一下当前 open 命令，判断现在是哪种模式"""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            rf'{根}\{ProgID}\shell\open\command') as 句柄:
            值, _ = winreg.QueryValueEx(句柄, '')
    except (FileNotFoundError, OSError):
        return '（未关联）'
    if '桥运行.py' in 值:
        return f'运行（{值}）'
    if '桥编辑器.pyw' in 值:
        return f'编辑器（{值}）'
    return f'其它（{值}）'


def 查看() -> int:
    当前 = _当前()
    模式 = '编辑器' if '编辑器' in 当前 else '运行'
    print(f'当前关联：{当前}\n')
    print(f'如果现在执行「--{模式}」，会写入（HKCU，不需要管理员）：')
    for 键, 名, 值 in 计划(模式):
        print(f'  HKCU\\{键}' + (f'\\{名}' if 名 else '') + f'  =  {值}')
    print()
    print('用法：')
    print('  python 工具/关联.py --运行      # 双击 = 运行（推荐，像 .py 一样）')
    print('  python 工具/关联.py --编辑器    # 双击 = 打开编辑器')
    print('  python 工具/关联.py --卸载      # 取消关联')
    return 0


def 安装(模式: str) -> int:
    try:
        import winreg
    except ImportError:
        print('只有 Windows 支持文件关联；其它系统请用命令行或 shebang 运行。',
              file=sys.stderr)
        return 1

    for 键, 名, 值 in 计划(模式):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, 键) as 句柄:
            winreg.SetValueEx(句柄, 名, 0, winreg.REG_SZ, 值)

    if 模式 == '运行':
        print('已关联：双击 .bridge = 运行它（会弹出控制台窗口，结束等你按回车）')
        print('想改代码：右键 → 编辑；想换成双击打开编辑器：--编辑器')
    else:
        print('已关联：双击 .bridge = 打开编辑器')
        print('想双击运行：--运行')
    print(f'运行器：{运行器}')
    print(f'解释器：{python}')
    print('撤销：python 工具/关联.py --卸载')
    return 0


def 卸载() -> int:
    try:
        import winreg
    except ImportError:
        return 1

    for 键, 名, _ in 计划('运行') + 计划('编辑器'):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 键, 0,
                                winreg.KEY_SET_VALUE) as 句柄:
                winreg.DeleteValue(句柄, 名)
        except (FileNotFoundError, OSError):
            pass
    for 键 in (rf'{根}\{ProgID}\shell\edit\command',
              rf'{根}\{ProgID}\shell\edit',
              rf'{根}\{ProgID}\shell\open\command',
              rf'{根}\{ProgID}\shell\open',
              rf'{根}\{ProgID}\shell',
              rf'{根}\{ProgID}\DefaultIcon',
              rf'{根}\{ProgID}',
              rf'{根}\.bridge'):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, 键)
        except (FileNotFoundError, OSError):
            pass
    print('已取消关联（.bridge 恢复成"未知文件"）')
    return 0


def main(参数: list[str]) -> int:
    if '--安装' in 参数 or '--install' in 参数:
        参数 = 参数 + ['--运行']
    if '--运行' in 参数 or '--run' in 参数:
        return 安装('运行')
    if '--编辑器' in 参数 or '--editor' in 参数:
        return 安装('编辑器')
    if '--卸载' in 参数 or '--uninstall' in 参数:
        return 卸载()
    return 查看()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
