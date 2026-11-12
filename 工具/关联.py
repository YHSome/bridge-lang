"""把 .bridge 关联到桥语言编辑器（只写 HKCU，不需要管理员）

    python 工具/关联.py             # 只看会写什么（默认安全模式）
    python 工具/关联.py --安装
    python 工具/关联.py --卸载

写的位置：

    HKCU\\Software\\Classes\\.bridge                       → BridgeLangFile
    HKCU\\Software\\Classes\\BridgeLangFile                → "桥语言源文件"
    HKCU\\Software\\Classes\\BridgeLangFile\\DefaultIcon    → pythonw.exe
    HKCU\\Software\\Classes\\BridgeLangFile\\shell\\open\\command
        → "<pythonw>" "<桥编辑器.pyw>" "%1"
"""

from __future__ import annotations

import sys
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
编辑器 = 项目根 / '桥编辑器.pyw'
pythonw = Path(sys.executable).with_name('pythonw.exe')


def 计划() -> list[tuple[str, str, str]]:
    """(键路径, 值名, 值) 的清单；值名为空表示默认值"""
    根 = r'Software\Classes'
    return [
        (rf'{根}\.bridge', '', 'BridgeLangFile'),
        (rf'{根}\.bridge', 'Content Type', 'text/x-bridge'),
        (rf'{根}\BridgeLangFile', '', '桥语言源文件'),
        (rf'{根}\BridgeLangFile\DefaultIcon', '', f'"{pythonw}",0'),
        (rf'{根}\BridgeLangFile\shell\open\command', '',
         f'"{pythonw}" "{编辑器}" "%1"'),
    ]


def 查看() -> int:
    print('会写入（HKCU，当前用户，不需要管理员）：')
    for 键, 名, 值 in 计划():
        print(f'  HKCU\\{键}' + (f'\\{名}' if 名 else '') + f'  =  {值}')
    print()
    print(f'编辑器路径：{编辑器}')
    print(f'解释器路径：{pythonw}')
    print('确认无误后跑：python 工具/关联.py --安装')
    return 0


def 安装() -> int:
    import winreg

    for 键, 名, 值 in 计划():
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, 键) as 句柄:
            winreg.SetValueEx(句柄, 名, 0, winreg.REG_SZ, 值)
    print('已关联 .bridge → 桥编辑器.pyw（双击 .bridge 就会打开编辑器）')
    print('想撤销：python 工具/关联.py --卸载')
    return 0


def 卸载() -> int:
    import winreg

    失败 = 0
    for 键, 名, _ in 计划():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 键, 0,
                                winreg.KEY_SET_VALUE) as 句柄:
                winreg.DeleteValue(句柄, 名)
        except FileNotFoundError:
            失败 += 1
    for 键 in (r'Software\Classes\BridgeLangFile\shell\open\command',
              r'Software\Classes\BridgeLangFile\DefaultIcon',
              r'Software\Classes\BridgeLangFile', r'Software\Classes\.bridge'):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, 键)
        except FileNotFoundError:
            pass
    print('已取消关联（.bridge 恢复成"未知文件"）')
    return 0


def main(参数: list[str]) -> int:
    if Path(sys.executable).name.lower() != 'pythonw.exe' and not pythonw.exists():
        print('提示：没找到 pythonw.exe，关联后用 python.exe 会在双击时弹黑窗', file=sys.stderr)
    if '--安装' in 参数 or '--install' in 参数:
        return 安装()
    if '--卸载' in 参数 or '--uninstall' in 参数:
        return 卸载()
    return 查看()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
