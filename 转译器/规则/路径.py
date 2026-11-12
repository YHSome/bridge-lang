"""路径 / 系统规则：os.path 与 os 的中文化

方言写法：

    导入 路径
    打印（路径.拼接("数据", "oj.db")）
    如果 路径.存在("数据"):
        打印（"在"）

    导入 系统
    系统.创建目录("数据/临时", 存在就算=真)
    打印（系统.当前目录()）

`os.makedirs(..., exist_ok=True)` 的关键字参数保持英文——桥语言翻译的是**函数名/属性名**，
不是关键字参数名（那样会把标准库 API 文档全部打乱，用户查文档时对不上）。
"""

模块 = {
    '路径': 'os.path',
    '系统': 'os',
}

成员 = {
    '路径': {
        '拼接': 'join',
        '存在': 'exists',
        '是文件': 'isfile',
        '是目录': 'isdir',
        '是链接': 'islink',
        '取目录': 'dirname',
        '取文件名': 'basename',
        '拆分': 'split',
        '拆扩展名': 'splitext',
        '绝对路径': 'abspath',
        '真实路径': 'realpath',
        '规范化': 'normpath',
        '共通前缀': 'commonprefix',
        '是绝对': 'isabs',
        '大小': 'getsize',
        '修改时间': 'getmtime',
    },
    '系统': {
        '环境': 'environ',
        '取环境': 'getenv',
        '当前目录': 'getcwd',
        '切换目录': 'chdir',
        '创建目录': 'makedirs',
        '建目录': 'mkdir',
        '列出目录': 'listdir',
        '扫描目录': 'scandir',
        '删除': 'remove',
        '删除目录': 'rmdir',
        '重命名': 'rename',
        '覆盖重命名': 'replace',
        '建临时文件': 'mkstemp',
        '系统名': 'name',
        '分隔符': 'sep',
        '换行符': 'linesep',
        '执行命令': 'system',
        '取进程号': 'getpid',
    },
}
