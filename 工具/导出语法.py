import json
import pathlib
import sys

sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from 转译器.规则加载 import 载入规则

规 = 载入规则()
目录 = pathlib.Path('vscode-桥语言')
(目录 / 'syntaxes').mkdir(parents=True, exist_ok=True)

关键字 = sorted(set(规.get('关键字') or {}) | set(规.get('内建') or {}) |
                set(规.get('异常') or {}))
模块 = sorted(set(规.get('模块') or {}))
方法 = sorted(set(规.get('方法') or {}))


def 词表模式(词们):
    return '|'.join(sorted((w.replace('\\', '\\\\') for w in 词们), key=len, reverse=True))


语法 = {
    '$schema': 'https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json',
    'name': '桥语言',
    'scopeName': 'source.bridge',
    'patterns': [
        {'include': '#注释'},
        {'include': '#字符串'},
        {'include': '#数字'},
        {'include': '#跳转语句'},
        {'include': '#模块成员'},
        {'include': '#方法调用'},
        {'include': '#关键字'},
    ],
    'repository': {
        '注释': {'patterns': [
            {'name': 'comment.line.number-sign.bridge', 'match': '#.*$'},
            {'name': 'comment.block.documentation.bridge',
             'begin': '"""', 'end': '"""'},
        ]},
        '字符串': {'patterns': [
            {'name': 'string.quoted.single.bridge', 'match': r"'[^'\\]*(\\.[^'\\]*)*'"},
            {'name': 'string.quoted.double.bridge',
             'begin': r'[fFrRbB]?"', 'end': r'"', 'patterns': [
                 {'name': 'constant.character.escape.bridge', 'match': r'\\.'},
                 {'include': '#插值'},
             ]},
        ]},
        '插值': {'patterns': [
            {'name': 'meta.interpolation.bridge',
             'begin': r'\{', 'end': r'\}', 'patterns': [{'include': '$self'}]},
        ]},
        '数字': {'patterns': [
            {'name': 'constant.numeric.bridge',
             'match': r'\b\d+(\.\d+)?\b'},
        ]},
        '跳转语句': {'patterns': [
            {'name': 'keyword.control.goto.bridge',
             'match': r'\b(标记|标签|跳转到|跳转|label|goto)\b'},
        ]},
        '模块成员': {'patterns': [
            {'name': 'support.function.module.bridge',
             'match': r'\b(' + 词表模式(模块) + r')\.[\u3400-\u9fffA-Za-z_][\w]*'},
            {'name': 'support.module.bridge',
             'match': r'\b(' + 词表模式(模块) + r')\b'},
        ]},
        '方法调用': {'patterns': [
            {'name': 'entity.name.function.method.bridge',
             'match': r'\.([\u3400-\u9fff]+)\s*\('},
            {'name': 'variable.other.member.bridge',
             'match': r'\.([\u3400-\u9fffA-Za-z_][\w]*)'},
        ]},
        '关键字': {'patterns': [
            {'name': 'keyword.control.bridge', 'match': r'\b(' + 词表模式(关键字) + r')\b'},
            {'name': 'constant.language.bridge', 'match': r'\b(真|假|空|True|False|None)\b'},
            {'name': 'entity.name.function.bridge',
             'match': r'\b(定义|函数|类)\s+([\u3400-\u9fffA-Za-z_][\w]*)',
             'captures': {'2': {'name': 'entity.name.function.bridge'}}},
        ]},
    },
}

输出 = 目录 / 'syntaxes' / 'bridge.tmLanguage.json'
输出.write_text(json.dumps(语法, ensure_ascii=False, indent=2), encoding='utf-8')
print('语法文件：', 输出, '关键字', len(关键字), '模块', len(模块), '方法', len(方法))
