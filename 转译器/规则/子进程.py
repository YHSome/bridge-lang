"""子进程规则：subprocess 模块的中文化（只翻成员，函数名留英文）

方言写法：

    导入 子进程

    结果 = 子进程.运行(["python", "--version"], 捕获输出=真, 文本=真)
    输出（结果.返回码, 结果.标准输出）

    # 拿输出（不检查返回码）
    输出（子进程.获取输出(["cmd", "/c", "echo", "hi"], 文本=真)）

注意：`capture_output=`、`text=` 这些**关键字参数名**保持英文——那是官方文档的名字。
"""

模块 = {
    '子进程': 'subprocess',
}

成员 = {
    '子进程': {
        '运行': 'run',
        '调用': 'call',
        '获取输出': 'check_output',
        '检查调用': 'check_call',
        '管道': 'PIPE',
        '标准输出': 'STDOUT',
        '空设备': 'DEVNULL',
        '超时错误': 'TimeoutExpired',
        '完成进程': 'CompletedProcess',
    },
}
