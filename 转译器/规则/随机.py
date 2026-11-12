"""随机规则：random 模块的中文化（第二个示范文件，用来验证规则扩展不用改主转译器）

方言写法：

    导入 随机
    随机.种子(42)
    打印（随机.随机整数(1，6)）
    打印（随机.选择(【“石头”，“剪刀”，“布”】)）

转译后：

    import random
    random.seed(42)
    print(random.randint(1,6))
    print(random.choice(["石头","剪刀","布"]))
"""

模块 = {
    '随机': 'random',
}

成员 = {
    '随机': {
        '种子': 'seed',
        '随机浮点': 'random',
        '均匀随机': 'uniform',
        '随机整数': 'randint',
        '选择': 'choice',
        '多选': 'choices',
        '样本': 'sample',
        '洗牌': 'shuffle',
        '高斯': 'gauss',
        '打乱顺序': 'shuffle',
    },
}
