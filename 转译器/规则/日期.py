"""日期规则：datetime / timedelta 的中文化

方言写法：

    导入 日期

    现在 = 日期.现在()
    输出（现在.格式化日期("%Y-%m-%d %H:%M")）

    借出 = 日期.解析("2026-11-01", "%Y-%m-%d")
    输出（"借了", (现在 - 借出).天数, "天")

`时间差(3)` 就是 3 天（timedelta 的第一个位置参数是 days）：

    三天后 = 现在 + 时间差(3)

注意：`日期` 映射到 datetime **模块**，成员都写成"类.方法"的形式
（`现在` → `datetime.now`），所以 `导入 日期` 仍然是一句合法的 `import datetime`。
"""

模块 = {
    '日期': 'datetime',
}

# 时间差 不是模块，是"构造表达式"：`时间差(3)` → `datetime.timedelta(3)`
# 放在标准库的 内建 表里（见 标准库.py），不需要 导入 时间差。

成员 = {
    '日期': {
        '现在': 'datetime.now',
        '今天': 'datetime.today',
        '世界时现在': 'datetime.utcnow',
        '从时间戳': 'datetime.fromtimestamp',
        '解析': 'datetime.strptime',
        '合并': 'datetime.combine',
    },
    '时间差': {},
}
