"""把 示例/ 里的 .bridge 生成一个静态展示页 docs/示例.html

    python 工具/导出示例页.py

页面只是"看代码的地方"：每个示例给标题、一句说明、前 16 行、GitHub 全文链接。
不放执行结果，不引入 JS。
"""

from __future__ import annotations

import html
import sys
import urllib.parse
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
仓库 = 'https://github.com/YHSome/bridge-lang/blob/main/'
展示上限 = 16


def _说明(文本: str) -> str:
    for 行 in 文本.splitlines():
        if 行.startswith('#'):
            说明 = 行.lstrip('#').strip()
            if 说明:
                return 说明
    return ''


def _卡片(相对: str) -> str:
    文件 = 项目根 / 相对
    try:
        文本 = 文件.read_text(encoding='utf-8-sig')
    except OSError:
        return ''
    行们 = 文本.splitlines()
    代码 = '\n'.join(行们[:展示上限])
    if len(行们) > 展示上限:
        代码 += '\n# …'
    链接 = 仓库 + urllib.parse.quote(相对.replace('\\', '/'))
    return f'''<div class="card 示例卡">
  <h3>{html.escape(文件.stem)}</h3>
  <p>{html.escape(_说明(文本)) or '桥语言示例'}</p>
<pre><code>{html.escape(代码)}</code></pre>
  <p><a href="{链接}">在 GitHub 看全文 →</a></p>
</div>'''


def main() -> int:
    示例们 = sorted((项目根 / '示例' / '特性').glob('*.bridge')) + \
        sorted((项目根 / '示例').glob('*.bridge'))
    卡片们 = '\n'.join(过滤 for 过滤 in
                     (_卡片(str(路径.relative_to(项目根))) for 路径 in 示例们) if 过滤)

    页面 = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>桥语言示例</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="nav">
  <a class="brand" href="index.html">桥语言</a>
  <nav><a href="index.html">首页</a><a href="示例.html">示例</a>
  <a href="https://github.com/YHSome/bridge-lang">GitHub</a></nav>
</header>
<main>
  <section class="hero" style="grid-template-columns:1fr;padding:48px 0 24px">
    <div>
      <span class="badge">示例 · 全部可运行</span>
      <h1>看代码，比看文档快</h1>
      <p class="lead">这些是仓库里的 <code>.bridge</code> 示例，覆盖跳转、并行、文档、JSON、表格、
      数据库、网络、调试。下载便携包后复制到项目里就能跑。</p>
      <div class="buttons">
        <a class="btn primary" href="https://github.com/YHSome/bridge-lang/releases">下载便携包</a>
        <a class="btn ghost" href="index.html">回首页</a>
      </div>
      <p class="hint">每个示例只展示前 {展示上限} 行，全文在 GitHub。</p>
    </div>
  </section>
  <section class="section">
    <h2>全部示例</h2>
    <div class="grid three">
{卡片们}
    </div>
  </section>
</main>
<footer>桥语言 Bridge Language · MIT · 用中文写 Python</footer>
</body>
</html>
'''
    出 = 项目根 / 'docs' / '示例.html'
    出.write_text(页面, encoding='utf-8')
    print(f'已生成 {出}（{len(示例们)} 个示例）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
