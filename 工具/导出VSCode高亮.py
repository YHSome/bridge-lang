"""从规则表生成 VS Code 插件的高亮 / 代码片段 / 语言配置

    python 工具/导出VSCode高亮.py           # 重新生成（改了规则就跑它）
    python 工具/导出VSCode高亮.py --检查     # 只比对，不一致就 exit 1（自检/CI 用）

规则变了重跑一次：关键字、内建、异常、模块、方法、句式糖全部从 `转译器/规则/` 读，
不在插件里手写第二份词表（避免"高亮和转译打架"）。

2026-11 修的两个坑：

1. **句式糖高亮原来是死代码**：`_分组(糖)` 拿到的 `糖` 是 `(正则, 模板)` 元组，
   `str(元组)` 再 `re.escape` → 生成出来的规则匹配的是"语法糖.py 的源码文本"，
   用户的代码永远命中不了。现在改成从每条糖的正则里**推导锚点词**（去掉 `?P<组名>`
   和已在词表里的词），这样 `交换 / 加到 / 不换行 / 每个` 这些才会亮。
2. **片段是一份手抄字典**，加语法就得手工补。现在从 `转译器/帮助.py` 的 `手写` 表生成
   （「语法」直接变成模板），帮助表改了片段自动跟着变。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
插件根 = 项目根 / 'vscode-桥语言'
语法路径 = 插件根 / 'syntaxes' / 'bridge.tmLanguage.json'
片段路径 = 插件根 / 'snippets' / 'bridge.code-snippets'
配置路径 = 插件根 / 'language-configuration.json'

# 中文也算"词字符"：中文词后面紧跟中文时不能误判边界
边界左 = '(?<![A-Za-z0-9_一-鿿])'
边界右 = '(?![A-Za-z0-9_一-鿿])'

运算符值 = {'==', '!=', '>', '<', '>=', '<=', 'and', 'or', 'not', 'in',
        'is', '//', '%', '**', ':=', '&', '|', '^', '~', '<<', '>>',
        '+', '-', '*', '/'}

汉字 = re.compile(r'[\u3400-\u9fff]+')

# 帮助表里没有、但写代码时想有模板的几条（句式糖本身没有"词条"）
_补充片段 = {
    '导入': ['导入 ${1:模块}'],
    '标记': ['标记 ${1:名字}'],
    '跳转到': ['跳转到 ${1:名字}'],
}


def _分组(词们, 前缀='(?:', 后缀=')') -> str:
    排序 = sorted({str(w) for w in 词们 if str(w).strip()}, key=lambda w: (-len(w), w))
    return 前缀 + '|'.join(re.escape(w) for w in 排序) + 后缀


def _载入():
    sys.path.insert(0, str(项目根))
    from 转译器.规则加载 import 载入规则

    return 载入规则()


def 糖锚点(规则: dict) -> list[str]:
    """从语法糖的正则里推导"用户真正会写、但词表里没有"的锚点词"""
    糖们 = 规则['语法糖']
    组名 = set()
    for 模式, _模板 in 糖们:
        组名 |= set(re.findall(r'\?P<(\w+)>', 模式))
    已在 = set()
    for 表名 in ('关键字', '内建', '异常', '方法', '模块'):
        已在 |= set(规则[表名])
    for 表 in (规则['成员'] or {}).values():
        已在 |= set(表)
    锚点 = set()
    for 模式, _模板 in 糖们:
        for 片段 in 汉字.findall(模式):
            if len(片段) < 2 or 片段 in 组名 or 片段 in 已在:
                continue
            锚点.add(片段)
    return sorted(锚点)


def 生成语法(规则: dict) -> dict:
    关键字 = 规则['关键字']
    运算词 = [k for k, v in 关键字.items() if v in 运算符值]
    控制词 = [k for k, v in 关键字.items() if v not in 运算符值]
    内建 = list(规则['内建'])
    异常 = list(规则['异常'])
    模块 = list(规则['模块'])
    方法 = list(规则['方法'])
    锚点 = 糖锚点(规则)
    成员规则 = []
    for 模块名, 表 in (规则['成员'] or {}).items():
        if not 表:
            continue
        成员规则.append({
            'match': f'({re.escape(模块名)})\\s*\\.\\s*({_分组(表.keys())}){边界右}',
            'captures': {
                '1': {'name': 'support.class.module.bridge'},
                '2': {'name': 'entity.name.function.member.bridge'},
            },
        })

    return {
        '$schema': 'https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json',
        'name': '桥语言',
        'scopeName': 'source.bridge',
        'patterns': [
            {'include': '#注释'},
            {'include': '#字符串'},
            {'include': '#数字'},
            {'include': '#定义名'},
            {'include': '#模块成员'},
            {'include': '#方法调用'},
            {'include': '#句式糖'},
            {'include': '#异常'},
            {'include': '#内建'},
            {'include': '#运算符词'},
            {'include': '#关键字'},
            {'include': '#全角标点'},
        ],
        'repository': {
            '注释': {
                'patterns': [
                    {'name': 'comment.line.number-sign.bridge', 'match': '#.*$'},
                    {'name': 'comment.block.documentation.bridge',
                     'begin': r'[rRuUbBfF]*"""', 'end': '"""'},
                    {'name': 'comment.block.documentation.bridge',
                     'begin': r"[rRuUbBfF]*'''", 'end': "'''"},
                ],
            },
            '字符串': {
                'patterns': [
                    {'name': 'string.quoted.triple.bridge',
                     'begin': r'[rRuUbBfF]*"""', 'end': '"""',
                     'patterns': [{'name': 'constant.character.escape.bridge',
                                   'match': r'\\.'}]},
                    {'name': 'string.quoted.triple.bridge',
                     'begin': r"[rRuUbBfF]*'''", 'end': "'''",
                     'patterns': [{'name': 'constant.character.escape.bridge',
                                   'match': r'\\.'}]},
                    {'name': 'string.quoted.double.bridge',
                     'begin': r'[rRuUbBfF]*"', 'end': '"',
                     'patterns': [{'name': 'constant.character.escape.bridge',
                                   'match': r'\\.'}]},
                    {'name': 'string.quoted.single.bridge',
                     'begin': r"[rRuUbBfF]*'", 'end': "'",
                     'patterns': [{'name': 'constant.character.escape.bridge',
                                   'match': r'\\.'}]},
                ],
            },
            '数字': {
                'patterns': [{
                    'name': 'constant.numeric.bridge',
                    'match': r'\b(?:0[xX][0-9a-fA-F]+|0[bB][01]+|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?j?)\b',
                }],
            },
            '定义名': {
                'patterns': [{
                    'match': r'(定义|类|def|class)\s+([^\s(（:：]+)',
                    'captures': {
                        '1': {'name': 'storage.type.function.bridge'},
                        '2': {'name': 'entity.name.function.bridge'},
                    },
                }],
            },
            '模块成员': {'patterns': 成员规则},
            '方法调用': {
                'patterns': [{
                    'match': rf'(\.)\s*({_分组(方法)}){边界右}',
                    'captures': {
                        '1': {'name': 'punctuation.separator.method.bridge'},
                        '2': {'name': 'entity.name.function.method.bridge'},
                    },
                }],
            },
            '句式糖': {
                'patterns': [{
                    'name': 'keyword.operator.sugar.bridge',
                    'match': f'{边界左}{_分组(锚点)}{边界右}',
                }],
            },
            '异常': {
                'patterns': [{
                    'name': 'support.class.exception.bridge',
                    'match': f'{边界左}{_分组(异常)}{边界右}',
                }],
            },
            '内建': {
                'patterns': [{
                    'name': 'support.function.builtin.bridge',
                    'match': f'{边界左}{_分组(内建)}{边界右}',
                }],
            },
            '运算符词': {
                'patterns': [{
                    'name': 'keyword.operator.word.bridge',
                    'match': f'{边界左}{_分组(运算词)}{边界右}',
                }],
            },
            '关键字': {
                'patterns': [{
                    'name': 'keyword.control.bridge',
                    'match': f'{边界左}{_分组(控制词)}{边界右}',
                }],
            },
            '全角标点': {
                'patterns': [{
                    'name': 'punctuation.bridge',
                    'match': r'[，。：；（）【】「」『』]',
                }],
            },
        },
    }


def _转义(行: str) -> str:
    """VSCode 片段里 $ 和 } 有特殊含义"""
    return 行.replace('\\', r'\\').replace('$', r'\$').replace('}', r'\}')


def 生成片段() -> dict:
    from 转译器.帮助 import 手写

    片段: dict[str, dict] = {}
    for 词, 手 in 手写.items():
        语法 = [行 for 行 in (手.get('语法') or []) if 行.strip()]
        if not 语法:
            continue
        片段[词] = {
            'prefix': 词,
            'body': [_转义(行) for 行 in 语法[:3]],
            'description': 手['作用'],
        }
    for 词, 体 in _补充片段.items():
        片段.setdefault(词, {'prefix': 词, 'body': [_转义(行) for 行 in 体],
                          'description': 词})
    return 片段


def 生成配置() -> dict:
    return {
        'comments': {'lineComment': '#'},
        'brackets': [['（', '）'], ['[', ']'], ['{', '}'], ['(', ')']],
        'autoClosingPairs': [
            {'open': '（', 'close': '）'}, {'open': '(', 'close': ')'},
            {'open': '[', 'close': ']'}, {'open': '{', 'close': '}'},
            {'open': '"', 'close': '"'}, {'open': "'", 'close': "'"},
        ],
        'surroundingPairs': [['（', '）'], ['(', ')'], ['[', ']'], ['{', '}']],
        'indentationRules': {
            'increaseIndentPattern':
                r'^\s*(如果|否则如果|否则|对于|当|定义|类|尝试执行|捕获|配对|情形).*[:：]\s*(#.*)?$',
            'decreaseIndentPattern': r'^\s*(否则|否则如果|捕获|情形)\b',
        },
    }


def _写到(路径: Path, 内容: dict) -> str:
    return json.dumps(内容, ensure_ascii=False, indent=2) + '\n'


def _比对(路径: Path, 新文本: str) -> bool:
    if not 路径.is_file():
        print(f'缺文件：{路径.relative_to(项目根)}')
        return False
    if 路径.read_text(encoding='utf-8') == 新文本:
        return True
    print(f'过期：{路径.relative_to(项目根)}（跑 python 工具/导出VSCode高亮.py）')
    return False


def 检查() -> tuple[bool, list[str]]:
    """给自检/CI 用：返回 (是否同步, 说明)"""
    规则 = _载入()
    语法 = 生成语法(规则)
    问题: list[str] = []

    # 生成的正则必须都能编译，否则插件会整片失效
    for 键, 条目 in 语法['repository'].items():
        for 模式 in 条目['patterns']:
            串 = 模式.get('match')
            if 串:
                try:
                    re.compile(串)
                except re.error as 错误:
                    问题.append(f'repository.{键} 正则编译不过：{错误}')

    好 = _比对(语法路径, _写到(语法路径, 语法))
    好 = _比对(片段路径, _写到(片段路径, 生成片段())) and 好
    好 = _比对(配置路径, _写到(配置路径, 生成配置())) and 好
    return 好 and not 问题, 问题


def main(参数: list[str]) -> int:
    规则 = _载入()
    if '--检查' in 参数:
        好, 问题 = 检查()
        for 条 in 问题:
            print(条)
        print('VS Code 插件与规则同步（语法 / 片段 / 语言配置）' if 好 else '插件与规则不同步')
        return 0 if 好 else 1

    语法 = 生成语法(规则)
    语法路径.parent.mkdir(parents=True, exist_ok=True)
    片段路径.parent.mkdir(parents=True, exist_ok=True)
    语法路径.write_text(_写到(语法路径, 语法), encoding='utf-8', newline='\n')
    片段路径.write_text(_写到(片段路径, 生成片段()), encoding='utf-8', newline='\n')
    配置路径.write_text(_写到(配置路径, 生成配置()), encoding='utf-8', newline='\n')

    # 版本号跟 版本.txt 走；顺手保证 snippets 挂上了
    版本 = (项目根 / '版本.txt').read_text(encoding='utf-8').strip() or '0.3.0'
    package = json.loads((插件根 / 'package.json').read_text(encoding='utf-8-sig'))
    package['version'] = 版本
    包含 = package['contributes'].setdefault('snippets', [])
    路径 = './snippets/bridge.code-snippets'
    if not any(项.get('path') == 路径 for 项 in 包含):
        包含.append({'language': 'bridge', 'path': 路径})
    (插件根 / 'package.json').write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8', newline='\n')

    print(f"语法：关键字 {len(规则['关键字'])} / 内建 {len(规则['内建'])} / "
          f"异常 {len(规则['异常'])} / 模块成员 {len(规则['成员'])} 组 / "
          f"方法 {len(规则['方法'])} / 句式糖锚点 {len(糖锚点(规则))}")
    print(f'片段：{len(生成片段())} 条')
    print(f'已生成 {插件根}（版本 {版本}）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
