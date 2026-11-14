"""主转译器：`.bridge` 方言源码  →  标准 Python 源码  →  code 对象

管线（每一步都可单独调用、单独测试）：

    ① 分段      把源码切成 代码 / 字符串 / 注释 三类区域
    ② 归一      代码区域内的全角标点 → 半角
    ③ 成员      中文模块.中文成员 → math.pi 这种
    ④ 词替换    关键字 / 内建 / 异常 的汉字 → Python 名字
    ⑤ 组装      字符串、注释原样拼回，行号严格不变
    ⑥ 编译      compile()；严格模式失败 → 前缀回退模式 → 再失败才抛错

为什么是「字符级扫描」而不是「tokenize 改 token」：
Python 3.13 的词法器会把 `打印（` 整个吞成一个 NAME（全角括号 U+FF08 被当成
标识符续接字符），token 级方案在这种输入上根本够不到括号。字符级扫描 + 字符串
感知是唯一稳妥的路径（详见 架构.md「踩坑记录」）。
"""

from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

from . import 跳转
from .规则加载 import 载入规则

# 汉字的粗粒度区间：CJK 统一表意文字 + 扩展 A。足够覆盖规则表里的词
汉字 = re.compile(r'[\u3400-\u9fff]+')

# 中文引号包裹的字符串：扫描阶段单独成段，替换成英文双引号
中文左引号 = '“'
中文右引号 = '”'

# 转译器版本：文件里可选地写一行 `桥语言版本("0.1")` 声明要求
版本 = '0.2.0'

# 文件头允许出现的声明名（只保留版本声明；`转译器位置` 已废弃，见 架构.md 5.6）
声明名 = ('桥语言版本',)

_声明正则 = re.compile(
    r'^[ \t　]*(?P<名>' + '|'.join(声明名) + r')'
    r'[ \t]*[（(][ \t]*["“](?P<值>[^"”]*)[\"”][ \t]*[）)][ \t]*$'
)


def 解析声明(源码: str) -> tuple[str, dict[str, str]]:
    """消费文件头的可选声明：`桥语言版本("0.1")`

    规则：
    - 只认「第一条代码行之前」的声明，写在代码后面按普通代码处理；
    - 声明行被改写成注释，**行数不变**，所以行号仍然对齐；
    - 返回 (改写后的源码, {'桥语言版本': '0.1'})。

    为什么需要吃掉它：它形态上是合法的函数调用，不消费掉就会一路传进 Python，
    运行期变成 `NameError: name '桥语言版本' is not defined`。
    """
    元信息: dict[str, str] = {}
    行们 = 源码.splitlines(keepends=True)
    正文已开始 = False
    for i, 行 in enumerate(行们):
        正文 = 行.rstrip('\r\n')
        换行 = 行[len(正文):]
        纯 = 正文.strip()
        if not 纯 or 纯.startswith('#'):
            continue
        if not 正文已开始:
            匹配 = _声明正则.match(正文)
            if 匹配:
                元信息[匹配.group('名')] = 匹配.group('值')
                行们[i] = '#' + 正文 + 换行
                continue
        正文已开始 = True
        break
    return ''.join(行们), 元信息


class 方言回退警告(UserWarning):
    """严格模式失败、用前缀回退模式才编过时发出的提醒"""


class 方言错误(SyntaxError):
    """方言源码本身有语法错误（严格模式和前缀模式都编译不过）"""

    def __init__(self, 消息: str, 行号: int | None = None, 列号: int | None = None) -> None:
        super().__init__(消息)
        self.行号 = 行号
        self.lineno = 行号
        self.offset = 列号

    def __str__(self) -> str:
        # 消息里已经写了行号（比如带"可能的原因"的建议）就不要重复贴后缀
        if not self.行号 or f'第 {self.行号} 行' in self.msg:
            return self.msg
        return self.msg + f'（第 {self.行号} 行）'


# --------------------------------------------------------------------------
# ① 分段
# --------------------------------------------------------------------------
# 会打断"代码段"的字符：引号（字符串）和 # （注释）
_分段触发 = re.compile(r'["\'#“]')


def _找字符串结束(源码: str, 起: int, 引号: str) -> int:
    """从 `起` 开始找字符串的结束位置（返回结束后的下标）

    - 单位引号字符串遇到换行就断（那是没写完的字符串，Python 也这么判）；
    - 反斜杠转义要跳过，所以不能用一次 find 了事。
    """
    n = len(源码)
    j = 起
    while j < n:
        命中 = 源码.find(引号, j)
        if 命中 < 0:
            return n
        # 数一数引号前面连着几个反斜杠：奇数个=被转义，继续找
        反斜杠 = 0
        k = 命中 - 1
        while k >= 起 and 源码[k] == '\\':
            反斜杠 += 1
            k -= 1
        if 反斜杠 % 2 == 0:
            return 命中 + len(引号)
        j = 命中 + len(引号)
    return n


def 分段(源码: str) -> list[tuple[str, str]]:
    """把源码切成 [('代码'|'字符串'|'注释'|'中文引号', 文本), ...]

    字符串内容（含 f-string、三引号、转义）和注释一律不参与任何替换——
    你写的是数据，不是语法。

    实现上不做"逐字符循环"：先用正则找到下一个可能的分界符，把中间一大段一次性
    切给代码段。web.bridge 那种 100 KB 的文件，逐字符循环要跑 10 万次 Python 层
    迭代，跳着找只要几千次。
    """
    段: list[tuple[str, str]] = []
    缓冲: list[str] = []

    def 收尾() -> None:
        if 缓冲:
            段.append(('代码', ''.join(缓冲)))
            缓冲.clear()

    i, n = 0, len(源码)
    while i < n:
        触发 = _分段触发.search(源码, i)
        if 触发 is None:
            缓冲.append(源码[i:])
            break
        j = 触发.start()
        if j > i:
            缓冲.append(源码[i:j])
        c = 源码[j]

        # 注释：一直到行尾
        if c == '#':
            收尾()
            行尾 = 源码.find('\n', j)
            行尾 = n if 行尾 < 0 else 行尾
            段.append(('注释', 源码[j:行尾]))
            i = 行尾
            continue

        # 英文引号字符串：单/双/三引号
        if c in '"\'':
            引号 = c * 3 if 源码[j:j + 3] == c * 3 else c
            结束 = _找字符串结束(源码, j + len(引号), 引号)
            if len(引号) == 1:
                换行 = 源码.find('\n', j + 1)
                if 0 <= 换行 < 结束:
                    结束 = 换行
            # 前缀（f / r / b / u 组合）要算进字符串本身，否则 f-string 认不出来；
            # 但 `if"x"` 这种前面是标识符字符的不能抢，那是关键字不是前缀。
            # 注意缓冲里可能是"整段代码"而不是单字符，所以要按尾部字符判。
            已有 = ''.join(缓冲)
            取 = len(已有)
            while 取 > 0 and 已有[取 - 1] in 'fFrRbBuU':
                取 -= 1
            前缀 = 已有[取:]
            if 前缀:
                前一个 = 已有[取 - 1] if 取 > 0 else ''
                合法 = (set(前缀.lower()) <= set('frbu')
                        and 前缀.lower().count('f') <= 1)
                if (前一个 and (前一个.isalnum() or 前一个 == '_')) or not 合法:
                    前缀 = ''
                    取 = len(已有)        # 不是前缀就原样还回去（别把 if 的 i 吞了）
            缓冲.clear()
            if 取:
                缓冲.append(已有[:取])
            收尾()
            段.append(('字符串', 前缀 + 源码[j:结束]))
            i = 结束
            continue

        # 中文引号字符串：“你好” → "你好"
        if c == 中文左引号:
            右 = 源码.find(中文右引号, j + 1)
            右 = n if 右 < 0 else 右
            收尾()
            段.append(('中文引号', 源码[j:右 + 1]))
            i = 右 + 1
            continue

        # 理论上到不了这里（触发符都处理完了），保险起见按普通字符吃
        缓冲.append(c)
        i = j + 1

    收尾()
    return 段


# --------------------------------------------------------------------------
# ② 归一 / ③ 成员 / ④ 词替换（只作用在「代码」段）
# --------------------------------------------------------------------------
_成员正则 = re.compile(r'(?P<模块>[\u3400-\u9fff]+)\s*\.\s*(?P<成员>[\u3400-\u9fff]+)')


_成员正则 = re.compile(
    r'(?P<模块>[A-Za-z_][\w.]*|[\u3400-\u9fff]+)\s*\.\s*(?P<成员>[\u3400-\u9fff]+)')


def _替换成员(文本: str, 规则: dict) -> str:
    """数学.圆周率 → math.pi；json.转字符串 → json.dumps

    模块名两种写法都认：中文别名（`数学`）或真实模块名（`json` / `os.path`）——
    后者靠 `模块反查` 找到对应的成员表。没登记的成员原样保留，不弄坏用户代码。
    """
    模块表 = 规则['模块']
    成员表 = 规则['成员']
    反查 = 规则.get('模块反查') or {}

    def 回调(m: re.Match) -> str:
        模块名, 成员名 = m.group('模块'), m.group('成员')
        英文模块 = 模块表.get(模块名)
        中文模块 = 模块名 if not 英文模块 else 模块名
        表 = 成员表.get(模块名) or 成员表.get(反查.get(模块名, '')) or {}
        英文成员 = 表.get(成员名)
        if 英文成员 is None:
            if not 英文模块:
                return m.group(0)      # 既不认识的模块、也没登记成员：原样返回
            英文成员 = 成员名
        return f'{英文模块 or 模块名}.{英文成员}'

    return _成员正则.sub(回调, 文本)


_方法正则 = re.compile(r'(?<=\.)\s*(?P<名>[\u3400-\u9fff]+)')


def _替换方法(文本: str, 规则: dict) -> str:
    """点号之后的中文方法名：数据.追加 → 数据.append

    只在 `.` 之后生效，所以 `排序(数据)`（内建）和 `数据.排序()`（方法 sort）
    可以是两个不同的词，互不干扰。
    """
    表 = 规则.get('方法') or {}
    if not 表:
        return 文本

    def 回调(m: re.Match) -> str:
        名 = m.group('名')
        新 = 表.get(名)
        if not 新:
            return m.group(0)          # 没登记就整段原样返回（连点号后的空白一起保留）
        前缀 = m.group(0)[:len(m.group(0)) - len(名)]
        return 前缀 + 新

    return _方法正则.sub(回调, 文本)


def 切分(汉字串: str, 词表: dict, 长键: list[str]) -> list[str]:
    """把连续汉字串切成 [关键字/标识符, ...]（前缀回退模式用）

    `如果名字等于` → ['if', '名字', '==']
    """
    部分: list[str] = []
    i = 0
    while i < len(汉字串):
        命中 = next((k for k in 长键 if 汉字串.startswith(k, i)), None)
        if 命中:
            部分.append(词表[命中])
            i += len(命中)
        else:
            j = i + 1
            while j < len(汉字串) and not any(汉字串.startswith(k, j) for k in 长键):
                j += 1
            部分.append(汉字串[i:j])
            i = j
    return 部分


def _是值位置(文本: str, 起: int, 止: int) -> bool:
    """判断一个词是不是出现在「值位置」：赋值号右边、括号/逗号后、行尾前

    `启动 = 是`   → 前是 `=`，后是行尾 → 值位置
    `等级 是 空`  → 前是标识符       → 比较位置（is）
    """
    前 = 文本[:起].rstrip()
    后 = 文本[止:].split('\n', 1)[0].strip()   # 只看同一行剩下的部分
    前字符 = 前[-1:]
    后字符 = 后[:1]
    return 前字符 in '=(,[{' and 后字符 in ('', ')', ']', ',', '}')


def _替换词(文本: str, 规则: dict, 前缀模式: bool) -> str:
    词表 = 规则['词表']
    值位置表 = 规则.get('值位置') or {}
    长键 = 规则['长键']

    def 回调(m: re.Match) -> str:
        串 = m.group(0)
        # 点号后面是"成员/属性"位置：`配置.数据库`、`书.名字` 都不能按词表翻。
        # 但 `from . import x` 这种相对导入的点号后面**该翻**（导入 是关键字）。
        前 = 文本[:m.start()].rstrip()
        if 前.endswith('.'):
            头 = 前[:-1].rstrip()
            前词 = 头.split()[-1] if 头.split() else ''
            if not 前词.endswith(('from', '导入', 'import', '从')):
                return 串
        if 串 in 值位置表 and _是值位置(文本, m.start(), m.end()):
            return 值位置表[串]
        if 串 in 词表:                     # 全等匹配（严格模式唯一命中的情况）
            return 词表[串]
        if 前缀模式:                       # 回退：拆关键字 + 标识符
            部分 = 切分(串, 词表, 长键)
            if len(部分) > 1:
                return ' '.join(部分)
        return 串                          # 就是个普通中文标识符，放行

    return 汉字.sub(回调, 文本)


# 条件语句：只有这一族允许吃掉行尾助词（`当 x 时:` → `while x:`）
_条件关键字 = ('while', 'if', 'elif')
_助词行 = re.compile(
    r'^(?P<缩进>[ \t]*)'
    r'(?P<关键字>while|if|elif)'
    r'\s+(?P<条件>\S.*?)'
    r'\s*(?P<助词>' + '|'.join(sorted(['的时候', '的话', '时'], key=len, reverse=True)) + r')'
    r'\s*:\s*$'
)


def _去助词行(行: str, 规则: dict) -> str:
    """吃掉条件语句行尾的助词：`当 计数 < 5 时:` → `while 计数 < 5:`

    只认 while / if / elif 开头的行，且要求 `条件` 非空——这样
    `如果 时:`（把「时」当布尔变量）不会被误伤成 `if :`。
    去掉的只是语气助词，**行数不变、产物与 `当 计数 < 5:` 完全相同**。
    """
    助词表 = 规则.get('助词') or {}
    if not 助词表:
        return 行
    匹配 = _助词行.match(行)
    if 匹配 and 匹配.group('助词') in 助词表:
        return f"{匹配.group('缩进')}{匹配.group('关键字')} {匹配.group('条件').rstrip()}:"
    return 行


# 语法糖的编译缓存（正则编译一次，逐行匹配直接复用）
@functools.lru_cache(maxsize=8)
def _编译糖(糖们: tuple[tuple[str, str], ...]) -> tuple[tuple[re.Pattern, str], ...]:
    结果 = []
    for 模式串, 模板 in 糖们:
        模板换 = re.sub(r'\{(\w+)\}', r'\\g<\1>', 模板)
        结果.append((re.compile(模式串), 模板换))
    return tuple(结果)


# --------------------------------------------------------------------------
# 整行处理（语法糖 / 助词）：需要看整行，所以先把字符串和注释遮起来
# --------------------------------------------------------------------------
# 每段填充用**不同的字符**，并且按行切开：这样一个"填充块"严格对应一段原文，
# 还原时才能按顺序一一换回。（早先用单一填充字符 + 不切行，多行字符串会被
# 拆成好几个填充块，导致还原错位——实测文件里第 6 行整行内容被吞掉。）
填充池 = [chr(0xE000 + i) for i in range(240)]
注释填充池 = [chr(0xE300 + i) for i in range(240)]


def _切行(文: str) -> list[str]:
    """按行切段（保留每行自己的换行符，方便原样拼回）"""
    块: list[str] = []
    起点 = 0
    for i, c in enumerate(文):
        if c == '\n':
            块.append(文[起点:i + 1])
            起点 = i + 1
    if 起点 < len(文):
        块.append(文[起点:])
    return 块 or ['']


def _遮罩(文本: str) -> tuple[str, list[tuple[str, str]]]:
    """把字符串/注释换成填充字符（每段每行一种字符），返回 (遮罩文本, [(填充字符, 原文)…])"""
    碎片: list[str] = []
    原段: list[tuple[str, str]] = []
    编号 = 0
    注释符: set[str] = set()
    for 种类, 文 in 分段(文本):
        if 种类 == '代码':
            碎片.append(文)
            continue
        池 = 注释填充池 if 种类 == '注释' else 填充池
        for 块 in _切行(文):
            主体 = 块.rstrip('\n')
            换行 = 块[len(主体):]
            if not 主体:                      # 纯空行（多行字符串里的空行）：没有东西要还原
                碎片.append(换行)
                continue
            字符 = 池[编号 % len(池)]
            编号 += 1
            碎片.append(字符 * len(主体) + 换行)
            原段.append((字符, 主体))
            if 种类 == '注释':
                注释符.add(字符)
    return ''.join(碎片), 原段


_填充正则 = re.compile('[\uE000-\uE0EF\uE300-\uE3EF]+')


def _还原(文本: str, 原段: list[tuple[str, str]]) -> str:
    """把填充字符换回原文；按出现顺序一一对应

    用一条正则在 C 层扫，比逐字符 Python 循环快一个数量级（大文件上肉眼可见）。
    """
    序号 = 0
    总数 = len(原段)

    def 换(m: re.Match) -> str:
        nonlocal 序号
        if 序号 < 总数:
            值 = 原段[序号][1]
            序号 += 1
            return 值
        return ''

    return _填充正则.sub(换, 文本)


def _整行处理(文本: str, 逐行函数) -> str:
    """把「需要整行视野」的处理（语法糖、行尾助词）安全地套到全文

    为什么要遮罩：分段器会把 `输出 "x"` 切成 代码`输出 ` + 字符串`"x"`，
    整行规则只看得到半行就会漏匹配；但直接对原文跑整行规则又会误改字符串里的内容。

    另外还要跳过**续行**：括号没闭合的行（`x = (\n  a if b\n  else c)`）属于上一行
    表达式的一部分，对它套"整行语句规则"会把三元表达式错当成语句（实测踩过）。
    """
    遮罩文本, 原段 = _遮罩(文本)
    注释符 = {字符 for 字符, _ in 原段 if 字符 in set(注释填充池)}

    def 处理一行(行: str, 是续行: bool) -> str:
        if 是续行:
            return 行                    # 表达式中间的行：一个字都不许动
        尾 = ''
        while 行 and 行[-1] in 注释符:
            尾 = 行[-1] + 尾
            行 = 行[:-1]
        return 逐行函数(行) + 尾

    行们 = 遮罩文本.split('\n')
    出 = []
    深度 = 0
    续行 = False
    for 行 in 行们:
        出.append(处理一行(行, 续行 or 深度 > 0))
        for c in 行:
            if c in '([{':
                深度 += 1
            elif c in ')]}':
                深度 = max(0, 深度 - 1)
        续行 = 行.rstrip().endswith('\\')
    return _还原('\n'.join(出), 原段)


def _翻译代码(文本: str, 规则: dict, 前缀模式: bool = False, 已分段: bool = False) -> str:
    """翻译一段**代码**：归一 → 成员 → 方法 → 词替换

    `已分段=True` 表示调用方已经确认这截是纯代码（转译主循环里就是这样），
    可以跳过再分段。f-string 的 `{表达式}` 则必须走分段——表达式里可能带字符串字面量
    （`{x or '（空）'}`），全角归一绝不能碰它们。

    性能上这一步很关键：web.bridge 有 1600 多个代码段，如果不跳过，每段都要再跑一次
    分段器，等于把整份文件重新扫了 1600 遍。
    """
    if 已分段 or ('"' not in 文本 and "'" not in 文本):
        代码 = 文本.translate(规则['全角表'])
        if 汉字.search(代码):
            代码 = _替换成员(代码, 规则)
            代码 = _替换方法(代码, 规则)
            代码 = _替换词(代码, 规则, 前缀模式)
        return 代码

    出: list[str] = []
    for 种类, 段 in 分段(文本):
        if 种类 != '代码':
            出.append(段)
            continue
        代码 = 段.translate(规则['全角表'])
        # 快路径：这一小段里一个汉字都没有（纯英文代码），三条替换正则全都可以跳过
        if 汉字.search(代码):
            代码 = _替换成员(代码, 规则)          # 数学.圆周率 → math.pi
            代码 = _替换方法(代码, 规则)          # 数据.追加   → 数据.append
            代码 = _替换词(代码, 规则, 前缀模式)  # 如果 → if（英文关键字原样透传）
        出.append(代码)
    return ''.join(出)


# --------------------------------------------------------------------------
# ⑤ 组装
# --------------------------------------------------------------------------
def _改写模块返回(文本: str) -> str:
    """把**模块顶层**的 `return X` 改写成 `raise 桥返回(X)`

    Python 不允许模块级 return，但桥语言允许"一个程序跑完返回一个值"，
    方便 `a = 运行("a.bridge")` 拿到结果。函数体里的 return 不动（有缩进）。
    """
    出: list[str] = []
    for 行 in 文本.split('\n'):
        if 行.startswith('return') and (len(行) == 6 or 行[6] in ' \t(,:'):
            值 = 行[6:].strip() or 'None'
            出.append(f'raise 桥返回({值})')
        else:
            出.append(行)
    return '\n'.join(出)



# --------------------------------------------------------------------------
# 导入行：模块别名唯一合法出现的地方之一（另一个是点号前，走成员表）
# --------------------------------------------------------------------------
_导入行 = re.compile(r'^(?P<缩进>[ \t]*)(?P<词>导入|import)\s+(?P<体>.+?)\s*$')
_从行 = re.compile(r'^(?P<缩进>[ \t]*)(?P<词>从|from)\s+(?P<模块>[^\s]+)\s+'
                 r'(?P<词2>导入|import)\s+(?P<体>.+?)\s*$')


def _替换导入(源码: str, 规则: dict) -> str:
    """把 `导入 数学` / `从 数学 导入 开方` 翻成 import；别的行原样不动

    模块别名不再进通用词表，所以这是它唯一的"无点号"入口。
    """
    模块表 = 规则.get('模块') or {}
    成员表 = 规则.get('成员') or {}

    def 翻模块(名: str) -> str:
        return 模块表.get(名, 名)

    def 翻成员(模块: str, 名: str) -> str:
        return (成员表.get(模块) or {}).get(名, 名)

    def 处理(行: str) -> str:
        m = _从行.match(行)
        if m:
            模块 = m.group('模块')
            英文 = 翻模块(模块)
            名字们 = []
            for 段 in re.split(r'[，,]', m.group('体')):
                段 = 段.strip()
                if not 段:
                    continue
                名, _, 别名 = 段.partition(' 作为 ')
                名 = 名.strip()
                换 = 翻成员(模块, 名)
                名字们.append(f'{换} as {别名.strip()}' if 别名.strip() else 换)
            return f"{m.group('缩进')}from {英文} import {', '.join(名字们)}"
        m = _导入行.match(行)
        if m:
            段们 = []
            for 段 in re.split(r'[，,]', m.group('体')):
                段 = 段.strip()
                if not 段:
                    continue
                名, _, 别名 = 段.partition(' 作为 ')
                名 = 名.strip()
                换 = 翻模块(名)
                段们.append(f'{换} as {别名.strip()}' if 别名.strip() else 换)
            return f"{m.group('缩进')}import {', '.join(段们)}"
        return 行

    if '导入' not in 源码 and '从' not in 源码:
        return 源码
    return '\n'.join(处理(行) for 行 in 源码.split('\n'))

def 转译(源码: str, *, 规则: dict | None = None, 前缀模式: bool = False) -> str:
    """方言源码 → 标准 Python 源码（纯文本，可直接写盘成 .py）"""
    if 源码.startswith('\ufeff'):          # 兼容带 BOM 的文件
        源码 = 源码[1:]
    源码, _ = 解析声明(源码)                # 头文件声明不进产物
    规 = 规则 or 载入规则()
    全角表 = 规['全角表']

    # ⓿ 跳转：`标记` / `跳转到` 是桥语言独有的语句，先在这一层改写成状态机
    缺失 = 跳转.缺失目标(源码)
    if 缺失 is not None:
        raise 方言错误(f'该标记不存在：「{缺失}」（这个文件里没有「标记 {缺失}」）')
    try:
        源码 = 跳转.转换(源码)
    except ValueError as 错误:
        raise 方言错误(str(错误)) from None

    # ⓪ 导入行：模块别名先落地（词表里已经没有它们了）
    源码 = _替换导入(源码, 规)

    # ① 语法糖：整行重写，此时还是中文原词（字符串被遮住）
    糖们 = _编译糖(tuple(tuple(糖) for 糖 in (规.get('语法糖') or [])))

    def 套糖(行: str) -> str:
        for _ in range(3):
            改了 = False
            for 模式, 模板 in 糖们:
                if 模式.match(行):
                    新行 = 模式.sub(模板, 行, count=1)
                    if 新行 != 行:
                        行 = 新行
                        改了 = True
                    break
            if not 改了:
                break
        return 行

    _尾语句 = re.compile(r'^(?P<头>[ \t]*[^:\n]+:\s+)(?P<尾>\S.*)$')

    def 糖行(行: str) -> str:
        """先整行套糖；再对 `if x: 输出 y` 这种单行尾巴套一次

        快路径：语法糖的锚点词全是中文，行里一个汉字都没有就直接放行——
        大文件里绝大多数行都是纯英文/纯符号，省掉 13 条正则的 match。
        例外：帮助语法（`?`）的锚点是问号不是汉字，所以要单独放行它。
        """
        if not 汉字.search(行) and '?' not in 行 and '？' not in 行:
            return 行
        for _ in range(4):
            新行 = 套糖(行)
            if 新行 != 行:
                行 = 新行
                continue
            拆 = _尾语句.match(行)
            if 拆:
                新尾 = 套糖(拆.group('尾'))
                if 新尾 != 拆.group('尾'):
                    行 = 拆.group('头') + 新尾
                    continue
            break
        return 行

    # 快路径：源码里一个汉字都没有，就不可能有语法糖/助词命中（锚点词全是中文）
    # 例外：`?` / `？` 是帮助语法的锚点，纯符号行也得过一遍糖
    有汉字 = bool(汉字.search(源码)) or ('?' in 源码 or '？' in 源码)
    源码 = _整行处理(源码, 糖行) if (糖们 and 有汉字) else 源码

    # ② 逐段翻译：归一 → 成员 → 方法 → 词替换（f-string 里的表达式也要翻）
    from .f字符串 import 加工 as _加工f字符串, 是f字符串 as _是f字符串

    输出: list[str] = []
    for 种类, 文本 in 分段(源码):
        if 种类 == '代码':
            输出.append(_翻译代码(文本, 规, 前缀模式, 已分段=True))
        elif 种类 == '中文引号':
            内容 = 文本[1:-1].replace('"', '\\"')
            输出.append(f'"{内容}"')
        elif 种类 == '字符串' and _是f字符串(文本):
            # f"{长度(数据)}" → f"{len(数据)}"：只进 {表达式}，不碰格式说明符
            新字面量, _ = _加工f字符串(
                文本, lambda 表达式: _翻译代码(表达式, 规, 前缀模式))
            输出.append(新字面量)
        else:                              # 普通字符串 / 注释：原样透传
            输出.append(文本)
    结果 = ''.join(输出)

    # ③ 行尾助词：此时关键字已是英文，整行处理；没有语气词就整段跳过
    if any(词 in 结果 for 词 in ('时', '的话')):
        结果 = _整行处理(结果, lambda 行: _去助词行(行, 规))
    # ④ 模块级 `返回 X` → `raise 桥返回(X)`，由 桥运行 接住
    return _改写模块返回(结果)


# --------------------------------------------------------------------------
# ⑥ 编译 / 运行
# --------------------------------------------------------------------------
def 编译(源码: str, 文件名: str = '<桥>', *, 规则: dict | None = None):
    """转译 + compile；严格模式失败自动回退前缀模式。

    返回 (code, 转译后的源码)。行号与方言源码一致，traceback 可直接对照。
    """
    规 = 规则 or 载入规则()
    if 源码.startswith('\ufeff'):
        源码 = 源码[1:]
    源码, 元信息 = 解析声明(源码)
    声明版本 = 元信息.get('桥语言版本')
    if 声明版本 and 声明版本 != 版本:
        raise 方言错误(f'这个文件要求桥语言 {声明版本}，当前转译器是 {版本}')

    最后错误: SyntaxError | None = None
    转译结果 = ''
    for 前缀模式 in (False, True):
        转译结果 = 转译(源码, 规则=规, 前缀模式=前缀模式)
        try:
            return compile(转译结果, 文件名, 'exec'), 转译结果
        except SyntaxError as 错误:
            最后错误 = 错误

    行号 = getattr(最后错误, 'lineno', None)
    上下文 = ''
    提示 = ''
    if 行号:
        原文行 = 源码.splitlines()
        if 0 < 行号 <= len(原文行):
            原行 = 原文行[行号 - 1]
            上下文 = f'\n  第 {行号} 行：{原行.strip()}'
            if '?' in 原行 or '？' in 原行:
                提示 = ('\n  提示：问号是帮助语法（`如果?` / `如果 ？`），'
                        '名字里不能带 ?。想问某个词，就把它单独写成一行。')
    from .诊断 import 编译建议

    raise 方言错误(
        f'{文件名} 转译后仍然编译不过：{最后错误.msg}{上下文}{提示}'
        f'{编译建议(源码, 行号, 规)}',
        行号=行号, 列号=getattr(最后错误, 'offset', None),
    ) from None


def 运行(文件路径: str | Path, *, 参数: list[str] | None = None, 中文报错: bool = True,
         使用缓存: bool = True) -> dict:
    """转译并执行一个 .bridge 文件，返回它执行完成后的全局命名空间

    - 用户代码跑挂时抛 `报错.运行失败`，里面是可以直接打印的中文报错
      （行号指向 .bridge 源码，并附英文原文）；
    - `使用缓存=True` 时走 `.bridgec` 缓存，命中就跳过扫描（规则一改自动失效）。
    """
    from .报错 import 格式化, 运行失败

    路径 = Path(文件路径)
    if 使用缓存:
        from .缓存 import 编译文件

        代码, _, _ = 编译文件(路径)
    else:
        代码, _ = 编译(路径.read_text(encoding='utf-8-sig'), str(路径))
    from .运行时 import 桥返回, 运行时名字

    命名空间 = {
        '__name__': '__main__',
        '__file__': str(路径),
        '__builtins__': __builtins__,
    }
    命名空间.update(运行时名字())
    旧参数 = sys.argv
    try:
        sys.argv = [str(路径), *(参数 or [])]
        exec(代码, 命名空间)
    except 桥返回 as 信号:
        命名空间['__返回__'] = 信号.值
    except SystemExit:
        raise
    except BaseException as 异常:
        if not 中文报错:
            raise
        raise 运行失败(格式化(异常), 异常) from None
    finally:
        sys.argv = 旧参数
    return 命名空间


def 运行源码(源码: str, 文件名: str = '<桥>', *, 中文报错: bool = True) -> dict:
    """不落盘直接跑一段方言源码（给测试和 REPL 用）"""
    import linecache

    from .报错 import 格式化, 运行失败

    代码, _ = 编译(源码, 文件名)
    # 注册到 linecache：这样报错时也能打出源码那一行（否则行号对了但内容空）
    行们 = 源码.splitlines(keepends=True)
    linecache.cache[文件名] = (sum(len(l) for l in 行们), None, 行们, 文件名)
    from .运行时 import 桥返回, 运行时名字

    命名空间 = {'__name__': '__main__', '__builtins__': __builtins__}
    命名空间.update(运行时名字())
    try:
        exec(代码, 命名空间)
    except 桥返回 as 信号:
        命名空间['__返回__'] = 信号.值
    except SystemExit:
        raise
    except BaseException as 异常:
        if not 中文报错:
            raise
        raise 运行失败(格式化(异常), 异常) from None
    return 命名空间
