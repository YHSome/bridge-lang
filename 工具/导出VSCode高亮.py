"""从规则表生成 VS Code 插件的高亮 / 代码片段 / 语言配置

    python 工具/导出VSCode高亮.py

规则变了重跑一次：关键字、内建、异常、模块、方法、句式糖全部从 `转译器/规则/` 读，
不在插件里手写第二份词表（避免"高亮和转译打架"）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
插件根 = 项目根 / 'vscode-桥语言'

# 中文也算"词字符"：中文词后面紧跟中文时不能误判边界
边界左 = '(?<![A-Za-z0-9_一-鿿])'
边界右 = '(?![A-Za-z0-9_一-鿿])'


def _分组(词们, 前缀='(?:', 后缀=')') -> str:
    排序 = sorted({str(w) for w in 词们 if str(w).strip()}, key=len, reverse=True)
    return 前缀 + '|'.join(re.escape(w) for w in 排序) + 后缀


def _载入():
    sys.path.insert(0, str(项目根))
    from 转译器.规则加载 import 载入规则

    return 载入规则()


def 生成语法(规则: dict) -> dict:
    关键字 = 规则['关键字']
    运算符值 = {'==', '!=', '>', '<', '>=', '<=', 'and', 'or', 'not', 'in',
             'is', '//', '%', '**', ':=', '&', '|', '^', '~', '<<', '>>'}
    运算词 = [k for k, v in 关键字.items() if v in 运算符值]
    控制词 = [k for k, v in 关键字.items() if v not in 运算符值]
    内建 = list(规则['内建'])
    异常 = list(规则['异常'])
    模块 = list(规则['模块'])
    方法 = list(规则['方法'])
    糖 = list(规则['语法糖'])
    成员 = 规则['成员']

    成员模式 = []
    for 模块名 in sorted(成员, key=len, reverse=True):
        if 模块名 not in 规则['模块']:
            continue
        for 名, 词们 in 成员.items():
            pass

    成员规则 = []
    for 模块名, 表 in 成员.items():
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
                    'match': rf'(定义|类|def|class)\s+([^\s(（:：]+)',
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
                    'match': f'{边界左}{_分组(糖)}{边界右}',
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


片段 = {
    '如果': {'prefix': '如果', 'body': ['如果 ${1:条件}:', '\t$0'], 'description': '如果'},
    '否则如果': {'prefix': '否则如果', 'body': ['否则如果 ${1:条件}:', '\t$0'], 'description': '否则如果'},
    '否则': {'prefix': '否则', 'body': ['否则:', '\t$0'], 'description': '否则'},
    '对于': {'prefix': '对于', 'body': ['对于 ${1:项} 在 ${2:序列}:', '\t$0'], 'description': 'for 循环'},
    '当': {'prefix': '当', 'body': ['当 ${1:条件}:', '\t$0'], 'description': 'while 循环'},
    '定义': {'prefix': '定义', 'body': ['定义 ${1:名字}(${2:参数}):', '\t$0'], 'description': '定义函数'},
    '类': {'prefix': '类', 'body': ['类 ${1:名字}:', '\t定义 __初始化__(自己):', '\t\t$0'],
           'description': '定义类'},
    '尝试执行': {'prefix': '尝试执行', 'body': ['尝试执行:', '\t$0', '捕获 ${1:值错误} 作为 ${2:错误}:', '\t输出（${2:错误})'],
             'description': 'try / 捕获'},
    '导入': {'prefix': '导入', 'body': ['导入 ${1:模块}'], 'description': '导入模块'},
    '读取': {'prefix': '读取', 'body': ['${1:对象} = 读取("${2:路径}")'], 'description': '读取文件/JSON/CSV/数据库'},
    '标记': {'prefix': '标记', 'body': ['标记 ${1:名字}'], 'description': 'goto 标签'},
    '跳转到': {'prefix': '跳转到', 'body': ['跳转到 ${1:名字}'], 'description': 'goto 跳转'},
    '输出': {'prefix': '输出', 'body': ['输出（${1:内容}）'], 'description': '打印'},
}


def main() -> int:
    规则 = _载入()
    语法 = 生成语法(规则)
    (插件根 / 'syntaxes').mkdir(parents=True, exist_ok=True)
    (插件根 / 'snippets').mkdir(parents=True, exist_ok=True)
    (插件根 / 'syntaxes' / 'bridge.tmLanguage.json').write_text(
        json.dumps(语法, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (插件根 / 'snippets' / 'bridge.code-snippets').write_text(
        json.dumps(片段, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (插件根 / 'language-configuration.json').write_text(json.dumps({
        'comments': {'lineComment': '#'},
        'brackets': [['（', '）'], ['[', ']'], ['{', '}'], ['(', ')']],
        'autoClosingPairs': [
            {'open': '（', 'close': '）'}, {'open': '(', 'close': ')'},
            {'open': '[', 'close': ']'}, {'open': '{', 'close': '}'},
            {'open': '"', 'close': '"'}, {'open': "'", 'close': "'"},
        ],
        'surroundingPairs': [['（', '）'], ['(', ')'], ['[', ']'], ['{', '}']],
        'indentationRules': {
            'increaseIndentPattern': r'^\s*(如果|否则如果|否则|对于|当|定义|类|尝试执行|捕获|配对|情形).*[:：]\s*(#.*)?$',
            'decreaseIndentPattern': r'^\s*(否则|否则如果|捕获|情形)\b',
        },
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # 版本号跟 版本.txt 走
    版本 = (项目根 / '版本.txt').read_text(encoding='utf-8').strip() or '0.2.0'
    package = json.loads((插件根 / 'package.json').read_text(encoding='utf-8-sig'))
    package['version'] = 版本
    包含 = package['contributes'].setdefault('snippets', [])
    路径 = './snippets/bridge.code-snippets'
    if not any(项.get('path') == 路径 for 项 in 包含):
        包含.append({'language': 'bridge', 'path': 路径})
    (插件根 / 'package.json').write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(f"语法：关键字 {len(规则['关键字'])} / 内建 {len(规则['内建'])} / "
          f"异常 {len(规则['异常'])} / 模块成员 {len(规则['成员'])} 组 / 方法 {len(规则['方法'])}")
    print(f'已生成 {插件根}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
