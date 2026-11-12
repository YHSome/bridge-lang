# 07 异常：尝试 / 捕获 / 最终 / 抛出 / 异常类型
# 对照文件：手打同名 .bridge，第 1 行起逐行对应

def 相除(被除数, 除数):
    return 被除数 / 除数

try:
    print("结果：", 相除(10, 0))
except ZeroDivisionError:
    print("捕获：除零错误")

def 检查年龄(年龄):
    if 年龄 < 0:
        raise ValueError("年龄不能为负")
    return 年龄

try:
    检查年龄(-1)
except ValueError as 错误:
    print("捕获值错误：", 错误)
finally:
    print("最终：无论如何都执行")

try:
    未定义变量
except NameError:
    print("捕获：名称错误")
