"""报错规则：把 Python 的英文报错翻译成中文

两张表：

- `异常名`：异常类名 → 中文（和 `标准库.py` 的 `异常` 表方向相反，那张表是"中文→英文"）
- `消息`：常见报错消息的**句式替换**（正则 → 中文模板，`{0}` `{1}` 用捕获组填）

刻意**不做全量翻译**：翻译错的报错比英文原报错更坑人。策略是
"能翻的翻成人话，翻不了的保留英文原文并附上中文异常名"，这样用户既能看懂，
又能把英文原文丢给搜索引擎/AI 查。
"""

异常名 = {
    'BaseException': '基础异常',
    'Exception': '异常',
    'NameError': '名字错误',
    'UnboundLocalError': '局部变量未赋值',
    'ValueError': '值错误',
    'TypeError': '类型错误',
    'IndexError': '索引错误',
    'KeyError': '键错误',
    'AttributeError': '属性错误',
    'ZeroDivisionError': '除零错误',
    'FileNotFoundError': '文件没找到',
    'IsADirectoryError': '目标是个目录',
    'PermissionError': '权限不足',
    'AssertionError': '断言失败',
    'ImportError': '导入失败',
    'ModuleNotFoundError': '模块没找到',
    'RecursionError': '递归太深',
    'MemoryError': '内存不足',
    'OverflowError': '数值溢出',
    'StopIteration': '迭代已结束',
    'KeyboardInterrupt': '用户中断',
    'SyntaxError': '语法错误',
    'IndentationError': '缩进错误',
    'TabError': '缩进里混了制表符',
    'TimeoutError': '超时',
    'RuntimeError': '运行期错误',
    'NotImplementedError': '这个功能还没实现',
    'FileExistsError': '文件已存在',
    'EOFError': '输入提前结束',
}

# (正则, 中文模板)；模板里的 {1} {2} 是捕获组，{0} 是整段匹配
消息 = [
    (r"name '(.+?)' is not defined", '名字 “{1}” 没有定义（是不是拼错了，或者忘了赋值？）'),
    (r"name '(.+?)' is not defined\. Did you mean: '(.+?)'\?", '名字 “{1}” 没有定义，是不是想写 “{2}”？'),
    (r"division by zero", '除数不能是 0'),
    (r"integer division or modulo by zero", '整数除法/取余的除数不能是 0'),
    (r"list index out of range", '列表下标越界（这个列表没那么长）'),
    (r"tuple index out of range", '元组下标越界'),
    (r"string index out of range", '字符串下标越界'),
    (r"index out of range", '下标越界'),
    (r"'(.+?)' object is not subscriptable", '“{1}” 不能用下标取值（它不是列表/字典/字符串）'),
    (r"'(.+?)' object is not callable", '“{1}” 不能当函数调用（是不是多写了括号？）'),
    (r"'(.+?)' object has no attribute '(.+?)'", '“{1}” 没有属性或方法 “{2}”')
    ,
    (r"'(.+?)' object is not iterable", '“{1}” 不能被遍历（不是列表/字典这类东西）'),
    (r"unsupported operand type\(s\) for (.+?): '(.+?)' and '(.+?)'",
     '“{2}” 和 “{3}” 不能直接做 {1} 运算（要不要先转类型？）'),
    (r"can only concatenate str \(not \"(.+?)\"\) to str", '字符串只能和字符串相加（不能直接和 {1} 相加）'),
    (r"object of type '(.+?)' has no len\(\)", '“{1}” 没有长度（不能用 长度()/len()）'),
    (r"can't multiply sequence by non-int of type '(.+?)'", '序列只能乘整数（不能乘 {1}）'),
    (r"invalid literal for int\(\) with base 10: '(.+?)'", '“{1}” 不是合法整数'),
    (r"could not convert string to float: '(.+?)'", '“{1}” 不是合法小数'),
    (r"expected (.+?), got (.+?)", '这里应该是 {1}，实际是 {2}'),
    (r"missing (\d+) required positional argument: '(.+?)'", '少传了参数 “{2}”（差 {1} 个）'),
    (r"takes (\d+) positional argument", '参数个数不对'),
    (r"unexpected keyword argument '(.+?)'", '多了一个不认识的参数 “{1}”'),
    (r"not enough values to unpack \(expected (\d+), got (\d+)\)",
     '解包数量不对：左边要 {1} 个，右边只给了 {2} 个'),
    (r"too many values to unpack \(expected (\d+)\)", '解包数量不对：右边给多了（左边只要 {1} 个）'),
    (r"string indices must be integers", '字符串的下标必须是整数'),
    (r"indentation error: (.+)", '缩进不对：{1}'),
    (r"unexpected indent", '多缩进了'),
    (r"expected an indented block", '这里应该缩进（大括号不用写，冒号后面缩进就是块）'),
    (r"unindent does not match any outer indentation level", '缩进层级对不上'),
    (r"invalid syntax", '这行语法不对'),
    (r"unterminated string literal", '字符串没闭合（少了一个引号？）'),
    (r"unmatched '(.+?)'", '括号/引号没配对：“{1}”'),
    (r"cannot access local variable '(.+?)' where it is not associated with a value",
     '局部变量 “{1}” 还没赋值就被用了'),
    (r"maximum recursion depth exceeded", '递归太深了（检查一下是不是忘了写终止条件）'),
    (r"\[Errno 2\] No such file or directory: '(.+?)'", '找不到文件：“{1}”'),
    (r"\[Errno 13\] Permission denied: '(.+?)'", '没有权限访问：“{1}”'),
    (r"\[Errno 22\] Invalid argument: '(.+?)'", '路径不合法：“{1}”'),
    (r"module '(.+?)' has no attribute '(.+?)'", '模块 “{1}” 里没有 “{2}”'),
    (r"No module named '(.+?)'", '没有这个模块：“{1}”（先 导入 或装一下？）'),
]
