"""把 vscode-桥语言/ 打成可安装的 .vsix（不需要 npm/vsce）

    python 工具/打包VSCode插件.py

VSIX 本质是个 zip：`extension/` 下放插件文件，根目录放 vsixmanifest 和内容类型表。
生成到 `发布/桥语言-vscode-<版本>.vsix`。
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
插件根 = 项目根 / 'vscode-桥语言'
发布 = 项目根 / '发布'

跳过 = {'.vscodeignore', 'node_modules', '.git'}
跳过后缀 = {'.vsix', '.map'}

内容类型 = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="js" ContentType="application/javascript"/>
  <Default Extension="md" ContentType="text/markdown"/>
  <Default Extension="code-snippets" ContentType="application/json"/>
  <Default Extension="vsixmanifest" ContentType="text/xml"/>
</Types>
'''


def 清单(版本: str, 发布者: str, 标识: str) -> str:
    return f'''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{标识}" Version="{版本}" Publisher="{发布者}"/>
    <DisplayName>桥语言</DisplayName>
    <Description xml:space="preserve">桥语言（.bridge）：中文 Python 的语法高亮、代码片段与运行/调试</Description>
    <Categories>Programming Languages</Categories>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.Changelog" Path="extension/CHANGELOG.md" Addressable="true"/>
  </Assets>
</PackageManifest>
'''


def main() -> int:
    包 = json.loads((插件根 / 'package.json').read_text(encoding='utf-8-sig'))
    版本 = 包['version']
    标识 = 包['name']
    发布者 = 包.get('publisher', 'bridge-lang')
    发布.mkdir(exist_ok=True)
    出 = 发布 / f'桥语言-vscode-{版本}.vsix'

    文件们 = []
    for 文件 in 插件根.rglob('*'):
        if not 文件.is_file():
            continue
        相对 = 文件.relative_to(插件根)
        if any(部分 in 跳过 for 部分 in 相对.parts):
            continue
        if 文件.suffix in 跳过后缀:
            continue
        文件们.append((文件, 相对.as_posix()))

    with zipfile.ZipFile(出, 'w', zipfile.ZIP_DEFLATED) as 包文件:
        def 写(名字: str, 内容: bytes):
            信息 = zipfile.ZipInfo(名字, date_time=(2020, 1, 1, 0, 0, 0))
            信息.compress_type = zipfile.ZIP_DEFLATED
            包文件.writestr(信息, 内容)

        写('extension.vsixmanifest', 清单(版本, 发布者, 标识).encode('utf-8'))
        写('[Content_Types].xml', 内容类型.encode('utf-8'))
        for 文件, 相对 in sorted(文件们, key=lambda 对: 对[1]):
            写(f'extension/{相对}', 文件.read_bytes())

    print(f'插件包：{出}')
    print(f'大小：{出.stat().st_size / 1024:.1f} KB / {len(文件们) + 2} 个文件')
    print(f'安装：code --install-extension "{出}"')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
