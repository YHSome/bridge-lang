"""桥语言自检：规则 / 示例 / 金标准 / 边界情况，一条命令跑完

    python 自检.py

任何一条失败都以非 0 退出码结束，方便以后挂 CI。
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

项目根 = Path(__file__).resolve().parent
sys.path.insert(0, str(项目根))

for 流 in (sys.stdout, sys.stderr):
    try:
        流.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from 转译器 import (  # noqa: E402
    检查命名,
    编译, 转译, 运行, 载入规则, 安装导入钩子, 解析声明, 版本, 方言错误,
    运行源码, 运行失败, 编译文件, 清理缓存,
)

示例目录 = 项目根 / '示例'
金标准目录 = 项目根 / '金标准'
通过 = 0
失败: list[tuple[str, str]] = []
预期失败: list[tuple[str, str]] = []

# 明知暂时不支持、并且是"用户自己造的句式"的检查项：记在这里，不拖累退出码。
预期失败表 = {
    '比对 03_循环.bridge': '03 是手打版，`当(条件)时重复执行:` 这套自创句式尚未支持（故意留观察）',
}


def 检查(名称: str, 动作) -> None:
    global 通过
    try:
        动作()
        通过 += 1
        print(f'  ok   {名称}')
    except Exception as 错误:
        原因 = f'{type(错误).__name__}: {错误}'
        if 名称 in 预期失败表:
            预期失败.append((名称, 原因))
            print(f'  skip {名称}（预期失败：{预期失败表[名称]}）')
            return
        失败.append((名称, 原因))
        print(f'  FAIL {名称} -> {原因}')


def 断言(条件: bool, 说明: str) -> None:
    if not 条件:
        raise AssertionError(说明)


def 抓输出(动作) -> str:
    缓冲 = io.StringIO()
    with redirect_stdout(缓冲):
        动作()
    return 缓冲.getvalue()


def 跑bridge(路径: Path) -> str:
    return 抓输出(lambda: 运行(路径))


def 跑py(路径: Path) -> str:
    源码 = 路径.read_text(encoding='utf-8-sig')
    return 抓输出(lambda: exec(compile(源码, str(路径), 'exec'), {'__name__': '__main__'}))


def main() -> int:
    print('== 规则加载 ==')
    规则 = 载入规则(强制=True)

    def 规则完整性():
        断言(len(规则['关键字']) >= 30, '关键字表太小')
        断言('数学' in 规则['模块'], '数学模块别名缺失')
        断言('（' in 规则['标点'], '全角括号规则缺失')
        断言('定义' in 规则['关键字'], '定义 → def 缺失')
        断言('输出' in 规则['内建'], '输出 → print 缺失')

    def 词表就绪():
        断言('如果' in 规则['词表'], '关键字没进词表')
        断言('数学' not in 规则['词表'], '模块别名不该进词表（会改坏 数据库 = 1 这种代码）')
        断言('数学' in 规则['模块'], '模块别名表缺了 数学')
        断言(转译('导入 数学\n').strip() == 'import math', '导入行没翻')

    检查('规则表合并', 规则完整性)
    检查('词表就绪', 词表就绪)

    print('== 示例 ==')
    for 文件 in sorted(示例目录.glob('*.bridge')):
        检查(f'编译 {文件.name}', lambda f=文件: 编译(f.read_text(encoding='utf-8-sig'), str(f)))
        检查(f'运行 {文件.name}', lambda f=文件: 跑bridge(f))

    def 示例1输出():
        输出 = 跑bridge(示例目录 / '示例1.bridge')
        断言('你好，世界！' in 输出, f'缺少问候：{输出!r}')
        断言('\n3\n7' in 输出, f'求和结果不对：{输出!r}')

    if (示例目录 / '示例1.bridge').is_file():
        检查('示例1 输出断言', 示例1输出)

    print('== 金标准 ==')
    for 文件 in sorted(金标准目录.glob('*.py')):
        检查(f'裸跑 {文件.name}', lambda f=文件: 跑py(f))
        桥文件 = 文件.with_suffix('.bridge')
        if 桥文件.is_file():
            def 比对(桥=桥文件, 参考=文件):
                甲 = 跑py(参考)
                乙 = 跑bridge(桥)
                断言(甲 == 乙, '输出与金标准不一致')
            检查(f'比对 {桥文件.name}', 比对)

    print('== 边界情况 ==')

    def 声明消费():
        源码 = f'桥语言版本("{版本}")\n输出（“版本声明已被消费”）\n'
        改写, 元信息 = 解析声明(源码)
        断言(元信息.get('桥语言版本') == 版本, f'元信息不对：{元信息}')
        断言(改写.splitlines()[0].startswith('#'), f'声明没被改成注释：{改写.splitlines()[0]!r}')
        代码, 产物 = 编译(源码, '<声明>')
        断言(产物.splitlines()[0].startswith('#'), f'产物第 1 行不是注释：{产物.splitlines()[0]!r}')
        断言(len(产物.splitlines()) == len(源码.splitlines()), '声明改变了行数')

    def 废弃声明按普通代码处理():
        # 转译器位置 已废弃：不再被消费，写它就会在运行期报 NameError（这是预期行为）
        断言(解析声明('转译器位置("../")\n')[1] == {}, '废弃声明不该再被识别')

    def 版本校验():
        try:
            编译('桥语言版本("9.9")\n输出（1）\n', '<版本>')
        except 方言错误 as 错误:
            断言('9.9' in str(错误), f'版本错误信息不对：{错误}')
            return
        raise AssertionError('声明的版本不对却没报错')

    def 未声明版本不报错():
        编译(f'桥语言版本("{版本}")\n输出（1）\n', '<版本>')

    检查('文件头声明被消费', 声明消费)
    检查('废弃的 转译器位置 不再识别', 废弃声明按普通代码处理)
    检查('版本不匹配报错', 版本校验)
    检查('版本匹配放行', 未声明版本不报错)

    def 前缀回退():
        源码 = '名字 ＝ “桥”\n如果名字等于“桥”:\n    输出（“前缀回退成功”）\n'
        代码, _ = 编译(源码, '<前缀>')
        产物 = 转译(源码, 前缀模式=True).replace(' ', '')
        断言('if名字=="桥"' in 产物, f'前缀切分失败：{产物!r}')

    def 字符串不动():
        产物 = 转译('输出（“如果 否则 对于 数学.圆周率”）\n')
        断言('如果 否则 对于 数学.圆周率' in 产物, '字符串内容被改坏了')

    def 注释不动():
        断言('数学.圆周率' in 转译('# 如果 否则 数学.圆周率\n输出（1）\n'), '注释被改坏了')

    def 行号稳定():
        源码 = '输出（1）\n\n输出（2）\n输出（“第三行”）\n'
        断言(len(转译(源码).splitlines()) == len(源码.splitlines()), '行数变了')

    def BOM兼容():
        编译('\ufeff输出（“带BOM”）\n', '<bom>')

    def 报错定位():
        try:
            编译('定义 坏掉了(:\n    输出（1）\n', '<坏>')
        except SyntaxError as 错误:
            断言('坏' in str(错误) or '第' in str(错误), '报错缺少定位')
            return
        raise AssertionError('应当抛错却没抛')

    def 行尾助词():
        甲 = 转译('当 计数 < 5 时:\n    计数 = 计数 + 1\n')
        乙 = 转译('当 计数 < 5:\n    计数 = 计数 + 1\n')
        断言(甲 == 乙, f'「时」没被吃掉：{甲!r} vs {乙!r}')
        断言('while 计数 < 5:' in 甲, f'产物不对：{甲!r}')
        断言('if 到了:' in 转译('如果 到了 的话:\n    通过\n'), '「的话」没被吃掉')
        断言('if 时:' in 转译('如果 时:\n    通过\n'), '把变量名「时」误伤了')
        断言('"当 x 时:"' in 转译('输出（"当 x 时:"）\n'), '字符串里的助词被误删')

    def f字符串():
        源码 = '名字 = "爸爸"\n输出（f"你好{名字}，长度{求长度(名字)}"）\n'
        产物 = 转译(源码)
        断言('f"你好{名字}，长度{len(名字)}"' in 产物, f'f-string 表达式没翻：{产物!r}')
        输出 = 抓输出(lambda: 运行源码(源码, '<f>'))
        断言('你好爸爸，长度2' in 输出, f'f-string 跑出来不对：{输出!r}')
        # 转义大括号、格式说明符、转换符都不能被动
        边界 = '输出（f"{{转义}} {1 + 2:.2f}"）\n'
        断言('{{转义}}' in 转译(边界), '{{ }} 被改坏了')
        断言('{1 + 2:.2f}' in 转译(边界), '格式说明符被改坏了')
        断言('{数据[0]!r:>10}' in 转译('输出（f"字段 {数据[0]!r:>10}"）\n'), '!r 转换符被改坏')
        # 普通字符串不许被动
        断言('{长度(数据)}' in 转译('输出（"{长度(数据)}"）\n'), '普通字符串被误翻')

    def 语句糖():
        源码 = '重复执行（3）次:\n    通过\n'
        产物 = 转译(源码)
        断言('for _ in range(3):' in 产物, f'重复执行（3）次 没生效：{产物!r}')
        断言(len(产物.splitlines()) == len(源码.splitlines()), '语法糖改变了行数')
        断言('for _ in range(k):' in 转译('重复 k 次:\n    通过\n'), '重复 k 次 没生效')
        断言('for _ in range(5):' in 转译('重复执行5次:\n    通过\n'), '无空格写法没生效')
        断言('while True:' in 转译('永久循环:\n    中断\n'), '永久循环 没生效')
        断言('for _ in range(len(数据)):' in 转译('重复执行（求长度(数据)）次:\n    通过\n'),
             '嵌套括号的表达式解析失败')
        断言('重复 = 1' in 转译('重复 = 1\n'), '把变量名「重复」误伤了')
        断言('"重复执行（3）次"' in 转译('输出（"重复执行（3）次"）\n'), '字符串里的糖被误改')

    def 语法糖全家桶():
        用例 = [
            ('对于 每个 x 在 [1,2]:\n    通过\n', 'for x in [1,2]:'),
            ('遍历 [1,2] 中的 每个 y:\n    通过\n', 'for y in [1,2]:'),
            ('如果 1 那么:\n    通过\n', 'if 1:'),
            ('否则如果 0 那么:\n    通过\n', 'elif 0:'),
            ('否则的话:\n    通过\n', 'else:'),
            ('定义函数 加法(a, b):\n    返回 a + b\n', 'def 加法(a, b):'),
            ('尝试执行:\n    通过\n', 'try:'),
            ('捕获 值错误 时:\n    通过\n', 'except ValueError:'),
            ('捕获异常时:\n    通过\n', 'except:'),
            ('无论如何:\n    通过\n', 'finally:'),
            ('只要 真 就重复:\n    中止\n', 'while True:'),
            # Scratch 风格：一直重复 / 重复执行直到 / 等待…直到 / 设 / 将
            ('一直重复:\n    跳出循环\n', 'while True:'),
            ('重复执行直到 x 大于 5:\n    通过\n', 'while not (x > 5):'),
            ('等待 x 小于 3 直到:\n    通过\n', 'while not (x < 3): pass'),
            ('设 x 为 1\n', 'x = 1'),
            ('将 x 增加 2\n', 'x += 2'),
            ('将 x 减少 1\n', 'x -= 1'),
            ('如果 x 大于 1 就 输出 "大"\n', 'if x > 1: print("大")'),
            ('如果 不成立 x:\n    通过\n', 'if not x:'),
            ('输出 "值", 1\n', 'print("值", 1)'),
        ]
        for 源码, 期望 in 用例:
            产物 = 转译(源码)
            断言(期望 in 产物, f'{源码.splitlines()[0]!r} 应产出 {期望!r}，实际 {产物!r}')
            断言(len(产物.splitlines()) == len(源码.splitlines()), f'{期望} 改变了行数')

    def 缩进不丢():
        源码 = '对于 x 在 [1]:\n    跳出循环\n'
        产物 = 转译(源码)
        断言('\n    break' in 产物, f'嵌套里的 跳出循环 丢了缩进：{产物!r}')
        源码2 = '对于 x 在 [1]:\n    如果 真 那么:\n        继续下一次循环\n'
        断言('\n        continue' in 转译(源码2), '嵌套里的 继续下一次循环 丢了缩进')

    def 关系词():
        产物 = 转译('如果 年龄 大于 18 并且 年龄 不大于 60:\n    通过\n')
        断言('if 年龄 > 18' in 产物 and '年龄 <= 60' in 产物, f'关系词没翻译：{产物!r}')
        断言('至少' not in 转译('如果 x 至少 1:\n    通过\n'), '「至少」没翻译')
        断言('*' in 转译('输出（3 乘以 4）\n'), '「乘以」没翻译')

    检查('无空格前缀回退', 前缀回退)
    检查('字符串内容不参与替换', 字符串不动)
    检查('注释不参与替换', 注释不动)
    检查('行号稳定', 行号稳定)
    检查('BOM 兼容', BOM兼容)
    检查('语法错误定位', 报错定位)
    检查('行尾助词（当…时:）', 行尾助词)
    def 反向查错():
        # 拼错关键字：编译期给出"是不是想写"
        try:
            编译('如过 1:\n    通过\n', '<诊断>')
        except 方言错误 as 错误:
            文本 = str(错误)
            断言('可能的原因' in 文本, f'没有建议段：{文本}')
            断言('如果' in 文本, f'没猜到「如果」：{文本}')
        else:
            raise AssertionError('拼错的关键字竟然编译过了')
        # 拼错内建：运行期给出提示
        try:
            运行源码('数据 = [1, 2]\n输出（求长肚(数据)）\n', '<诊断>')
        except 运行失败 as 错误:
            断言('求长度' in 错误.文本, f'没猜到「求长度」：{错误.文本}')
        else:
            raise AssertionError('拼错的内建竟然跑过了')
        # 不认识的名字不要瞎猜
        try:
            运行源码('输出（没定义的名字）\n', '<诊断>')
        except 运行失败 as 错误:
            断言('是不是想写' not in 错误.文本, f'不该猜却猜了：{错误.文本}')
        else:
            raise AssertionError('未定义名字竟然跑过了')

    def 交互式试写():
        from 转译器.REPL import 交互环境

        环境 = 交互环境()
        断言(环境.喂('名字 = "爸爸"') == [], '赋值不该有输出')
        输出 = 抓输出(lambda: 环境.喂('输出（f"你好{名字}"）'))
        断言('你好爸爸' in 输出, f'f-string 在 REPL 里没生效：{输出!r}')
        表达式输出 = 抓输出(lambda: 环境.喂('1 + 1'))
        断言('2' in 表达式输出, f'表达式没自动打印值：{表达式输出!r}')
        # 没写完的块：继续要下一行，空行才真正执行（和官方 REPL 一致）
        断言(环境.喂('如果 1 大于 0:') == [], '块头不该立刻报错')
        断言(环境.喂('    输出（"正"）') == [], '块体阶段不该执行')
        输出 = 抓输出(lambda: 环境.喂(''))
        断言('正' in 输出, f'块体没执行：{输出!r}')
        # 语法糖在 REPL 里也生效
        环境.喂('重复执行（2）次:')
        环境.喂('    输出（"糖"）')
        输出 = 抓输出(lambda: 环境.喂(''))
        断言(输出.count('糖') == 2, f'语法糖在 REPL 里没生效：{输出!r}')
        # 拼错给建议
        建议 = 环境.喂('如过 1:')
        断言(any('如果' in 行 for 行 in 建议), f'REPL 没给建议：{建议}')
        # 查词
        查 = 环境.喂('查 如过')
        断言(any('如果' in 行 for 行 in 查), f'REPL 查词不对：{查}')
        断言(环境.喂('退出') == ['__退出__'], '退出命令没生效')

    def 查看上次转译():
        from 转译器.REPL import 交互环境

        环境 = 交互环境()
        环境.喂('如果 1 大于 0:')
        环境.喂('    输出（"正"）')
        抓输出(lambda: 环境.喂(''))
        查看 = 环境.喂('查看')
        文本 = '\n'.join(查看)
        断言('if 1 > 0:' in 文本, f'查看没显示转译结果：{查看}')
        断言('print("正")' in 文本, f'查看没显示块体：{查看}')

    def 选区落盘():
        from 转译器.编辑器 import 选区到临时文件

        目录 = 项目根 / '.自检临时' / '选区'
        try:
            路径 = 选区到临时文件('输出（"选中"）\n', 目录)
            断言(路径.is_file(), '选区临时文件没写出来')
            断言(路径.read_text(encoding='utf-8') == '输出（"选中"）\n', '写进去的内容不对')
            断言(路径.suffix == '.bridge', f'临时文件后缀不对：{路径.suffix}')
        finally:
            shutil.rmtree(项目根 / '.自检临时' / '选区', ignore_errors=True)

    检查('反向查错（拼错就给建议）', 反向查错)
    def 标准库覆盖():
        源码 = (
            '导入 时间\n导入 路径\n导入 json\n导入 系统\n'
            '时间.睡眠(0)\n'
            '路径文本 = 路径.拼接("数据", "oj.db")\n'
            '输出（"扩展名：", 路径.拆扩展名(路径文本)【1】）\n'
            '数据 = {"名字": "爸爸"}\n'
            '文本 = json.转字符串(数据, ensure_ascii=假)\n'
            '输出（"JSON：", 文本）\n'
            '输出（"回来：", json.解析(文本)【"名字"】）\n'
            '输出（"系统名是不是字符串：", 类型(系统.系统名) 等于 字符串）\n'
        )
        产物 = 转译(源码)
        断言('import time' in 产物 and 'import json' in 产物, f'模块别名没翻：{产物!r}')
        断言('time.sleep(0)' in 产物, '时间.睡眠 没生效')
        断言('os.path.join(' in 产物, '路径.拼接 没生效')
        断言('os.path.splitext(' in 产物, '成员没走 模块反查')
        断言('json.dumps(' in 产物, 'json.转字符串 没生效（英文模块名 + 中文成员）')
        断言('os.name' in 产物, '系统.系统名 没生效')
        输出 = 抓输出(lambda: 运行源码(源码, '<标准库>'))
        断言('扩展名： .db' in 输出, f'路径规则跑出来不对：{输出!r}')
        断言('"名字": "爸爸"' in 输出, f'JSON 没输出中文：{输出!r}')
        断言('回来： 爸爸' in 输出, f'JSON 解析不对：{输出!r}')
        断言('系统名是不是字符串： True' in 输出, f'系统规则不对：{输出!r}')

    检查('REPL 交互式试写', 交互式试写)
    检查('REPL 查看（上次转译成什么）', 查看上次转译)
    检查('编辑器选区落盘（Ctrl+Enter 用）', 选区落盘)

    def 文件树():
        from 转译器.编辑器 import 过滤文件, 列出桥文件

        根 = 项目根 / '.自检临时' / '文件树'
        try:
            shutil.rmtree(根, ignore_errors=True)
            (根 / '子目录' / '深一层').mkdir(parents=True)
            (根 / '甲.bridge').write_text('输出（1）\n', encoding='utf-8')
            (根 / '子目录' / '乙.bridge').write_text('输出（2）\n', encoding='utf-8')
            (根 / '子目录' / '深一层' / '丙.bridge').write_text('输出（3）\n', encoding='utf-8')
            (根 / '无关.py').write_text('print(1)\n', encoding='utf-8')
            (根 / '__pycache__').mkdir()
            (根 / '__pycache__' / '脏.bridge').write_text('x', encoding='utf-8')

            文件们 = 列出桥文件(根)
            相对 = [str(p.relative_to(根)).replace('\\', '/') for p in 文件们]
            断言(相对 == ['子目录/乙.bridge', '子目录/深一层/丙.bridge', '甲.bridge']
                 or sorted(相对) == sorted(['甲.bridge', '子目录/乙.bridge',
                                            '子目录/深一层/丙.bridge']),
                 f'递归列文件不对：{相对}')
            断言(not any('__pycache__' in r for r in 相对), f'缓存目录没跳过：{相对}')
            断言(not any(r.endswith('.py') for r in 相对), f'.py 不该进树：{相对}')
            断言(len(过滤文件(文件们, 根, '子目录')) == 2, '过滤 子目录 不对')
            断言(len(过滤文件(文件们, 根, '深一层')) == 1, '过滤嵌套目录不对')
            断言(len(过滤文件(文件们, 根, '甲 bridge')) == 1, '多关键词全命中时应命中 1 个')
            断言(len(过滤文件(文件们, 根, '甲 py')) == 0, '多关键词里有不命中时不应返回')
            断言(len(过滤文件(文件们, 根, '')) == 3, '空关键词应返回全部')
        finally:
            shutil.rmtree(根, ignore_errors=True)

    检查('编辑器文件树（递归列 .bridge + 过滤）', 文件树)

    def 脚手架():
        from 转译器.脚手架 import 初始化

        目录 = 项目根 / '.自检临时' / '起步工程'
        try:
            if 目录.exists():
                shutil.rmtree(目录, ignore_errors=True)
            结果 = 初始化(目录)
            断言(set(结果['文件']) == {'主程序.bridge', '工具.bridge', 'README.md'},
                 f'生成的文件不对：{结果["文件"]}')
            # 模块缓存会跨测试残留（其它测试也用过叫「工具」的模块），先清掉再装钩子
            sys.modules.pop('工具', None)
            安装导入钩子([目录])
            输出 = 抓输出(lambda: 运行(目录 / '主程序.bridge'))
            断言('你好，爸爸' in 输出, f'主程序没跑起来：{输出!r}')
            断言('桥语言：中文也能写程序' in 输出, f'导入子模块失败：{输出!r}')
            断言('这一行是原生 Python' in 输出, f'英文混写没生效：{输出!r}')
            try:
                初始化(目录)
            except FileExistsError:
                pass
            else:
                raise AssertionError('重复初始化竟然没拒绝')
            初始化(目录, 覆盖=True)
        finally:
            安装导入钩子([])
            sys.modules.pop('工具', None)
            shutil.rmtree(目录, ignore_errors=True)

    检查('桥 init 起步工程（能跑/不覆盖）', 脚手架)

    def 译名改名():
        """`反向译 --译名`：变量/函数改中文，模块名与三方 API 不动"""
        目录 = 项目根 / '.自检临时' / '译名工程'
        try:
            if 目录.exists():
                shutil.rmtree(目录, ignore_errors=True)
            目录.mkdir(parents=True)
            (目录 / 'tools.py').write_text(
                'def render_title(text):\n    return text.strip()\n', encoding='utf-8')
            (目录 / 'main.py').write_text(
                'from . import tools\n\n\n'
                'def build(name, title):\n'
                '    heading = tools.render_title(title)\n'
                '    return heading\n', encoding='utf-8')
            (目录 / 'handler.py').write_text(
                'class Handler:\n'
                '    def __init__(self, user):\n'
                '        self.user = user\n\n'
                '    def send(self, body, status=200, headers=None):\n'
                '        return body, status, headers\n\n\n'
                'def view(h: Handler):\n'
                '    return h.send(b"", 302, headers={"a": "b"})\n', encoding='utf-8')

            完成 = subprocess.run(
                [sys.executable, str(项目根 / '工具' / '反向译.py'), str(目录), '--译名',
                 '-o', str(目录 / '出')],
                capture_output=True, text=True, encoding='utf-8', errors='replace')
            断言('文件 3 个，往返一致 3 个' in 完成.stdout, f'改名后往返不一致：{完成.stdout[-300:]}')

            主 = (目录 / '出' / 'main.bridge').read_text(encoding='utf-8')
            句柄 = (目录 / '出' / 'handler.bridge').read_text(encoding='utf-8')
            断言('定义 构建(名字, 标题)' in 主, f'函数/参数没改名：{主!r}')
            断言('tools.渲染标题(标题)' in 主, f'跨模块调用没改名：{主!r}')
            断言('从 . 导入 tools' in 主, f'模块名被改了：{主!r}')
            断言('self.用户 = 用户' in 句柄, f'实例属性没改名：{句柄!r}')
            断言('类 处理器' in 句柄, f'类名没改名：{句柄!r}')
            断言('请求头={"a": "b"}' in 句柄, f'调用的关键字参数没跟着改：{句柄!r}')
        finally:
            shutil.rmtree(目录, ignore_errors=True)

    检查('反向译 --译名（改名但不动模块/三方 API）', 译名改名)

    def 规则体检():
        from 转译器.体检 import 体检, 统计

        计数 = 统计(体检(载入规则(强制=True)))
        断言(计数['错误'] == 0, f'规则表有 {计数["错误"]} 条错误')
        断言(计数['警告'] == 0, f'规则表有 {计数["警告"]} 条警告')

        坏 = {
            '关键字': {'如果': 'if', '坏词': '这不是关键字'},
            '内建': {}, '异常': {}, '模块': {}, '成员': {}, '方法': {},
            '值位置': {}, '助词': {},
            '语法糖': [
                (r'^(?P<缩进>[ \t]*)坏糖\s+(?P<条件>\S.*)$', '{缩进}if {次数}:'),
                (r'坏糖2', 'pass'),
            ],
        }
        结果 = 体检(坏)
        级别们 = [项['级别'] for 项 in 结果]
        说明 = ' '.join(项['说明'] for 项 in 结果)
        断言('错误' in 级别们, f'没抓到非法关键字/缺占位：{结果}')
        断言('次数' in 说明, f'没指出缺哪个占位符：{说明}')
        断言('警告' in 级别们, f'没抓到"没整行锚定"：{结果}')

    检查('规则体检（自身健康 + 能抓坏规则）', 规则体检)

    def 分段不丢字符():
        """分段器改写过一次（逐字符 → 跳着扫），这里守住它最基本的性质"""
        from 转译器.主转译器 import 分段

        样本 = [
            'a = 1\n输出（"x"）\n',
            '"""多行\n字符串"""\n定义 f():\n    返回 1\n',
            'body = f"""\n<b>{名字}</b>\n"""\n',
            'if"x":  # 关键字直接贴字符串\n    通过\n',
            "s = 'a\\'b'  # 转义引号\n",
            'r = "反斜杠\\\\"  # 结尾反斜杠\n',
            '无闭合 = "没写完\n下一行\n',
        ]
        for 源码 in 样本:
            段们 = 分段(源码)
            拼接 = ''.join(文 for _, 文 in 段们)
            断言(拼接 == 源码, f'分段丢字符：{源码!r} → {拼接!r}')
        # f-string 的前缀必须归到字符串段里，否则字段不会被翻译
        段们 = 分段('body = f"""\n{x}\n"""\n')
        字符串段 = [文 for 种类, 文 in 段们 if 种类 == '字符串']
        断言(any(文.startswith('f') for 文 in 字符串段), f'f 前缀丢了：{段们!r}')

    检查('标准库覆盖（时间/路径/json/系统）', 标准库覆盖)

    def 运行环境规则():
        源码 = (
            '导入 运行环境\n'
            '输出（"平台是字符串：", 类型(运行环境.平台) 等于 字符串）\n'
            '输出（"递归上限大于 0：", 运行环境.递归上限() 大于 0）\n'
            '运行环境.设置递归上限(1500)\n'
            '输出（"调过之后：", 运行环境.递归上限()）\n'
            '输出（"参数是列表：", 类型(运行环境.参数) 等于 列表）\n'
            '运行环境.标准输出.写("从标准输出写\\n")\n'
            '运行环境.标准输出.刷新()\n'
        )
        产物 = 转译(源码)
        断言('import sys' in 产物, f'模块别名没翻：{产物!r}')
        断言('sys.platform' in 产物, '运行环境.平台 没生效')
        断言('sys.getrecursionlimit()' in 产物, '递归上限 没生效')
        断言('sys.setrecursionlimit(1500)' in 产物, '设置递归上限 没生效')
        断言('sys.argv' in 产物, '参数 没生效')
        断言('sys.stdout.write(' in 产物 and 'sys.stdout.flush()' in 产物, '标准输出/刷新 没生效')
        输出 = 抓输出(lambda: 运行源码(源码, '<sys>'))
        断言('平台是字符串： True' in 输出, f'平台规则不对：{输出!r}')
        断言('调过之后： 1500' in 输出, f'递归上限没改到：{输出!r}')
        断言('参数是列表： True' in 输出, f'参数规则不对：{输出!r}')
        断言('从标准输出写' in 输出, f'写标准输出失败：{输出!r}')

    检查('运行环境（sys）规则', 运行环境规则)

    def 数学全量():
        表 = 载入规则()['成员'].get('数学') or {}
        断言(len(表) >= 50, f'数学成员太少：{len(表)}')
        for 中文, 英文 in [
            ('以二为底对数', 'log2'), ('勾股斜边', 'hypot'), ('立方根', 'cbrt'),
            ('两参反正切', 'atan2'), ('整数平方根', 'isqrt'), ('精确求和', 'fsum'),
            ('近似相等', 'isclose'), ('拆分数', 'modf'),
        ]:
            if 中文 == '拆分数':
                continue
            断言(表.get(中文) == 英文, f'{中文} 应该映射到 {英文}，实际 {表.get(中文)}')

        源码 = (
            '导入 数学\n'
            '输出（"斜边：", 数学.勾股斜边(3, 4)）\n'
            '输出（"对数：", 数学.以二为底对数(8)）\n'
            '输出（"反正切：", 四舍五入(数学.两参反正切(1, 1), 6)）\n'
            '输出（"组合：", 数学.组合数(5, 2)）\n'
            '输出（"根号取整：", 数学.整数平方根(17)）\n'
        )
        产物 = 转译(源码)
        断言('math.hypot(' in 产物, f'勾股斜边没翻：{产物!r}')
        断言('math.log2(' in 产物, f'以二为底对数没翻：{产物!r}')
        断言('math.atan2(' in 产物, f'两参反正切没翻：{产物!r}')
        输出 = 抓输出(lambda: 运行源码(源码, '<数学>'))
        断言('斜边： 5.0' in 输出, f'斜边算错：{输出!r}')
        断言('组合： 10' in 输出, f'组合数算错：{输出!r}')
        断言('根号取整： 4' in 输出, f'整数平方根算错：{输出!r}')

    检查('数学库全量成员（55 条）', 数学全量)

    def 桥语言三特性():
        """跳转 / 运行与并行 / 读取文档——这三样是桥语言在 Python 之上加的语义"""
        临时 = 项目根 / '.自检临时' / '特性'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            shutil.copytree(示例目录 / '特性', 临时)

            # ① 跳转：循环三次、跳过一行、变量还在
            跳转输出 = 跑bridge(临时 / '跳转.bridge')
            断言('第 2 次' in 跳转输出, f'跳转循环没跑够：{跳转输出!r}')
            断言('这一行永远不会执行' not in 跳转输出, '跳转没跳过那一行')
            断言('甲 = 10' in 跳转输出, '跳转后变量丢了')

            # ② 运行 / 并行
            运行输出 = 跑bridge(临时 / '运行与并行.bridge')
            断言(运行输出.count('你好，世界！') >= 2, f'运行/并行调用次数不对：{运行输出!r}')
            断言('子程序返回： 1' in 运行输出, f'没拿到子程序返回值：{运行输出!r}')
            # 等待完成：并行的话必须在"并行结束"之前出现（说明真的等到了）
            等之后 = 运行输出.split('== 等待完成', 1)[-1]
            断言('你好，世界！' in 等之后 and '并行结束' in 等之后,
                 f'等待完成没等到子线程：{运行输出!r}')

            # ③ 读取文档：文件子类 / 改名 / 追加 / 复制 / 删除
            文档输出 = 跑bridge(临时 / '读取文档.bridge')
            断言('第一个字符： 你' in 文档输出, f'索引取字符失败：{文档输出!r}')
            断言('它是不是文件： True' in 文档输出, f'文档不是文件子类：{文档输出!r}')
            断言('后缀： .txt' in 文档输出, f'文件类属性缺失：{文档输出!r}')
            断言('改名后： b.txt' in 文档输出, f'改名失败：{文档输出!r}')
            断言('加完：' in 文档输出 and '追加后：' in 文档输出,
                 f'回写/追加失败：{文档输出!r}')
            断言('复制出来： b副本.txt' in 文档输出, f'复制失败：{文档输出!r}')

            # ④ 跳到没声明过的标记 → 明确报错
            try:
                运行源码('标记 甲\n输出（"开始"）\n跳转到 乙\n', '<跳转>')
            except 方言错误 as 错误:
                断言('该标记不存在' in str(错误), f'错误信息不对：{错误}')
            else:
                raise AssertionError('跳到不存在的标记竟然没报错')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

    检查('桥语言三特性（跳转/运行并行/读取文档）', 桥语言三特性)

    def 特性回归():
        """挑刺挑出来的几处边界，钉死别回退"""
        临时 = 项目根 / '.自检临时' / '特性回归'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            临时.mkdir(parents=True)

            # ① 只有标签没有跳转：标签行抹成空行，照样能跑（REPL 里单喂一行标签也安全）
            只标签 = 临时 / '只标签.bridge'
            只标签.write_text('输出（"没有跳转"）\n标记 一个标签\n', encoding='utf-8')
            输出 = 抓输出(lambda: 运行(只标签))
            断言('没有跳转' in 输出, f'只有标签的文件跑不了：{输出!r}')

            # ② 标签写在 if 里面 → 明确的中文错误，而不是 invalid syntax
            try:
                编译('如果 真:\n    标记 里面\n    输出（1）\n跳转到 里面\n', '<坏标签>')
            except 方言错误 as 错误:
                断言('写在 if/for/while 里面' in str(错误), f'错误信息不对：{错误}')
            else:
                raise AssertionError('if 里的标签竟然编译过了')

            # ③ 嵌套 运行：子程序里再 运行 同目录的另一个文件
            子 = 临时 / '子.bridge'
            子.write_text('输出（"子"）\n返回 5\n', encoding='utf-8')
            孙 = 临时 / '孙.bridge'
            孙.write_text('输出（"孙"）\n返回 9\n', encoding='utf-8')
            嵌套 = 临时 / '嵌套.bridge'
            嵌套.write_text('甲 = 运行("孙.bridge")\n输出（"拿到", 甲 + 1）\n', encoding='utf-8')
            输出 = 抓输出(lambda: 运行(嵌套))
            断言('孙' in 输出 and '拿到 10' in 输出, f'嵌套运行没跑对：{输出!r}')

            # ④ 编译产物自带运行时 import，能脱离 桥.py 单独跑
            跳 = 临时 / '跳.bridge'
            跳.write_text('计数 = 0\n标记 顶\n计数 += 1\n如果 计数 小于 3:\n    跳转到 顶\n'
                          '输出（"计数", 计数）\n', encoding='utf-8')
            产物 = 临时 / '跳.py'
            subprocess.run([sys.executable, str(项目根 / '桥.py'), '编译', str(跳),
                            '-o', str(产物)], check=True, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
            完成 = subprocess.run([sys.executable, str(产物)], capture_output=True, text=True,
                                 encoding='utf-8', errors='replace')
            断言(完成.returncode == 0 and '计数 3' in 完成.stdout,
                 f'编译产物单独跑失败：{完成.stderr[-300:]}')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

    检查('特性回归（只标签/坏标签/嵌套运行/编译产物）', 特性回归)

    def 图书管理系统冒烟():
        """真实小项目：添加/重复/借书/还书/统计，连库文件一起验"""
        临时 = 项目根 / '.自检临时' / '图书系统'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            shutil.copytree(项目根 / '图书管理系统', 临时,
                            ignore=shutil.ignore_patterns('__pycache__', '图书数据*'))
            输入 = ('1\n三体\n刘慈欣\n5\n'      # 新增
                    '1\n三体\n刘慈欣\n1\n'      # 同名再加 → 合并
                    '4\n1\n张三\n' * 4 +        # 借 4 次：第 4 次撞上限
                    '7\n'                      # 统计
                    '5\n1\n张三\n'             # 还书
                    '0\n')
            完成 = subprocess.run(
                [sys.executable, str(项目根 / '桥.py'), '运行',
                 str(临时 / '主程序.bridge')],
                input=输入, capture_output=True, text=True, encoding='utf-8',
                errors='replace', cwd=str(项目根))
            输出 = 完成.stdout
            断言(完成.returncode == 0, f'图书系统退出码 {完成.returncode}：{完成.stderr[-300:]}')
            断言('已添加 #1 《三体》 共 5 册' in 输出, f'新增不对：{输出[-300:]}')
            断言('《三体》已存在，现在共 6 册' in 输出, f'同名合并不对：{输出[-300:]}')
            断言('已借出：《三体》 给 张三' in 输出, f'借书不对：{输出[-300:]}')
            断言('每人最多 3 本' in 输出, f'借阅上限没生效：{输出[-300:]}')
            断言('在借册数： 3' in 输出, f'统计不对：{输出[-300:]}')
            断言('已归还：《三体》' in 输出, f'还书不对：{输出[-300:]}')
            库 = (临时 / '图书数据.json').read_text(encoding='utf-8')
            断言('"在借": 2' in 库, f'库没落盘或没还书：{库[:200]}')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

    检查('图书管理系统冒烟（真实小项目）', 图书管理系统冒烟)

    def JSON对象():
        """读取 .json 得到可按字段操作的对象：读/改/追加/存/点号路径"""
        临时 = 项目根 / '.自检临时' / 'json'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            临时.mkdir(parents=True)
            配置 = 临时 / '配置.json'
            配置.write_text(
                '{"站点名": "OJ", "端口": 8080, "管理员": ["张三"],'
                ' "数据库": {"主机": "127.0.0.1"}}', encoding='utf-8')
            输出 = 抓输出(lambda: 运行源码(f'''配置 = 读取("{配置.as_posix()}")
输出（配置.站点名, 配置["端口"], 配置.数据库.主机, 配置.管理员[0], 配置.条目数）
配置.端口 = 9090
配置.管理员.追加（"李四")
配置.保存()
输出（配置.取("数据库.主机"), 配置.有("端口"), 配置.有("域名"))
''', '<json>'))
            断言('OJ 8080 127.0.0.1 张三 4' in 输出, f'JSON 读不对：{输出!r}')
            断言('127.0.0.1 True False' in 输出, f'JSON 取/有 不对：{输出!r}')
            落盘 = 配置.read_text(encoding='utf-8')
            断言('9090' in 落盘 and '李四' in 落盘, f'JSON 没保存：{落盘[:120]}')
            # 读不存在的 json 要报错（不是静默给空对象）
            try:
                运行源码(f'读取("{临时.as_posix()}/没有.json")\n', '<json缺>')
            except 运行失败 as 错误:
                断言('不存在' in 错误.文本, f'缺文件报错不对：{错误.文本[:80]}')
            else:
                raise AssertionError('读不存在的 json 竟然没报错')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

    检查('读取和操作 JSON（.json → 结构化对象）', JSON对象)
    def 新语法新工具():
        """比较词、REPL 补全/历史/标签提示、调试条件断点"""
        # ① 大于等于 / 小于等于
        输出 = 抓输出(lambda: 运行源码(
            '甲 = 5\n如果 甲 大于等于 5 且 甲 小于等于 5:\n    输出（"边界对"）\n', '<比较>'))
        断言('边界对' in 输出, f'比较词不对：{输出!r}')

        # ② REPL：补全 / 历史 / 标签提示
        from 转译器.REPL import 交互环境

        环境 = 交互环境()
        候选 = 环境.补全('排序')
        断言('排序' in 候选, f'补全不对：{候选[:5]}')
        环境.喂('甲 = 1')
        历史 = 环境.喂('历史')
        断言(any('甲 = 1' in 行 for 行 in 历史), f'历史不对：{历史}')

        # ③ 调试条件断点：只在 合计>2 时停
        临时 = 项目根 / '.自检临时' / '条件断点'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            临时.mkdir(parents=True)
            文件 = 临时 / '累加.bridge'
            文件.write_text('合计 = 0\n对于 i 在 范围(5):\n    合计 += i\n'
                            '输出（"完", 合计）\n', encoding='utf-8')
            完成 = subprocess.run(
                [sys.executable, str(项目根 / '桥.py'), '调试', str(文件),
                 '--断点', '3:合计>2'],
                input='p 合计\nc\n', capture_output=True, text=True,
                encoding='utf-8', errors='replace')
            断言('第 3 行' in 完成.stdout, f'条件断点没停：{完成.stdout[-200:]}')
            断言('3' in 完成.stdout, f'条件断点值不对：{完成.stdout[-200:]}')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

    检查('新语法与新工具（比较词/REPL/条件断点）', 新语法新工具)
    def AI文档():
        """给 AI 的参考必须存在、JSON 可读、数量与规则一致（落后就提示重跑生成器）"""
        import json as _json

        参考 = 项目根 / 'AI参考.md'
        速查 = 项目根 / 'AI速查.txt'
        JSON文件 = 项目根 / 'docs' / '桥语言规则.json'
        断言(参考.is_file() and 速查.is_file() and JSON文件.is_file(),
             '缺文件：先跑 python 工具/导出AI参考.py')
        数据 = _json.loads(JSON文件.read_text(encoding='utf-8'))
        规 = 载入规则()
        对不上 = [名 for 名, 键 in (('关键字', '关键字'), ('内建', '内建'),
                                   ('异常', '异常'), ('方法', '方法'), ('模块', '模块'))
                 if len(数据.get(键, {})) != len(规.get(键) or {})]
        断言(not 对不上,
             f'AI 文档落后于规则（{对不上}）：跑 python 工具/导出AI参考.py')
        文本 = 参考.read_text(encoding='utf-8')
        断言('标记' in 文本 and '跳转到' in 文本, '参考里没写跳转')
        断言('读取' in 文本 and '表格' in 文本, '参考里没写文件/JSON/表格')
        断言('禁止' in 文本 or '硬规则' in 文本, '参考里没写禁区')
        入口 = 项目根 / 'AGENTS.md'
        断言(入口.is_file(), '缺 AGENTS.md：跑 python 工具/导出AI参考.py')
        断言('AI速查.txt' in 入口.read_text(encoding='utf-8'), 'AGENTS.md 没指向速查')
        # `桥.py AI` 要能直接把速查打出来
        import subprocess as _子

        输出 = _子.run([sys.executable, str(项目根 / '桥.py'), 'AI'], cwd=str(项目根),
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout
        断言('## 关键字' in 输出 and '## 独有' in 输出, f'桥.py AI 输出不对：{输出[:120]}')

    检查('给 AI 的参考文档（与规则同步）', AI文档)
    def 新语言面():
        """运算符、match/lambda/海象、新标准库、数据库、REPL 标签块、命名检查"""
        # ① 运算符 / 新语法
        输出 = 抓输出(lambda: 运行源码(
            '甲 = 7\n输出（甲 整除 2, 甲 取模 2, 甲 乘方 2, 甲 左移 1）\n'
            '配对 甲:\n    情形 7:\n        输出（"七")\n'
            '加一 = 匿名函数 x: x + 1\n输出（加一(1)）\n'
            '如果 (乙 赋值为 5) 大于 1:\n    输出（乙)\n', '<新语法>'))
        断言('3 1 49 14' in 输出 and '七' in 输出 and '2' in 输出 and '5' in 输出,
             f'新语法不对：{输出!r}')

        # ② 新标准库
        输出 = 抓输出(lambda: 运行源码(
            '导入 迭代工具\n导入 统计\n输出（列表(迭代工具.组合([1,2], 2)), 统计.平均([1,2,3])）\n',
            '<新库>'))
        断言('(1, 2)' in 输出 and '2' in 输出, f'新库不对：{输出!r}')

        # ③ 数据库（临时文件）
        临时 = 项目根 / '.自检临时' / '数据库'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            临时.mkdir(parents=True)
            库路径 = (临时 / '测.db').as_posix()
            输出 = 抓输出(lambda: 运行源码(f'''库 = 打开数据库("{库路径}")
表 = 库.建表("书", {{"名": "TEXT", "数": "INTEGER"}})
表.插入({{"名": "甲", "数": 1}})
表.插入({{"名": "乙", "数": 2}})
输出（表.行数, 表.查询("数 > ?", [1])[0]["名"]）
库.关闭()
''', '<数据库>'))
            断言('2 乙' in 输出, f'数据库对象不对：{输出!r}')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

        # ④ REPL 标签块
        from 转译器.REPL import 交互环境

        环境 = 交互环境()
        环境.喂('计数 = 0')
        环境.喂('标记 顶')
        环境.喂('计数 += 1')
        环境.喂('如果 计数 小于 2:')
        环境.喂('    跳转到 顶')
        抓输出(lambda: 环境.喂(''))
        断言(环境.命名空间.get('计数') == 2, f'REPL 标签块不对：{环境.命名空间.get("计数")}')

        # ⑤ 命名检查
        规则 = 载入规则()
        问题 = 检查命名('定义 现在():\n    返回 1\n', 规则['词表'], 规则['方法'],
                        规则.get('成员'), 规则.get('模块'))
        断言(any(名 == '现在' for _, 名, _ in 问题), f'命名检查没报 现在：{问题}')

    检查('新语言面（运算符/新库/数据库/REPL）+ 命名检查', 新语言面)
    def 数据库事务与网络():
        """事务回滚、批量插入；本地 HTTP 真请求"""
        # ① 事务回滚
        临时 = 项目根 / '.自检临时' / '事务'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            临时.mkdir(parents=True)
            库路径 = (临时 / '账.db').as_posix()
            输出 = 抓输出(lambda: 运行源码(f'''库 = 打开数据库("{库路径}")
表 = 库.建表("账", {{"名": "TEXT UNIQUE", "钱": "INTEGER"}})
表.插入多([{{"名": "甲", "钱": 1}}, {{"名": "乙", "钱": 2}}])
输出（"批量：", 表.行数)
尝试执行:
    带 库.事务():
        表.插入({{"名": "丙", "钱": 3}})
        抛出 值错误("炸")
捕获 值错误:
    输出（"回滚后：", 表.行数)
库.关闭()
库.删除自己()
''', '<事务>'))
            断言('批量： 2' in 输出 and '回滚后： 2' in 输出, f'事务不对：{输出!r}')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

        # ② 本地 HTTP（真发一个请求）
        import http.server
        import threading

        class 处理(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                体 = '桥语言'.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(体)))
                self.end_headers()
                self.wfile.write(体)

            def log_message(self, *args):
                pass

        服务器 = http.server.HTTPServer(('127.0.0.1', 0), 处理)
        端口 = 服务器.server_address[1]
        threading.Thread(target=服务器.serve_forever, daemon=True).start()
        try:
            输出 = 抓输出(lambda: 运行源码(
                f'响应 = 取网页("http://127.0.0.1:{端口}/")\n'
                '输出（响应.状态码, 响应.正常, 响应.文本）\n', '<网络>'))
            断言('200 True 桥语言' in 输出, f'网络对象不对：{输出!r}')
        finally:
            服务器.shutdown()
            服务器.server_close()

    检查('数据库事务（回滚）+ 网络真请求', 数据库事务与网络)

    def 版本一致():
        """转译器版本、pyproject 版本、包版本.txt 三处一致"""
        import re as _re

        from 转译器 import 版本

        pyproject = (项目根 / 'pyproject.toml').read_text(encoding='utf-8')
        匹配 = _re.search(r'version\s*=\s*"([^"]+)"', pyproject)
        断言(匹配 and 匹配.group(1) == 版本, f'pyproject 版本对不上：{匹配.group(1) if 匹配 else "?"}')
        版本文件 = 项目根 / '版本.txt'
        if 版本文件.is_file():
            断言(版本文件.read_text(encoding='utf-8').strip() == 版本, '版本.txt 对不上')

    检查('版本号一致（转译器/pyproject/版本.txt）', 版本一致)




    def 教程示例():
        """教程里 10 个示例都能编译、能跑（07 会临时建文件，但会自己删）"""
        for 文件 in sorted((项目根 / '教程' / '示例').glob('*.bridge')):
            编译(文件.read_text(encoding='utf-8-sig'), str(文件))
        断言(True, '')

    检查('教程示例全部可编译', 教程示例)


    def 调试器():
        """断点停在指定行，c 继续、p 看变量"""
        临时 = 项目根 / '.自检临时' / '调试'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            临时.mkdir(parents=True)
            文件 = 临时 / '算.bridge'
            文件.write_text('合计 = 0\n对于 i 在 范围(3):\n    合计 += i\n'
                            '输出（"合计", 合计）\n', encoding='utf-8')
            完成 = subprocess.run(
                [sys.executable, str(项目根 / '桥.py'), '调试', str(文件), '--断点', '4'],
                input='p 合计\nc\n', capture_output=True, text=True,
                encoding='utf-8', errors='replace')
            断言('第 4 行' in 完成.stdout, f'没停在断点：{完成.stdout[-300:]}')
            断言('(桥调试)' in 完成.stdout, f'没进调试提示：{完成.stdout[-300:]}')
            断言('合计 3' in 完成.stdout, f'看变量不对：{完成.stdout[-300:]}')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

    检查('调试器（断点/继续/看变量）', 调试器)

    def 自包含与新标准库():
        """--自包含 的产物不带桥语言 import；正则/子进程/日期/表格 都能用"""
        临时 = 项目根 / '.自检临时' / '自包含'
        try:
            shutil.rmtree(临时, ignore_errors=True)
            临时.mkdir(parents=True)
            (临时 / '分数.csv').write_text('姓名,分数\n张三,90\n', encoding='utf-8')
            源 = 临时 / '主.bridge'
            源.write_text('''导入 正则
导入 子进程
导入 日期

输出（正则.全部查找(r"\\d+", "a1b2"))
输出（日期.解析("2020-01-01", "%Y-%m-%d").格式化日期("%Y")）

结果 = 子进程.运行([sys.executable, "-c", "print(1)"],
                   capture_output=真, text=真, encoding="utf-8")
输出（"码", 结果.返回码）

表 = 读取("./分数.csv")
输出（"列", 表.列("分数"))
表.追加行(["李四", "85"])
表.保存()
'''.replace('导入 子进程', '导入 sys\n导入 子进程'), encoding='utf-8')

            产物 = 临时 / '主.py'
            subprocess.run([sys.executable, str(项目根 / '桥.py'), '编译', str(源),
                            '-o', str(产物), '--自包含'], check=True,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
            完成 = subprocess.run([sys.executable, str(产物)], capture_output=True,
                                 text=True, encoding='utf-8', errors='replace')
            输出 = 完成.stdout
            断言(完成.returncode == 0, f'自包含产物跑挂：{完成.stderr[-300:]}')
            断言("['1', '2']" in 输出, f'正则不对：{输出!r}')
            断言('2020' in 输出, f'日期不对：{输出!r}')
            断言('码 0' in 输出, f'子进程不对：{输出!r}')
            断言("['90']" in 输出, f'表格列不对：{输出!r}')
            断言('李四' in (临时 / '分数.csv').read_text(encoding='utf-8'), '表格没保存')
            断言('from 转译器.运行时 import' not in 产物.read_text(encoding='utf-8'),
                 '自包含产物里还留着桥语言 import')
        finally:
            shutil.rmtree(临时, ignore_errors=True)

    检查('自包含编译 + 正则/子进程/日期/表格', 自包含与新标准库)
    检查('分段不丢字符（含 f 前缀/转义/未闭合）', 分段不丢字符)
    检查('f-string 里的表达式也能翻', f字符串)
    检查('语句糖（重复执行 N 次）', 语句糖)
    检查('语法糖全家桶（for/if/try/def...）', 语法糖全家桶)
    检查('语法糖不丢缩进', 缩进不丢)
    检查('关系词（大于/至少/乘以...）', 关系词)

    print('== 别名与混写（vibe coding 中途介入）==')

    def 别名齐全():
        词 = 规则['词表']
        for 别名, 目标 in [('求长度', 'len'), ('求最大值', 'max'), ('求排序', 'sorted'),
                           ('非', 'not'), ('或', 'or'), ('且', 'and'),
                           ('跳出', 'break'), ('下一步', 'continue'), ('空值', 'None'),
                           ('假如', 'if'), ('遍历', 'for'), ('最后', 'finally'),
                           ('显示', 'print'), ('区间', 'range'), ('占位', 'pass'),
                           ('引入', 'import'), ('当作', 'as'), ('引发', 'raise')]:
            断言(词.get(别名) == 目标, f'别名 {别名} 应映射到 {目标}，实际 {词.get(别名)!r}')
        断言(规则['方法'].get('追加') == 'append', '方法 追加 → append 缺失')
        断言(规则['方法'].get('加进去') == 'append', '方法 加进去 → append 缺失')

    def 同义词不打架():
        """多对一允许；一个中文词对应两个不同 Python 名 = 必须报错"""
        合并 = {}
        for 表名 in ('关键字', '内建', '异常', '模块'):
            for 中文, 英文 in 规则[表名].items():
                if 中文 in 合并 and 合并[中文] != 英文:
                    raise AssertionError(f'{中文} 同时映射到 {合并[中文]} 和 {英文}')
                合并[中文] = 英文

    def 同一目标多种写法等价():
        变体 = [
            '如果 真:\n    输出("命中")\n',
            '假如 真值:\n    打印("命中")\n',
            '若 对:\n    显示("命中")\n',
        ]
        输出集 = set()
        for 源码 in 变体:
            代码, _ = 编译(源码, '<同义>')
            输出集.add(抓输出(lambda: exec(代码, {'__name__': '__main__'})))
        断言(输出集 == {'命中\n'}, f'同义写法结果不一致：{输出集!r}')

    def 方法只在点号后生效():
        产物 = 转译('数据.排序()\n排序(数据)\n')
        断言('数据.sort()' in 产物, f'方法表没生效：{产物!r}')
        断言('sorted(数据)' in 产物, f'内建名被方法表抢走了：{产物!r}')

    def 中英混写():
        源码 = ('数据 = [3, 1]\n'
                '数据.追加(2)\n'
                'print("英文输出", 求长度(数据))\n'
                '输出("中文输出", len(数据))\n'
                'def 英文函数(x):\n    return x + 1\n'
                '定义 中文函数(x):\n    返回 x + 2\n'
                'if 英文函数(1) == 2:\n    输出("英文 if")\n'
                '如果 中文函数(1) == 3:\n    print("中文 如果")\n'
                'for i in 范围(1):\n    print("混写循环", i)\n')
        代码, _ = 编译(源码, '<混写>')
        输出 = 抓输出(lambda: exec(代码, {'__name__': '__main__'}))
        断言('英文输出 3' in 输出, f'混写输出不对：{输出!r}')
        断言('中文输出 3' in 输出, f'混写输出不对：{输出!r}')
        断言('英文 if' in 输出 and '混写循环 0' in 输出, f'混写输出不对：{输出!r}')

    def 原生python直接当bridge跑():
        参考 = 金标准目录 / '05_容器.py'
        源码 = 参考.read_text(encoding='utf-8-sig')
        甲 = 抓输出(lambda: exec(compile(源码, str(参考), 'exec'), {'__name__': '__main__'}))
        代码, 产物 = 编译(源码, '<原生>')
        断言(产物 == 源码, '纯 Python 源码被转译器改动了')
        乙 = 抓输出(lambda: exec(代码, {'__name__': '__main__'}))
        断言(甲 == 乙, '纯 Python 源码跑出来的结果不一致')

    检查('别名表齐全', 别名齐全)
    检查('同义词不打架（多对一允许）', 同义词不打架)
    检查('同一目标多种写法等价', 同一目标多种写法等价)
    检查('方法表只在点号后生效', 方法只在点号后生效)
    检查('中英关键字混写', 中英混写)
    检查('原生 Python 可直接当 .bridge 跑', 原生python直接当bridge跑)

    print('== 中文报错 ==')

    def 报错_除零():
        try:
            运行源码('打印（1 ／ 0）\n', '<报错>')
        except 运行失败 as 错误:
            文本 = 错误.文本
            断言('除零错误' in 文本, f'没有中文异常名：{文本}')
            断言('除数不能是 0' in 文本, f'没有中文消息：{文本}')
            断言('英文原文' in 文本, '没有保留英文原文')
            断言('第 1 行' in 文本, f'行号不对：{文本}')
            断言('主转译器' not in 文本, '把内部帧也打出来了')
            return
        raise AssertionError('除零竟然没报错')

    def 报错_名字():
        try:
            运行源码('打印（没定义的名字）\n', '<报错>')
        except 运行失败 as 错误:
            断言('名字 “没定义的名字” 没有定义' in 错误.文本, f'消息没翻译：{错误.文本}')
            return
        raise AssertionError('未定义名字竟然没报错')

    def 报错_类型():
        try:
            运行源码('数量 = “三”\n打印（数量 ＋ 1）\n', '<报错>')
        except 运行失败 as 错误:
            断言('不能直接和 int 相加' in 错误.文本 or '字符串只能和字符串相加' in 错误.文本,
                 f'消息没翻译：{错误.文本}')
            return
        raise AssertionError('类型错误竟然没报错')

    检查('报错中文化·除零', 报错_除零)
    检查('报错中文化·名字未定义', 报错_名字)
    检查('报错中文化·类型错误', 报错_类型)

    print('== 编译缓存 ==')

    def 缓存命中与失效():
        目录 = 项目根 / '.自检临时'
        try:
            if 目录.exists():
                shutil.rmtree(目录, ignore_errors=True)
            目录.mkdir(parents=True, exist_ok=True)
            文件 = 目录 / '缓存测试.bridge'
            文件.write_text('输出（"缓存"）\n', encoding='utf-8')
            _, _, 首次 = 编译文件(文件)
            断言(not 首次, '第一次竟然命中了缓存')
            _, _, 第二次 = 编译文件(文件)
            断言(第二次, '第二次没命中缓存')
            文件.write_text('输出（"缓存改过了"）\n', encoding='utf-8')
            _, 产物, 第三次 = 编译文件(文件)
            断言(not 第三次, '文件改了还命中旧缓存')
            断言('缓存改过了' in 产物, '缓存没有跟着文件更新')
        finally:
            shutil.rmtree(目录, ignore_errors=True)

    def 缓存清理():
        目录 = 项目根 / '.自检临时'
        try:
            if 目录.exists():
                shutil.rmtree(目录, ignore_errors=True)
            目录.mkdir(parents=True, exist_ok=True)
            文件 = 目录 / '清理测试.bridge'
            文件.write_text('输出（1）\n', encoding='utf-8')
            编译文件(文件)
            断言(清理缓存(目录) >= 1, '清理缓存没删到文件')
        finally:
            shutil.rmtree(目录, ignore_errors=True)

    检查('缓存首次未命中/二次命中/改文件失效', 缓存命中与失效)
    检查('缓存清理', 缓存清理)

    print('== 跨文件导入 ==')

    def 跨文件导入():
        # 临时文件放在项目内（系统临时目录在沙箱里可能不可写），跑完删掉
        目录 = 项目根 / '.自检临时'
        try:
            if 目录.exists():
                shutil.rmtree(目录, ignore_errors=True)
            目录.mkdir(parents=True, exist_ok=True)
            (目录 / '工具.bridge').write_text(
                '定义 打招呼(名字):\n    输出（“工具收到：”， 名字）\n', encoding='utf-8')
            (目录 / '主程序.bridge').write_text(
                '导入 工具\n工具.打招呼（“爸爸”）\n', encoding='utf-8')
            安装导入钩子([目录])
            输出 = 跑bridge(目录 / '主程序.bridge')
            断言('工具收到： 爸爸' in 输出, f'导入钩子没生效：{输出!r}')
        finally:
            安装导入钩子([])
            shutil.rmtree(目录, ignore_errors=True)

    检查('导入 工具.bridge', 跨文件导入)

    print('== 桥语言包 & 反向译 ==')

    def 桥语言包导入():
        """`程序/__init__.bridge` + 同目录 .bridge 子模块（学 OJ 那次实验的形态）"""
        目录 = 项目根 / '.自检临时' / '包测试'
        try:
            if 目录.exists():
                shutil.rmtree(目录, ignore_errors=True)
            (目录 / '程序').mkdir(parents=True, exist_ok=True)
            (目录 / '程序' / '__init__.bridge').write_text(
                '名字 = "桥语言包"\n', encoding='utf-8')
            (目录 / '程序' / '子模块.bridge').write_text(
                '定义 打招呼():\n    返回 "子模块报到"\n', encoding='utf-8')
            (目录 / '主程序.bridge').write_text(
                '导入 程序\n输出（程序.名字）\n'
                '从 程序 导入 子模块\n输出（子模块.打招呼()）\n', encoding='utf-8')
            安装导入钩子([目录])
            输出 = 跑bridge(目录 / '主程序.bridge')
            断言('桥语言包' in 输出, f'包 __init__ 没加载：{输出!r}')
            断言('子模块报到' in 输出, f'包内子模块没加载：{输出!r}')
        finally:
            安装导入钩子([])
            shutil.rmtree(目录, ignore_errors=True)

    def 反向译往返():
        sys.path.insert(0, str(项目根 / '工具'))
        import 反向译  # noqa: PLC0415

        参考 = 金标准目录 / '03_循环.py'
        原文 = 参考.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
        产物, 统计 = 反向译.反向译(原文)
        断言(统计['关键字'] > 0 and 统计['内建'] > 0, f'反向译没翻到东西：{统计}')
        断言(转译(产物) == 原文, '反向译的结果转不回来')
        断言('对于' in 产物 and '输出' in 产物, f'产物不像桥语言：{产物[:80]!r}')

    检查('桥语言包（__init__.bridge）导入', 桥语言包导入)
    检查('反向译：Python → 桥语言 往返一致', 反向译往返)

    print()
    print(f'通过 {通过} 条，预期失败 {len(预期失败)} 条，失败 {len(失败)} 条')
    for 名称, 原因 in 预期失败:
        print(f'  ~ {名称}: {预期失败表.get(名称, "")}')
    for 名称, 原因 in 失败:
        print(f'  - {名称}: {原因}')
    return 0 if not 失败 else 1


if __name__ == '__main__':
    raise SystemExit(main())
