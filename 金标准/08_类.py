# 08 类：类 / 初始化 / 属性 / 方法 / 继承
# 对照文件：手打同名 .bridge，第 1 行起逐行对应

class 动物:
    def __init__(self, 名字, 年龄):
        self.名字 = 名字
        self.年龄 = 年龄

    def 叫声(self):
        return "……"

    def 介绍(self):
        return self.名字 + "，" + str(self.年龄) + "岁"

class 狗(动物):
    def 叫声(self):
        return "汪汪"

class 猫(动物):
    def 叫声(self):
        return "喵"

小黑 = 狗("小黑", 3)
小白 = 猫("小白", 2)
print("名字：", 小黑.名字)
print("介绍：", 小黑.介绍())
print("狗叫：", 小黑.叫声())
print("猫叫：", 小白.叫声())
print("是否实例：", isinstance(小黑, 动物))
print("类型名：", type(小黑).__name__)
