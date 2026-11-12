"""日志规则：logging 的中文化（只翻常用入口，格式串仍是英文）

    导入 日志

    日志.基础配置(级别=日志.信息级别, 格式="%(levelname)s %(message)s")
    日志.记录信息("程序启动")
"""

模块 = {
    '日志': 'logging',
}

成员 = {
    '日志': {
        '基础配置': 'basicConfig',
        '取记录器': 'getLogger',
        '记录调试': 'debug',
        '记录信息': 'info',
        '记录警告': 'warning',
        '记录错误': 'error',
        '记录严重': 'critical',
        '异常日志': 'exception',
        '调试级别': 'DEBUG',
        '信息级别': 'INFO',
        '警告级别': 'WARNING',
        '错误级别': 'ERROR',
    },
}
