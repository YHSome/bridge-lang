"""把「建 Release」的最后一步压到 3 次点击：打开预填好的发版页

    python 工具/打开发版页.py            # 只打印链接和要上传的文件
    python 工具/打开发版页.py --打开      # 顺手用默认浏览器打开（预填 tag / 标题 / 说明）

为什么需要它：建 Release 必须带账号登录态，脚本用 API 得先有 token；
不想给 token 的时候，用这个把"填 tag、写说明、改文件名"全省掉，
你只需要**把 3 个文件拖进网页 → 点 Publish**。

文件已经按 ASCII 名准备好（首页下载链接用的就是这些名字）：
    发布/上传-<版本>/bridge-lang-<版本>.zip
    发布/上传-<版本>/bridge-lang-<版本>-full.zip
    发布/上传-<版本>/bridge-lang-vscode-<版本>.vsix
"""

from __future__ import annotations

import sys
import urllib.parse
import webbrowser
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(项目根 / '工具'))

默认仓库 = 'YHSome/bridge-lang'


def main(参数: list[str]) -> int:
    版本 = (项目根 / '版本.txt').read_text(encoding='utf-8').strip()
    标签 = f'v{版本}'
    仓库 = 默认仓库
    if '--仓库' in 参数:
        仓库 = 参数[参数.index('--仓库') + 1]
    if '--标签' in 参数:
        标签 = 参数[参数.index('--标签') + 1]
        版本 = 标签.lstrip('v')

    try:
        from 发版 import _说明  # 和 API 发版用同一份说明，避免两处不一致

        说明 = _说明(版本)
    except Exception:            # noqa: BLE001
        说明 = f'桥语言 {标签}'

    上传目录 = 项目根 / '发布' / f'上传-{版本}'
    文件们 = sorted(上传目录.glob('*')) if 上传目录.is_dir() else []

    查询 = urllib.parse.urlencode({
        'tag': 标签,
        'title': f'桥语言 {标签}',
        'body': 说明,
    })
    地址 = f'https://github.com/{仓库}/releases/new?{查询}'

    print(f'仓库：{仓库}   标签：{标签}')
    print(f'要上传的目录：{上传目录}')
    for 文件 in 文件们:
        print(f'  · {文件.name}  ({文件.stat().st_size / 1024:.0f} KB)')
    if not 文件们:
        print('  （目录是空的：先跑 python 工具/发版.py --只打包）')
    print()
    print('发版页（已预填 tag / 标题 / 说明）：')
    print(地址)
    print()
    print('接下来：拖 3 个文件进网页 → 点 Publish release → 首页下载按钮就通了。')

    if '--打开' in 参数:
        if webbrowser.open(地址):
            print('\n（已用默认浏览器打开；那里需要你的 GitHub 登录态）')
        else:
            print('\n（没能自动打开浏览器，请手动复制上面的链接）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
