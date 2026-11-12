"""反向译：把 Python 源码翻译成桥语言源码

    python 工具/反向译.py <文件.py>            # 输出到 stdout
    python 工具/反向译.py <文件.py> -o 输出.bridge
    python 工具/反向译.py <目录> -o <输出目录>  # 批量

做什么：把 `def / if / for / print / math.pi / ValueError` 这些**英文词**
换成桥语言的中文写法，其余一个字符都不动（缩进、字符串、注释、空行、标识符全保留）。

为什么能保证"翻译是安全的"：桥语言的转译是纯词法替换，所以反向翻译只要保证
**每个替换都能被正向规则还原**（`print → 输出 → print`）。工具跑完后自带一个
`--验证` 模式：把产物再转回 Python，和原文逐字节比对。

故意不做的事：

- 不动标识符（`ROOT`、`app`、变量名一律保留）——桥语言不翻译标识符；
- 不动字符串和注释（那是数据/给人看的字，翻了就错）；
- f-string 里的 `{表达式}` 也不动（桥语言暂不支持 f-string 内翻译），只提示有几处；
- `{{` `}}`、字典、装饰器、`async` 等结构原样保留。
"""

from __future__ import annotations

import io
import json
import sys
import tokenize
from pathlib import Path

项目根 = Path(__file__).resolve().parent.parent
if str(项目根) not in sys.path:
    sys.path.insert(0, str(项目根))

from 转译器 import 转译, 载入规则  # noqa: E402

规则 = 载入规则()

# ---- 首选中文写法（一个英文词往往对应多个中文别名，这里挑最"正统"的那个）----
关键字首选 = {
    'def': '定义', 'return': '返回', 'if': '如果', 'elif': '否则如果', 'else': '否则',
    'for': '对于', 'in': '在', 'while': '当', 'and': '并且', 'or': '或者', 'not': '不是',
    'is': '是', 'True': '真', 'False': '假', 'None': '空', 'class': '类',
    'import': '导入', 'from': '从', 'as': '作为', 'try': '尝试', 'except': '捕获',
    'finally': '最终', 'raise': '抛出', 'pass': '通过', 'break': '中断', 'continue': '继续',
    'del': '删除', 'assert': '断言', 'with': '带', 'yield': '产出', 'async': '异步',
    'await': '等待', 'global': '全局', 'nonlocal': '非局部', 'lambda': 'lambda',
}

内建首选 = {
    'print': '输出', 'input': '输入', 'len': '长度', 'range': '范围', 'int': '整数',
    'float': '浮点', 'str': '字符串', 'bool': '布尔', 'list': '列表', 'dict': '字典',
    'set': '集合', 'tuple': '元组', 'sum': '求和', 'max': '最大', 'min': '最小',
    'abs': '绝对值', 'sorted': '排序', 'enumerate': '枚举', 'map': '映射',
    'filter': '过滤', 'any': '任意', 'all': '全部', 'zip': '拉链', 'repr': '复述',
    'round': '四舍五入', 'isinstance': 'isinstance', 'type': 'type',
}

异常首选 = {英文: 中文 for 中文, 英文 in 规则['异常'].items()}
模块首选 = {英文: 中文 for 中文, 英文 in 规则['模块'].items()}
成员首选: dict[str, dict[str, str]] = {}
for 模块, 表 in 规则['成员'].items():
    for 中文, 英文 in 表.items():
        成员首选.setdefault(模块, {}).setdefault(英文, 中文)   # 先登记者优先（睡眠 优于 延时）
# 真实模块名也建一份索引：`time.sleep` 也要能翻成 `时间.睡眠`
for 中文模块, 英文模块 in 规则['模块'].items():
    if 中文模块 in 成员首选:
        成员首选.setdefault(英文模块, 成员首选[中文模块])
方法首选 = {}
for 中文, 英文 in 规则['方法'].items():
    方法首选.setdefault(英文, 中文)


def _替换点号模块(源码: str) -> str:
    """把 `os.path`、`os.environ` 这种**带点的模块名**当成一个整体换掉

    tokenize 会把 `os.path` 切成 `os` `.` `path`，如果只翻 `os` 就会变成
    `系统.path`（实测产物）。所以先按"最长优先"把带点模块名整体换掉。
    """
    from 转译器.主转译器 import 分段

    带点 = {英: 中 for 中, 英 in 规则['模块'].items() if '.' in 英}
    if not 带点:
        return 源码
    模式 = __import__('re').compile(
        r'(?<![\w.])(' + '|'.join(__import__('re').escape(k) for k in sorted(带点, key=len, reverse=True)) + r')(?![\w])'
    )
    出: list[str] = []
    for 种类, 文本 in 分段(源码):
        出.append(模式.sub(lambda m: 带点[m.group(1)], 文本) if 种类 == '代码' else 文本)
    return ''.join(出)


def 反向译(源码: str, *, 翻译方法: bool = True) -> tuple[str, dict]:
    """返回 (桥语言源码, 统计)"""
    原源码 = 源码
    源码 = _替换点号模块(源码)
    行们 = 源码.splitlines(keepends=True)
    编辑: list[tuple[tuple[int, int], tuple[int, int], str]] = []
    统计 = {'关键字': 0, '内建': 0, '异常': 0, '模块': 0, '成员': 0, '方法': 0,
            'fstring内跳过': 0, 'fstring字段': 0}
    待属性模块: str | None = None
    f串深度 = 0
    f起 = getattr(tokenize, 'FSTRING_START', -1)
    f止 = getattr(tokenize, 'FSTRING_END', -1)

    for 令牌 in tokenize.generate_tokens(io.StringIO(源码).readline):
        文 = 令牌.string

        # f-string 内部是"字符串里的表达式"：桥语言的转译不进字符串，所以这里也不能动，
        # 否则 `f"{a if b else c}"` 会被翻译成中文却再翻不回来（实测踩过）
        if 令牌.type == f起:
            f串深度 += 1
            continue
        if 令牌.type == f止:
            f串深度 = max(0, f串深度 - 1)
            continue
        if f串深度:
            统计['fstring内跳过'] += 1
            continue

        if 令牌.type not in (tokenize.NAME, tokenize.OP):
            if 令牌.type in (tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT,
                            tokenize.INDENT, tokenize.DEDENT):
                待属性模块 = None      # 换行/注释后，"模块.属性" 的上下文断了
            continue

        # 模块名后面的属性：math.pi → 数学.圆周率
        if 待属性模块:
            if 令牌.type == tokenize.NAME:
                中文 = 成员首选.get(待属性模块, {}).get(文)
                if 中文:
                    编辑.append((令牌.start, 令牌.end, 中文))
                    统计['成员'] += 1
                待属性模块 = None
            elif 文 == '.':
                continue          # 等属性名出来再判，别把点号当成"属性没了"
            else:
                待属性模块 = None
            continue

        if 文 in 关键字首选:
            编辑.append((令牌.start, 令牌.end, 关键字首选[文]))
            统计['关键字'] += 1
            continue
        if 文 in 内建首选:
            编辑.append((令牌.start, 令牌.end, 内建首选[文]))
            统计['内建'] += 1
            continue
        if 文 in 异常首选:
            编辑.append((令牌.start, 令牌.end, 异常首选[文]))
            统计['异常'] += 1
            continue
        if 文 in 模块首选:
            编辑.append((令牌.start, 令牌.end, 模块首选[文]))
            统计['模块'] += 1
            待属性模块 = 文
            continue
        if 文 in 成员首选:
            # 模块名本身保持英文（json / os），但它的成员可以翻成中文
            待属性模块 = 文
            continue
        if 翻译方法 and 文 in 方法首选 and 令牌.type == tokenize.NAME:
            # 只翻「点号后面」的方法名：前面一个有效令牌是 '.'
            上一条 = _找上一条(源码, 令牌.start)
            if 上一条 is not None and 上一条.string == '.':
                编辑.append((令牌.start, 令牌.end, 方法首选[文]))
                统计['方法'] += 1

    # f-string：`{表达式}` 里的词也要翻（正向已经能翻进去，反向必须对上）
    from 转译器.f字符串 import 定位 as _f定位, 加工 as _f加工

    绝对编辑: list[tuple[int, int, str]] = []
    for 起, 止 in _f定位(源码):
        字面量 = 源码[起:止]
        # 只对「字段里的表达式」递归，别对整段字面量递归（那会自己调自己）
        新, 字段数 = _f加工(字面量, lambda 表达式: 反向译(表达式, 翻译方法=翻译方法)[0])
        统计['fstring字段'] = 统计.get('fstring字段', 0) + 字段数
        if 新 != 字面量:
            绝对编辑.append((起, 止, 新))

    # 把行/列坐标换成绝对偏移，和 f-string 的偏移编辑一起从后往前套
    行首: list[int] = [0]
    for 行 in 行们:
        行首.append(行首[-1] + len(行))
    for (行, 列), (_, 末列), 新 in 编辑:
        绝对编辑.append((行首[行 - 1] + 列, 行首[行 - 1] + 末列, 新))

    结果 = 源码
    for 起, 止, 新 in sorted(绝对编辑, key=lambda x: x[0], reverse=True):
        结果 = 结果[:起] + 新 + 结果[止:]
    return 结果, 统计


_令牌缓存: dict[int, list] = {}


def _找上一条(源码: str, 位置) -> tokenize.TokenInfo | None:
    """找位置紧挨在这之前的有效令牌（用来判断"点号后"）"""
    键 = id(源码)
    if 键 not in _令牌缓存:
        _令牌缓存[键] = list(tokenize.generate_tokens(io.StringIO(源码).readline))
    上一条 = None
    for 令牌 in _令牌缓存[键]:
        if 令牌.type in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                        tokenize.DEDENT, tokenize.COMMENT, tokenize.ENCODING):
            continue
        if 令牌.start >= 位置:
            return 上一条
        上一条 = 令牌
    return 上一条


def 验证(产物: str, 原文: str) -> tuple[bool, str]:
    """把产物再转回 Python，跟原文逐字节比对"""
    回来 = 转译(产物)
    if 回来 == 原文:
        return True, ''
    原行 = 原文.splitlines()
    回行 = 回来.splitlines()
    for i in range(max(len(原行), len(回行))):
        甲 = 原行[i] if i < len(原行) else '<缺行>'
        乙 = 回行[i] if i < len(回行) else '<缺行>'
        if 甲 != 乙:
            return False, f'第 {i + 1} 行\n  原: {甲!r}\n  回: {乙!r}'
    return False, '长度不同'


def 处理文件(源: Path, 出: Path | None, 映射: dict[str, str] | None = None,
             环境: dict | None = None) -> dict:
    """`映射` 非空时先把英文标识符改成中文，再做词级反译"""
    原文 = 源.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    工作文 = 原文
    改名数 = 0
    if 映射:
        from 改名 import 改名 as 执行改名

        工作文, 改名数 = 执行改名(原文, 映射, 环境['模块别名'], 环境['定义'],
                                  环境['属性'], 环境.get('项目模块'),
                                  环境.get('类'), 环境.get('参数表'))
    产物, 统计 = 反向译(工作文)
    好, 原因 = 验证(产物, 工作文)
    if 好 and 映射:
        from 改名 import 校验

        问题 = 校验(原文, 转译(产物), 映射)
        if 问题:
            好, 原因 = False, f'标识符改名对不上：{问题}'
    统计['往返一致'] = 好
    统计['改名'] = 改名数
    if not 好:
        统计['不一致'] = 原因
    if 出:
        出.parent.mkdir(parents=True, exist_ok=True)
        出.write_text(产物, encoding='utf-8', newline='\n')
    return 统计


def _准备改名环境(源: Path, 译名模块) -> tuple[dict[str, str], dict]:
    """先把所有文件扫一遍，收集名字、分配中文、过滤掉会撞规则表的名字"""
    from 改名 import 收集

    文件们 = sorted(源.rglob('*.py'))
    项目模块 = {文件.stem for 文件 in 文件们}
    模块别名: set[str] = set()
    定义: set[str] = set()
    属性: set[str] = set()
    项目类: set[str] = set()
    参数表: dict[str, set[str]] = {}
    可改: set[str] = set()
    for 文件 in 文件们:
        信息 = 收集(文件.read_text(encoding='utf-8-sig'), 项目模块)
        # 只有**项目自己的**模块才参与"模块.成员"改名；三级库的模块（sqlite3、re）
        # 不能算进来，否则 `sqlite3.connect` 会被当成项目函数改掉
        模块别名 |= (信息['模块'] & (项目模块 | {'程序'}))
        定义 |= 信息['定义']
        属性 |= 信息['属性']
        项目类 |= 信息.get('类', set())
        for 名, 参 in (信息.get('参数表') or {}).items():
            参数表.setdefault(名, set()).update(参)
        可改 |= 信息['可改']

    映射, 冲突 = 译名模块.分配(可改 | 定义)

    # 翻出来会撞规则表的名字，一律保留英文（否则正向转译会把变量名当关键字翻掉）
    from 转译器.规则加载 import 载入规则

    规则 = 载入规则()
    禁用 = set(规则['词表']) | set(规则['方法']) | set(规则['模块'])
    禁用长 = {词 for 词 in 禁用 if len(词) >= 2}

    import re as _re

    _汉字串 = _re.compile(r'[\u3400-\u9fff]+')

    def _安全(中: str) -> bool:
        """中文名里每段连续汉字都不能是规则词（或以其开头）

        为啥按"段"看：`PDF路径` 里的 `路径` 是一段独立的汉字串，正向转译会把它
        当成 os.path 的中文别名整段换掉。纯中文名只有一段，等价于整名检查。
        """
        for 段 in _汉字串.findall(中):
            if 段 in 禁用 or any(段.startswith(词) for 词 in 禁用长 if 词):
                return False
        return True

    映射 = {英: 中 for 英, 中 in 映射.items() if _安全(中)}

    return 映射, {'模块别名': 模块别名, '定义': 定义, '属性': 属性, '冲突': 冲突,
                  '项目模块': 项目模块, '类': 项目类, '参数表': 参数表}


def main(argv: list[str]) -> int:
    译名模式 = '--译名' in argv or '-n' in argv
    参数 = [a for a in argv if not a.startswith('-o') and a not in ('--译名', '-n')]
    if len(参数) < 2:
        print('用法：python 工具/反向译.py <文件.py|目录> [-o 输出] [--译名]')
        return 2
    源 = Path(参数[1])
    出 = None
    if '-o' in argv:
        出 = Path(argv[argv.index('-o') + 1])

    映射: dict[str, str] | None = None
    环境: dict | None = None
    if 译名模式:
        import 译名  # noqa: PLC0415

        映射, 环境 = _准备改名环境(源 if 源.is_dir() else 源.parent, 译名)
        print(f'标识符改名：{len(映射)} 个' +
              (f'（{len(环境["冲突"])} 个撞名已加序号）' if 环境['冲突'] else ''))

    if 源.is_dir():
        结果 = {}
        目标根 = 出 or (源.parent / (源.name + '-桥语言'))
        for 文件 in sorted(源.rglob('*.py')):
            相对 = 文件.relative_to(源).with_suffix('.bridge')
            结果[str(相对)] = 处理文件(文件, 目标根 / 相对, 映射, 环境)
        print(json.dumps(结果, ensure_ascii=False, indent=2))
        好 = sum(1 for v in 结果.values() if v.get('往返一致'))
        print(f'\n文件 {len(结果)} 个，往返一致 {好} 个')
        if 映射:
            print(f'标识符改名 {sum(v.get("改名", 0) for v in 结果.values())} 处')
        print(f'输出目录：{目标根}')
        return 0 if 好 == len(结果) else 1

    统计 = 处理文件(源, 出, 映射, 环境)
    if 出:
        print(f'已写出 {出}')
    print(json.dumps(统计, ensure_ascii=False, indent=2))
    return 0 if 统计.get('往返一致') else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
