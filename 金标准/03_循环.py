# 03 循环：对于 / 在 / 范围 / 当 / 中断 / 继续
# 对照文件：手打同名 .bridge，第 1 行起逐行对应

合计 = 0
for i in range(1, 6):
    合计 = 合计 + i
print("1到5之和：", 合计)

for 名称 in ["甲", "乙", "丙"]:
    print("名字：", 名称)

计数 = 0
while 计数 < 5:
    计数 = 计数 + 1
    if 计数 == 3:
        continue
    print("计数：", 计数)

for i in range(10):
    if i == 4:
        break
    print("直到四：", i)

for 序号, 名称 in enumerate(["甲", "乙"]):
    print("枚举：", 序号, 名称)
