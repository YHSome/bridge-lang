# 09 模块：导入 / 从 / 作为 / 模块成员翻译
# 对照文件：手打同名 .bridge，第 1 行起逐行对应

import math
import random

print("圆周率：", math.pi)
print("开方：", math.sqrt(16))
print("2的10次方：", math.pow(2, 10))
print("最大公约数：", math.gcd(12, 18))
print("向上取整：", math.ceil(3.2))

random.seed(42)
print("随机整数：", random.randint(1, 6))
print("选择：", random.choice(["甲", "乙", "丙"]))

from math import floor
print("向下取整：", floor(3.9))

from math import sqrt as 开方
print("开方(别名)：", 开方(81))
