"""一条命令发版：打包 → 建 GitHub Release → 上传三个附件

    set GITHUB_TOKEN=ghp_xxx
    python 工具/发版.py                    # 按 版本.txt 发当前版本
    python 工具/发版.py --标签 v0.4.1       # 给历史 tag 补发
    python 工具/发版.py --只打包            # 只出 zip，不碰网络
    python 工具/发版.py --草稿              # 建草稿，网页上再点发布

它做的事：

1. 读 `版本.txt`，算出 tag（`v0.4.1`）；
2. 调 `工具/打包.py`（精简 + 完整）和 `工具/打包VSCode插件.py`；
3. `POST /repos/{仓库}/releases` 建 Release（已存在就只更新说明）；
4. 把三个文件传上去，并把 `桥-0.4.1.zip` 改名为 `bridge-lang-0.4.1.zip`（和首页链接一致）。

Token 从哪来：环境变量 `GITHUB_TOKEN` / `GH_TOKEN`，或 `gh auth token`。
网络提示：`api.github.com` 通、`uploads.github.com` 可能被墙 —— 被墙时请先开代理
（设置 `HTTPS_PROXY`），或改用 `--只打包` 后网页上传。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
默认仓库 = 'YHSome/bridge-lang'
发布目录 = 项目根 / '发布'


def _令牌() -> str:
    for 名 in ('GITHUB_TOKEN', 'GH_TOKEN'):
        if os.environ.get(名):
            return os.environ[名].strip()
    try:
        结果 = subprocess.run(['gh', 'auth', 'token'], capture_output=True,
                              text=True, check=True)
        return 结果.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


def _请求(方法: str, 地址: str, 令牌: str, 体=None, 头=None):
    数据 = None
    if 体 is not None:
        数据 = 体 if isinstance(体, bytes) else json.dumps(体).encode('utf-8')
    请求 = urllib.request.Request(地址, data=数据, method=方法)
    请求.add_header('Authorization', f'Bearer {令牌}')
    请求.add_header('Accept', 'application/vnd.github+json')
    请求.add_header('X-GitHub-Api-Version', '2022-11-28')
    if 体 is not None and not isinstance(体, bytes):
        请求.add_header('Content-Type', 'application/json')
    for 键, 值 in (头 or {}).items():
        请求.add_header(键, 值)
    with urllib.request.urlopen(请求, timeout=180) as 回:
        return json.loads(回.read().decode('utf-8') or '{}')


def _打包(版本: str) -> list[tuple[Path, str]]:
    """跑三个打包脚本，返回 [(本地文件, 上传后的名字)]"""
    for 命令 in ([sys.executable, str(项目根 / '工具' / '打包.py')],
                 [sys.executable, str(项目根 / '工具' / '打包.py'), '--完整'],
                 [sys.executable, str(项目根 / '工具' / '打包VSCode插件.py')]):
        完成 = subprocess.run(命令, cwd=项目根, capture_output=True, text=True,
                             encoding='utf-8', errors='replace')
        if 完成.returncode != 0:
            print(f'打包失败：{" ".join(命令[1:])}')
            print((完成.stdout or '')[-800:])
            print((完成.stderr or '')[-800:])
            raise SystemExit(1)

    映射 = [
        (发布目录 / f'桥-{版本}.zip', f'bridge-lang-{版本}.zip'),
        (发布目录 / f'桥-{版本}-完整.zip', f'bridge-lang-{版本}-full.zip'),
        (发布目录 / f'桥语言-vscode-{版本}.vsix', f'bridge-lang-vscode-{版本}.vsix'),
    ]
    缺 = [路径.name for 路径, _ in 映射 if not 路径.is_file()]
    if 缺:
        print(f'打包完了但缺文件：{缺}')
        raise SystemExit(1)
    return 映射


def _说明(版本: str) -> str:
    """从 git log 拉"上一个 tag 之后"的提交标题，拼成 Release 说明"""
    try:
        标签们 = subprocess.run(['git', 'tag', '--list', '--sort=-creatordate'],
                              cwd=项目根, capture_output=True, text=True,
                              encoding='utf-8', errors='replace').stdout.split()
        上一个 = next((t for t in 标签们 if t != f'v{版本}'), '')
        范围 = [f'{上一个}..HEAD'] if 上一个 else ['HEAD']
        日志 = subprocess.run(['git', 'log', '--no-merges', '--pretty=%s', *范围],
                            cwd=项目根, capture_output=True, text=True,
                            encoding='utf-8', errors='replace').stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        日志 = ''
    条目 = [行.strip('﻿').strip() for 行 in 日志.splitlines() if 行.strip()][:20]
    行们 = [
        f'桥语言 v{版本}',
        '',
        '## 下载',
        '',
        '| 文件 | 用途 |',
        '| --- | --- |',
        f'| `bridge-lang-{版本}.zip` | 精简包：运行时 + 示例 + AI 文档 |',
        f'| `bridge-lang-{版本}-full.zip` | 完整包：教程/工具/自检/对照用例/docs |',
        f'| `bridge-lang-vscode-{版本}.vsix` | VS Code 插件：高亮 + 片段 |',
        '',
    ]
    if 条目:
        行们 += ['## 这次改了什么', '']
        行们 += [f'- {条}' for 条 in 条目]
        行们 += ['']
    return '\n'.join(行们)


def main(参数: list[str]) -> int:
    版本 = (项目根 / '版本.txt').read_text(encoding='utf-8').strip()
    标签 = f'v{版本}'
    if '--标签' in 参数:
        标签 = 参数[参数.index('--标签') + 1]
        版本 = 标签.lstrip('v')
    if '--仓库' in 参数:
        仓库 = 参数[参数.index('--仓库') + 1]
    else:
        仓库 = 默认仓库

    print(f'仓库：{仓库}  标签：{标签}')
    映射 = _打包(版本)
    总大小 = sum(路径.stat().st_size for 路径, _ in 映射) / 1024 / 1024
    print(f'打包完成：{len(映射)} 个文件，共 {总大小:.2f} MB')
    for 路径, 名 in 映射:
        print(f'  {路径.name}  →  {名}  ({路径.stat().st_size / 1024:.0f} KB)')

    if '--只打包' in 参数:
        print('\n（--只打包：不碰网络。要发布就设 GITHUB_TOKEN 后重跑）')
        return 0

    令牌 = _令牌()
    if not 令牌:
        print('\n没有拿到 token。两种办法：')
        print('  1) set GITHUB_TOKEN=ghp_xxx   然后重跑本脚本')
        print('  2) 打开 https://github.com/' + 仓库 + '/releases/new 手动上传 发布/ 里的文件')
        return 2

    api = f'https://api.github.com/repos/{仓库}'
    说明 = _说明(版本)
    草稿 = '--草稿' in 参数

    # 已存在就只更新说明，避免 422
    发布 = None
    try:
        发布 = _请求('GET', f'{api}/releases/tags/{标签}', 令牌)
        print(f'\nRelease 已存在（id {发布["id"]}），只更新说明')
        发布 = _请求('PATCH', f'{api}/releases/{发布["id"]}', 令牌,
                    {'body': 说明, 'name': f'桥语言 {标签}'})
    except urllib.error.HTTPError as 错误:
        if 错误.code != 404:
            raise
        print('\n建新 Release…')
        发布 = _请求('POST', f'{api}/releases', 令牌, {
            'tag_name': 标签,
            'name': f'桥语言 {标签}',
            'body': 说明,
            'draft': 草稿,
        })

    已有 = {项['name'] for 项 in 发布.get('assets', [])}
    上传地址 = 发布['upload_url'].split('{')[0]
    for 路径, 名 in 映射:
        if 名 in 已有:
            print(f'  跳过（已存在）：{名}')
            continue
        地址 = f'{上传地址}?name={urllib.parse.quote(名)}'
        try:
            _请求('POST', 地址, 令牌, 路径.read_bytes(),
                  头={'Content-Type': 'application/octet-stream'})
            print(f'  已上传：{名}')
        except urllib.error.HTTPError as 错误:
            print(f'  上传失败：{名} → HTTP {错误.code}')
            print('    （uploads.github.com 可能被墙：设 HTTPS_PROXY 或用网页上传）')
        except urllib.error.URLError as 错误:
            print(f'  上传失败：{名} → {错误.reason}')
            print('    （uploads.github.com 可能被墙：设 HTTPS_PROXY 或用网页上传）')

    print(f'\n完成：https://github.com/{仓库}/releases/tag/{标签}')
    return 0


if __name__ == '__main__':
    import urllib.parse  # noqa: PLC0415（只有上传时才用到）

    raise SystemExit(main(sys.argv[1:]))
