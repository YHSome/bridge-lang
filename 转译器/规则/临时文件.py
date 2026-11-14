"""临时文件规则：tempfile 的中文化

    导入 临时文件

    带 临时文件.临时文件("w+", 后缀=".txt") 作为 件:
        件.写("草稿")
        ...
"""

模块 = {
    '临时文件': 'tempfile',
}

成员 = {
    '临时文件': {
        '临时文件': 'NamedTemporaryFile',
        '临时目录': 'TemporaryDirectory',
        '临时目录名': 'gettempdir',
        '创建临时目录': 'mkdtemp',
        '创建临时文件': 'mkstemp',
        '临时名字': 'mktemp',
        '默认目录': 'gettempdir',
    },
}
