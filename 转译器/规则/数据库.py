"""数据库规则：sqlite3 的中文化

常用路径其实不用它——`读取("图书.db")` 会直接给你一个数据库对象；
这里只翻"低层/异常"那部分。
"""

模块 = {
    '数据库': 'sqlite3',
}

成员 = {
    '数据库': {
        '连接': 'connect',
        '数据错误': 'DatabaseError',
        '完整性错误': 'IntegrityError',
        '操作错误': 'OperationalError',
        '行': 'Row',
    },
}
