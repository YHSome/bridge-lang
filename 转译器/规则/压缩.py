"""压缩规则：zipfile 的中文化

    导入 压缩

    带 压缩.压缩包("备份.zip", "w") 作为 包:
        包.打包("a.txt", "a.txt")
        输出（包.列出())

    压缩.解压("备份.zip", "./解压到")
"""

模块 = {
    '压缩': 'zipfile',
}

成员 = {
    '压缩': {
        '压缩包': 'ZipFile',
        '是压缩包': 'is_zipfile',
        '解压': 'extractall',
        '解压到': 'extractall',
        '信息': 'infolist',
        '只读': 'ZIP_STORED',
        '尽量压': 'ZIP_DEFLATED',
        '坏压缩包': 'BadZipFile',
    },
}
