"""桥语言命令行入口

    python 桥.py 运行  示例/你好.bridge
    python 桥.py 查看  示例/你好.bridge          # 打印转译后的标准 Python
    python 桥.py 编译  示例/你好.bridge -o 示例/你好.py
    python 桥.py 规则                            # 列出当前加载的规则表
    python 桥.py 检查  示例/你好.bridge          # 只转译不执行，检查语法

这个文件只做三件事：解析命令行 → 调 转译器 → 打印结果/错误。
所有语言逻辑都在 转译器/ 里，不要往这里塞规则。
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Windows 控制台默认 GBK，直接把输出钉成 UTF-8，避免中文乱码
for 流 in (sys.stdout, sys.stderr):
    try:
        流.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

项目根 = Path(__file__).resolve().parent
sys.path.insert(0, str(项目根))

from 转译器 import (  # noqa: E402
    转译, 编译, 运行, 方言错误, 载入规则, 规则清单, 安装导入钩子,
    运行失败, 缓存信息, 清理缓存, 版本,
)

用法 = f"""桥语言 {版本} · Python 的中文方言

用法：
  python 桥.py 运行  <文件.bridge> [-参数...]   转译并执行
  python 桥.py 查看  <文件.bridge>              打印转译后的标准 Python
  python 桥.py 编译  <文件.bridge> [-o 输出.py] [--自包含] 转译并写盘
  python 桥.py 检查  <文件.bridge> [--命名|--严格] 只转译不执行；--命名 查撞词，--严格 查可疑名字
  python 桥.py 规则                             列出当前加载的规则表
  python 桥.py 查    <中文词|英文名>            查一个词怎么映射，还有哪些同义写法
  python 桥.py 缓存  [清理]                    查看/清理 .bridgec 编译缓存
  python 桥.py 调试  <文件.bridge> [--断点 3,7:条件] 断点调试（n/o/c/p/e/l/q）
  python 桥.py repl  [一行代码]               交互式试写（不建文件）
  python 桥.py mcp                            MCP 服务（给 AI 工具调）
  python 桥.py init  [目录] [-f]               生成一个能跑的起步工程
  python 桥.py 体检                            规则表体检（重叠/非法映射/漏占位）
  python 桥.py 帮助  [词]                      问一个词怎么用；不写词看目录（= .bridge 里写 `词?`）
"""


def 找文件(参数: list[str]) -> Path:
    if not 参数:
        print(用法)
        raise SystemExit(2)
    路径 = Path(参数[0])
    if not 路径.is_file():
        print(f'找不到文件：{路径}', file=sys.stderr)
        raise SystemExit(2)
    return 路径


def 命令_运行(参数: list[str]) -> int:
    路径 = 找文件(参数)
    # 脚本同目录也加入规则搜索范围，这样 `导入 工具` 能找到同目录的 工具.bridge
    安装导入钩子([路径.parent, Path.cwd()])
    try:
        运行(路径, 参数=参数[1:])
    except 运行失败 as 错误:
        print(f'\n{错误.文本}', file=sys.stderr)
        return 1
    except 方言错误 as 错误:
        print(f'方言错误：{错误}', file=sys.stderr)
        return 1
    except SyntaxError as 错误:
        print(f'方言语法错误：{错误.msg}（行 {错误.lineno}）', file=sys.stderr)
        return 1
    except Exception:
        traceback.print_exc()
        return 1
    return 0


def 命令_查看(参数: list[str]) -> int:
    路径 = 找文件(参数)
    源码 = 路径.read_text(encoding='utf-8-sig')
    print(转译(源码))
    return 0


def 命令_编译(参数: list[str]) -> int:
    路径 = 找文件(参数)
    输出 = None
    if '-o' in 参数:
        输出 = Path(参数[参数.index('-o') + 1])
    else:
        输出 = 路径.with_suffix('.py')
    源码 = 路径.read_text(encoding='utf-8-sig')
    自包含 = '--自包含' in 参数 or '--self' in 参数
    转译结果 = 转译(源码)
    编译(源码, str(路径))                       # 顺手校验一次
    输出.parent.mkdir(parents=True, exist_ok=True)  # 输出目录不存在就建，别为个路径报错
    # 跳转/运行/并行/读取文档这些是"运行时名字"：编译成纯 .py 时得自带
    运行时名 = ('桥跳转', '桥返回', '桥运行', '桥并行', '桥读取', '桥新建', '桥删除',
              '桥等待', '文件', '文档', '结构化', 'JSON节点', '表格',
              '桥排队', '桥切片', '桥最后一个', '桥前几个', '桥倒过来',
              '桥读二进制', '桥打开压缩包', '桥帮助', '二进制文件', '压缩包')
    if any(名 in 转译结果 for 名 in 运行时名):
        根 = 项目根.as_posix()
        if 自包含:
            from 转译器.自包含 import 生成前缀

            头 = (f"import sys as _桥sys; _桥sys.path.insert(0, {根!r})  # 桥语言根\n"
                 + 生成前缀())
        else:
            头 = (
                # 编译产物可能被搬到别的目录跑，所以把桥语言根目录写进 sys.path
                f"import sys as _桥sys; _桥sys.path.insert(0, {根!r})  # 桥语言根\n"
                'from 转译器.运行时 import ' +
                ', '.join(名字 for 名字 in 运行时名 if 名字 in 转译结果) +
                '  # 桥语言运行时\n'
            )
        转译结果 = 头 + 转译结果
    输出.write_text(转译结果, encoding='utf-8')
    print(f'已写出：{输出}')
    return 0


def 命令_检查(参数: list[str]) -> int:
    路径 = 找文件(参数)
    源码 = 路径.read_text(encoding='utf-8-sig')
    代码, 转译结果 = 编译(源码, str(路径))
    print(f'语法检查通过：{路径}（{len(转译结果.splitlines())} 行）')

    from 转译器 import 检查命名
    from 转译器.规则加载 import 载入规则

    规则 = 载入规则()
    问题 = 检查命名(源码, 规则['词表'], 规则['方法'], 规则.get('成员'),
                规则.get('模块'))
    if 问题:
        print(f'\n命名提醒（{len(问题)} 处；`--命名` 可单独看，不影响检查结果）：')
        for 行, 名, 说明 in 问题:
            print(f'  第 {行} 行 「{名}」：{说明}')
        print('（规则词在词法层无条件替换，起名时避开它们）')

    # 命名提醒默认就显示（以前要加 --命名，等于没提醒）
    if '--严格' in 参数:
        严格问题 = _严格检查(源码)
        if 严格问题:
            print(f'\n严格检查：{len(严格问题)} 处')
            for 行, 说明 in 严格问题:
                print(f'  {说明}' if not 行 else f'  第 {行} 行：{说明}')
            return 1
        print('严格检查通过（没有发现可疑的未定义名）')
    return 0


def _严格检查(源码: str) -> list[tuple[int, str]]:
    """AST 版：报"被读、但从没在作用域里定义"的名字（带行号，保守）"""
    import ast
    import builtins

    from 转译器 import 编译

    try:
        译文 = 编译(源码, '<严格检查>')[1]
        树 = ast.parse(译文)
    except Exception:
        return []

    from 转译器.运行时 import 运行时名字

    内置 = (set(dir(builtins)) | set(运行时名字())
            | {'__file__', '__name__', '__builtins__', '__doc__',
               '文件', '文档', '结构化', 'JSON节点', '表格', '数据库', '数据库表',
               '响应', '事务', '桥打开数据库', '桥取网页', '桥发请求'})
    问题: list[tuple[int, str]] = []

    def 收集(节点) -> set[str]:
        """收集一个作用域里被"定义"的名字（含嵌套，宁缺勿滥）"""
        名: set[str] = set()
        栈 = [节点]
        while 栈:
            当前 = 栈.pop()
            if isinstance(当前, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                名.add(当前.name)
            if isinstance(当前, ast.arg):
                名.add(当前.arg)
            if isinstance(当前, ast.Name) and isinstance(当前.ctx, (ast.Store, ast.Del)):
                名.add(当前.id)
            if isinstance(当前, (ast.Import, ast.ImportFrom)):
                for 别名 in 当前.names:
                    名.add((别名.asname or 别名.name).split('.')[0])
            if isinstance(当前, ast.ExceptHandler) and 当前.name:
                名.add(当前.name)
            if isinstance(当前, ast.Global):
                名.update(当前.names)
            栈.extend(ast.iter_child_nodes(当前))
        return 名

    全局 = 收集(树)

    def 检查作用域(节点, 局部: set[str]) -> None:
        for 子 in ast.walk(节点):
            if isinstance(子, ast.Name) and isinstance(子.ctx, ast.Load):
                if (子.id not in 局部 and 子.id not in 全局 and 子.id not in 内置
                        and not 子.id.startswith('__')):
                    问题.append((子.lineno, f'「{子.id}」被用到，但这个作用域里没定义'))

    检查作用域(树, 全局)
    for 节点 in 树.body:
        if isinstance(节点, (ast.FunctionDef, ast.AsyncFunctionDef)):
            检查作用域(节点, 全局 | 收集(节点))

    return list(dict.fromkeys(问题))


def 命令_规则(参数: list[str]) -> int:
    规则 = 载入规则()
    print('规则文件（表名(条数)）：')
    for 文件, 表们 in 规则清单().items():
        print(f'  {文件:<12} {"  ".join(表们)}')
    print()
    print(f"关键字 {len(规则['关键字'])} 条 · 内建 {len(规则['内建'])} 条 · "
          f"异常 {len(规则['异常'])} 条 · 标点 {len(规则['标点'])} 条 · "
          f"方法 {len(规则['方法'])} 条 · 模块 {len(规则['模块'])} 个")
    print(f"已中文化的模块：{'、'.join(规则['模块']) or '（无）'}")
    print(f"已中文化的方法：{'、'.join(规则['方法']) or '（无）'}")
    return 0


def 命令_查(参数: list[str]) -> int:
    """查一个中文词的映射，以及「同一个 Python 关键字还能怎么写」"""
    规则 = 载入规则()
    词 = 参数[0] if 参数 else ''
    if not 词:
        print('用法：python 桥.py 查 <中文词或英文名>')
        return 2

    命中: list[tuple[str, str]] = []
    for 表名 in ('关键字', '内建', '异常', '模块'):
        if 词 in 规则[表名]:
            命中.append((表名, 规则[表名][词]))
    if 词 in 规则['方法']:
        命中.append(('方法（点号后）', 规则['方法'][词]))
    for 模块名, 成员表 in 规则['成员'].items():
        for 中文, 英文 in 成员表.items():
            if 词 in (中文, 英文):
                命中.append((f'成员.{模块名}', f'{中文} → {英文}'))
    # 英文名反查
    if not 命中:
        for 表名 in ('关键字', '内建', '异常', '模块'):
            for 中文, 英文 in 规则[表名].items():
                if 英文 == 词:
                    命中.append((表名, f'{中文} → {英文}'))
        for 中文, 英文 in 规则['方法'].items():
            if 英文 == 词:
                命中.append(('方法（点号后）', f'{中文} → {英文}'))

    if not 命中:
        print(f'规则表里没有 {词!r}（写英文原名也一样能跑，转译器原样透传）')
        return 1

    for 类别, 值 in 命中:
        if '→' in 值:
            print(f'{类别}：{值}')
        else:
            print(f'{类别}：{词} → {值}')

    目标值 = {值.split('→')[-1].strip() if '→' in 值 else 值 for _, 值 in 命中}
    同义: set[str] = set()
    for 表名 in ('关键字', '内建', '异常', '模块'):
        for 中文, 英文 in 规则[表名].items():
            if 英文 in 目标值 and 中文 != 词:
                同义.add(中文)
    for 中文, 英文 in 规则['方法'].items():
        if 英文 in 目标值 and 中文 != 词:
            同义.add(中文 + '（方法）')
    print(f'同一目标的其他写法：{"、".join(sorted(同义)) or "（无）"}')
    return 0


def 命令_缓存(参数: list[str]) -> int:
    信息 = 缓存信息()
    print(f"缓存文件：{信息['文件数']} 个，共 {信息['字节数'] / 1024:.1f} KB")
    print(f"当前规则指纹：{信息['指纹']}（规则一改，旧缓存自动失效）")
    if 参数 and 参数[0] in ('清理', '清空', '-c'):
        个数 = 清理缓存()
        print(f'已清理 {个数} 个缓存文件')
    return 0


def 命令_体检(参数: list[str]) -> int:
    from 转译器.体检 import 体检 as 跑体检, 统计

    结果 = 跑体检(载入规则(强制=True))
    计数 = 统计(结果)
    for 级别 in ('错误', '警告', '提示'):
        同级别 = [项 for 项 in 结果 if 项['级别'] == 级别]
        if not 同级别:
            continue
        print(f'[{级别}] {len(同级别)} 条')
        for 项 in 同级别:
            print(f"  · {项['项目']}：{项['说明']}")
        print()
    print(f"共 {len(结果)} 条：错误 {计数['错误']} / 警告 {计数['警告']} / 提示 {计数['提示']}")
    return 1 if 计数['错误'] else 0


def 命令_AI(参数: list[str]) -> int:
    """把「给 AI 的参考」直接打印出来（省得去目录里翻）

        python 桥.py AI             # 速查（适合整段粘给 AI）
        python 桥.py AI --完整      # 完整参考
        python 桥.py AI --json      # 机器可读规则表
        python 桥.py AI --路径      # 只打印文件在哪
    """
    目标们 = {
        '速查': 项目根 / 'AI速查.txt',
        '完整': 项目根 / 'AI参考.md',
        'json': 项目根 / 'docs' / '桥语言规则.json',
        '入口': 项目根 / 'AGENTS.md',
    }
    if '--路径' in 参数:
        for 名, 文件 in 目标们.items():
            print(f'{名:<4} {文件}  {"✓" if 文件.is_file() else "（缺，跑 python 工具/导出AI参考.py）"}')
        return 0
    键 = '完整' if any(a in ('--完整', '--full', '-f') for a in 参数) else (
        'json' if '--json' in 参数 else ('入口' if '--入口' in 参数 else '速查'))
    文件 = 目标们[键]
    if not 文件.is_file():
        print(f'没有 {文件.name}：先跑 python 工具/导出AI参考.py', file=sys.stderr)
        return 1
    print(文件.read_text(encoding='utf-8'), end='')
    return 0


def 命令_调试(参数: list[str]) -> int:
    """python 桥.py 调试 <文件> [--断点 3,7] [-- 传给程序的参数]"""
    from 转译器.调试 import 调试运行

    协议 = '--协议' in 参数
    if 协议:
        参数 = [a for a in 参数 if a != '--协议']

    断点: dict[int, str | None] = {}
    剩余: list[str] = []
    i = 0
    传入: list[str] = []
    while i < len(参数):
        if 参数[i] in ('--断点', '-b') and i + 1 < len(参数):
            for 段 in 参数[i + 1].replace('，', ',').split(','):
                段 = 段.strip()
                if not 段:
                    continue
                行号文本, _, 条件 = 段.partition(':')
                行号文本 = 行号文本.strip()
                if 行号文本.isdigit():
                    断点[int(行号文本)] = 条件.strip() or None
            i += 2
            continue
        if 参数[i] == '--':
            传入 = 参数[i + 1:]
            break
        剩余.append(参数[i])
        i += 1
    路径 = 找文件(剩余)
    if 协议:
        from 转译器.协议调试 import 协议调试

        return 协议调试(路径, set(断点), 传入)
    if not 断点:
        print('提示：没给断点，进去就会停在第一行（--断点 3,7 或 3:条件）',
              file=sys.stderr)
        return 调试运行(路径, {1: None}, 传入)
    return 调试运行(路径, 断点, 传入)


def 命令_mcp(参数: list[str]) -> int:
    from 转译器.MCP import main as mcp_main

    return mcp_main(参数)


def 命令_repl(参数: list[str]) -> int:
    from 转译器.REPL import main as repl_main

    return repl_main(参数)


def 命令_init(参数: list[str]) -> int:
    from 转译器.脚手架 import 初始化

    目标 = Path(参数[0]) if 参数 else Path.cwd()
    覆盖 = any(a in ('-f', '--force') for a in 参数)
    try:
        结果 = 初始化(目标, 覆盖=覆盖)
    except FileExistsError as 错误:
        print(f'{错误}\n（确实要覆盖就加 -f）', file=sys.stderr)
        return 1
    print(f'已在 {结果["目录"]} 生成起步工程：')
    for 名 in 结果['文件']:
        print(f'  · {名}')
    print()
    print('下一步：')
    print(f'  python 桥.py 运行 "{Path(结果["目录"]) / "主程序.bridge"}"')
    print(f'  python 桥.py repl          # 想试一句就试一句')
    return 0


def 命令_帮助(参数: list[str]) -> int:
    """`python 桥.py 帮助 如果` —— 和 .bridge 里写 `如果?` 是同一条链路"""
    from 转译器.运行时 import 桥帮助

    桥帮助(参数[0] if 参数 else '')
    return 0


命令表 = {
    '运行': 命令_运行,
    '帮助': 命令_帮助,
    '?': 命令_帮助,
    'help': 命令_帮助,    '查看': 命令_查看,
    '编译': 命令_编译,
    '检查': 命令_检查,
    '规则': 命令_规则,
    '查': 命令_查,
    '缓存': 命令_缓存,
    '体检': 命令_体检,
    'AI': 命令_AI,
    'ai': 命令_AI,
    '提示词': 命令_AI,
    '调试': 命令_调试,
    'mcp': 命令_mcp,
    'repl': 命令_repl,
    'init': 命令_init,
}


def main(参数: list[str]) -> int:
    if not 参数:
        print(用法)
        return 0
    命令 = 参数[0]
    if 命令 in ('-h', '--help'):
        print(用法)
        return 0
    处理器 = 命令表.get(命令)
    if 处理器 is None:
        print(f'未知命令：{命令}\n')
        print(用法)
        return 2
    return 处理器(参数[1:])


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
