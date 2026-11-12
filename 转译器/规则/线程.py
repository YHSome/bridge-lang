"""线程规则：threading 的中文化

    导入 线程

    件 = 线程.线程(目标=干活)
    件.启动()
    件.加入()
"""

模块 = {
    '线程': 'threading',
}

成员 = {
    '线程': {
        '线程': 'Thread',
        '当前线程': 'current_thread',
        '事件': 'Event',
        '锁': 'Lock',
        '递归锁': 'RLock',
        '条件变量': 'Condition',
        '定时器': 'Timer',
        '守护线程': 'daemon',
        '活跃数': 'active_count',
    },
}
