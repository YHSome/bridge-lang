"""通过 GitHub API 把本地提交推上去（github.com:443 被墙，但 api.github.com 通）

    python 工具/上架GitHub.py [--仓库 YHSome/bridge-lang]

做法：Git Data API —— 为每个文件建 blob → 建 tree → 建 commit → 更新 refs/heads/main。
文件清单以 `git ls-files` 为准（.gitignore 已经把实验/压测/构建产物排掉了）；
远端有、本地没有的文件会**自动从 tree 里删掉**（sha=None），所以撤文件也能用它。
"""

from __future__ import annotations

import base64
import concurrent.futures
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
默认仓库 = 'YHSome/bridge-lang'


def _token() -> str:
    return subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True,
                          check=True).stdout.strip()


class 接口:
    def __init__(self, 仓库: str, 令牌: str) -> None:
        self.仓库 = 仓库
        self.令牌 = 令牌

    def 调用(self, 方法: str, 路径: str, 体: dict | None = None):
        地址 = f'https://api.github.com/repos/{self.仓库}{路径}'
        data = json.dumps(体).encode('utf-8') if 体 is not None else None
        请求 = urllib.request.Request(地址, data=data, method=方法)
        请求.add_header('Authorization', f'Bearer {self.令牌}')
        请求.add_header('Accept', 'application/vnd.github+json')
        请求.add_header('X-GitHub-Api-Version', '2022-11-28')
        if data:
            请求.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(请求, timeout=90) as 回:
            return json.loads(回.read().decode('utf-8') or '{}')


def main(参数: list[str]) -> int:
    仓库 = 默认仓库
    if '--仓库' in 参数:
        仓库 = 参数[参数.index('--仓库') + 1]

    令牌 = _token()
    接口对象 = 接口(仓库, 令牌)
    文件们 = subprocess.run(['git', 'ls-files', '-z'], cwd=项目根,
                           capture_output=True, check=True).stdout.split(b'\0')
    路径们 = [p.decode('utf-8') for p in 文件们 if p]

    def 建blob(相对: str):
        文件 = 项目根 / 相对
        内容 = base64.b64encode(文件.read_bytes()).decode('ascii')
        return 接口对象.调用('POST', '/git/blobs', {'content': 内容, 'encoding': 'base64'})['sha']

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as 池:
        摘要们 = list(池.map(建blob, 路径们))

    树项 = [{'path': 相对, 'mode': '100644', 'type': 'blob', 'sha': 摘要}
            for 相对, 摘要 in zip(路径们, 摘要们)]

    # 是否已有 main
    try:
        引用 = 接口对象.调用('GET', '/git/ref/heads/main')
        父 = 引用['object']['sha']
        旧提交 = 接口对象.调用('GET', f'/git/commits/{父}')
        基树 = 旧提交['tree']['sha']
        远端 = 接口对象.调用('GET', f'/git/trees/{基树}?recursive=1')['tree']
        远端路径 = {项['path'] for 项 in 远端 if 项['type'] == 'blob'}
        本地路径 = set(路径们)
        删除 = sorted(远端路径 - 本地路径)
        for 路径 in 删除:
            树项.append({'path': 路径, 'mode': '100644', 'type': 'blob', 'sha': None})
        新树 = 接口对象.调用('POST', '/git/trees',
                           {'base_tree': 基树, 'tree': 树项})['sha']
        父们 = [父]
        if 删除:
            print(f'删除远端多余文件 {len(删除)} 个：')
            for 路径 in 删除[:10]:
                print('  -', 路径)
    except urllib.error.HTTPError as 错误:
        if 错误.code != 404:
            raise
        新树 = 接口对象.调用('POST', '/git/trees', {'tree': 树项})['sha']
        父们 = []

    提交 = 接口对象.调用('POST', '/git/commits', {
        'message': subprocess.run(['git', 'log', '-1', '--pretty=%s'], cwd=项目根,
                                  capture_output=True, text=True, encoding='utf-8',
                                  errors='replace').stdout.strip() or '更新',
        'tree': 新树,
        'parents': 父们,
    })

    if 父们:
        接口对象.调用('PATCH', '/git/refs/heads/main', {'sha': 提交['sha']})
    else:
        try:
            接口对象.调用('POST', '/git/refs', {'ref': 'refs/heads/main', 'sha': 提交['sha']})
        except urllib.error.HTTPError as 错误:
            if 错误.code == 422:
                接口对象.调用('PATCH', '/git/refs/heads/main', {'sha': 提交['sha']})
            else:
                raise

    print(f'已推送 {len(路径们)} 个文件')
    print(f'提交：{提交["sha"]}')
    print(f'仓库：https://github.com/{仓库}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
