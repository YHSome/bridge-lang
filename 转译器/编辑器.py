"""桥语言编辑器 —— 轻量 IDE：写 .bridge，一键运行

双击（或 `python 转译器/编辑器.py`）就能开，零第三方依赖，只用标准库 tkinter：

    ┌───────────────────────────────────────────────┐
    │ 打开  保存  另存为 │ ▶ 运行(F5)  ■ 停止  转译预览 │
    ├───────────────────────────────────────────────┤
    │  1 │ # 示例1：定义、全角标点、中英混写          │
    │  2 │                                           │
    │  3 │ 定义 两个数之和(a, b):                     │  ← 编辑区（中文关键字高亮）
    │ ...│                                           │
    ├───────────────────────────────────────────────┤
    │ 你好，世界！                                   │  ← 输出区（stdout + stderr 原样）
    │ 3                                             │
    │ 7                                             │
    ├───────────────────────────────────────────────┤
    │ 示例/示例1.bridge        行 7, 列 12   就绪    │
    └───────────────────────────────────────────────┘

设计要点：

1. **一键运行走的是真命令行**：`python 桥.py 运行 <文件>` 起子进程跑，
   所以编辑器里跑出来的行为 = 你终端里跑出来的行为，不存在"IDE 专用路径"；
2. **未保存也能跑**：内存里的内容先落到 `.运行临时/` 再跑，不用先 Ctrl+S；
3. **高亮复用转译器自己的分段器**（`转译器.主转译器.分段`），
   所以"中文引号里的字不算关键字"这种规则和转译完全一致，不会出现编辑器高亮一套、转译另一套；
4. **停止**会 kill 子进程；输出是流式刷进来的，长循环也能看到实时输出。

快捷键：F5 运行 · Ctrl+S 保存 · Ctrl+O 打开 · Ctrl+E 转译预览 · Esc 停止
"""

from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

项目根 = Path(__file__).resolve().parent.parent
if str(项目根) not in sys.path:
    sys.path.insert(0, str(项目根))

from 转译器 import 编译, 转译, 载入规则, 方言错误  # noqa: E402
from 转译器.主转译器 import 分段  # noqa: E402

临时目录 = 项目根 / '.运行临时'
规则 = 载入规则()
词表 = 规则['词表']
方法表 = 规则['方法']
模块表 = 规则['模块']


def 选区到临时文件(文本: str, 目录: Path) -> Path:
    """把一段选中的代码写成临时 .bridge，返回路径（Ctrl+Enter 试跑选区用）"""
    目录.mkdir(parents=True, exist_ok=True)
    路径 = 目录 / '选区.bridge'
    路径.write_text(文本, encoding='utf-8')
    return 路径


# 侧栏不展示这些目录（缓存、临时产物、别人的东西）
跳过目录 = frozenset({
    '__pycache__', '.git', '.回归', '.运行临时', '.自检临时', '.tmp',
    '.venv', 'node_modules', '.idea', '.vscode', 'docs',
})


def 列出桥文件(根: Path, *, 后缀: tuple[str, ...] = ('.bridge',)) -> list[Path]:
    """递归列出目录下所有 .bridge（以及 .py，方便对照），按路径排序

    转译器就在根目录，所以"子目录里的 .bridge"才是主角：这个列表让编辑器
    不用一个个点开文件夹找。
    """
    根 = Path(根)
    结果: list[Path] = []
    for 路径 in 根.rglob('*'):
        if not 路径.is_file() or 路径.suffix not in 后缀:
            continue
        相对 = 路径.relative_to(根)
        if any(部分 in 跳过目录 for 部分 in 相对.parts[:-1]):
            continue
        结果.append(路径)
    return sorted(结果, key=lambda p: str(p.relative_to(根)).lower())


def 过滤文件(文件们: list[Path], 根: Path, 关键词: str) -> list[Path]:
    """按空格分隔的多个关键词过滤（全部命中才算），不区分大小写"""
    词们 = [w for w in 关键词.strip().lower().split() if w]
    if not 词们:
        return list(文件们)

    def 相对(p: Path) -> str:
        try:
            return str(p.relative_to(根)).replace('\\', '/').lower()
        except ValueError:
            return str(p).replace('\\', '/').lower()

    return [p for p in 文件们 if all(w in 相对(p) for w in 词们)]

汉字 = __import__('re').compile(r'[\u3400-\u9fff]+')
数字 = __import__('re').compile(r'\b\d+(?:\.\d+)?\b')
英文关键字 = __import__('re').compile(
    r'\b(?:def|return|if|elif|else|for|in|while|import|from|as|try|except|finally|'
    r'raise|class|pass|break|continue|global|nonlocal|del|assert|with|yield|async|await|'
    r'True|False|None|and|or|not|is|lambda)\b'
)
英文内建 = __import__('re').compile(
    r'\b(?:print|len|range|max|min|sum|abs|sorted|enumerate|map|filter|zip|any|all|'
    r'int|float|str|bool|list|dict|set|tuple|input|repr|divmod|isinstance|type)\b'
)

配色 = {
    '背景': '#1e1f29',
    '前景': '#e6e6e6',
    '选中': '#3a3d52',
    '行号背景': '#181922',
    '行号前景': '#5f6478',
    '当前行': '#2a2d3d',
    '关键字': '#ff79c6',
    '内建': '#8be9fd',
    '模块': '#50fa7b',
    '方法': '#f1fa8c',
    '字符串': '#f1fa8c',
    '注释': '#6272a4',
    '数字': '#bd93f9',
    '错误': '#ff5555',
    '成功': '#50fa7b',
    '产物': '#8be9fd',
}


def _建悬停表() -> dict[str, str]:
    """中文词 → 它会被翻译成什么（给鼠标悬停用）"""
    表: dict[str, str] = {}
    for 类别 in ('关键字', '内建', '异常', '模块'):
        for 中, 英 in (规则.get(类别) or {}).items():
            表[中] = 英
    for 中, 英 in 方法表.items():
        旧 = 表.get(中)
        表[中] = f'{英}()（点号后）' if not 旧 else f'{旧} ／ {英}()（点号后）'
    for 模块, 成员 in (规则.get('成员') or {}).items():
        for 中, 英 in 成员.items():
            表[f'{模块}.{中}'] = 英
            表.setdefault(中, f'{英}（{模块} 的成员）')
    # 句式糖的引导词：从正则里把开头的汉字抓出来，映射到它会生成的语句
    for 模式, 模板 in (规则.get('语法糖') or []):
        抓 = re.search(r'\^\(\?P<缩进>\[ \\t\]\*\)([\u3400-\u9fff]+)', 模式)
        if 抓:
            表.setdefault(抓.group(1), '句式糖 → ' + 模板.replace('{缩进}', ''))
    # 桥语言独有的语句（不是词表能表达的）
    表.setdefault('标记', '标签：`跳转到 它` 的落点（goto）')
    表.setdefault('标签', '同 `标记`')
    表.setdefault('跳转到', 'goto：跳到某个 `标记`；也可写 `跳转` / `goto`')
    表.setdefault('跳转', '同 `跳转到`')
    表.setdefault('等待完成', '等 `并行` 收尾（桥语言配套函数）')
    return 表


悬停表 = _建悬停表()


def 查映射(词: str) -> str | None:
    """查一个中文词的映射；`数学.圆周率` 和 `圆周率` 都认"""
    if not 词:
        return None
    if 词 in 悬停表:
        return 悬停表[词]
    if '.' in 词:
        前半, 后半 = 词.rsplit('.', 1)
        for 模块名, 成员 in (规则.get('成员') or {}).items():
            if 模块名 in 词 and 后半 in 成员:
                return f'{成员[后半]}'
    return None


def 解析行号(文本: str) -> int | None:
    """从报错行里抠出源码行号：`第 12 行 │ …` / `line 12` / `(xx.bridge, line 3)`"""
    for 模式 in (r'第\s*(\d+)\s*行', r'line\s+(\d+)'):
        匹配 = re.search(模式, 文本, re.I)
        if 匹配:
            return int(匹配.group(1))
    return None


class 桥编辑器:
    def __init__(self, 初始文件: str | None = None) -> None:
        self.根 = tk.Tk()
        self.根.title('桥语言编辑器')
        self.根.geometry('1080x720')
        self.根.minsize(680, 420)

        self.路径: Path | None = None
        self.脏 = False
        self.进程: subprocess.Popen | None = None
        self.输出队列: queue.Queue = queue.Queue()
        self.运行中 = False
        self.字号 = 12
        self.断点: set[int] = set()
        self.断点表: dict[str, set[int]] = {}   # 每个文件各自的断点
        self._断点文件 = ''
        self.自动保存 = True                    # 停手 1.2 秒自动存
        self._自动保存任务 = None

        self._建界面()
        self._绑定()
        if 初始文件:
            self.打开(Path(初始文件))
        else:
            self._填充欢迎示例()
        self.根.after(300, self.高亮)

    # ------------------------------------------------------------------ 界面
    def _建界面(self) -> None:
        self.根.configure(bg=配色['背景'])

        工具栏 = tk.Frame(self.根, bg=配色['背景'])
        工具栏.pack(side='top', fill='x', padx=8, pady=(8, 4))

        def 按钮(文字, 命令):
            b = tk.Button(
                工具栏, text=文字, command=命令, bd=0, relief='flat',
                bg='#2f3242', fg=配色['前景'], activebackground='#3d4157',
                activeforeground='#ffffff', padx=12, pady=5, cursor='hand2',
                font=('Microsoft YaHei UI', 10),
            )
            b.pack(side='left', padx=(0, 6))
            return b

        按钮('打开', self.打开)
        按钮('保存', self.保存)
        按钮('另存为', self.另存为)
        tk.Frame(工具栏, width=12, bg=配色['背景']).pack(side='left')
        按钮('▶ 运行', self.运行)
        按钮('🐞 调试', self.调试运行)
        按钮('格式化', self.格式化文档)
        按钮('试跑选区', self.试跑选区)
        按钮('■ 停止', self.停止)
        按钮('转译预览', self.预览转译)
        按钮('清空输出', self.清空输出)

        # ---- 状态栏：必须比 expand 的分栏先 pack，否则会被挤成 1 像素
        状态 = tk.Frame(self.根, bg='#181922')
        状态.pack(side='bottom', fill='x')
        self.状态文件 = tk.Label(状态, text='未命名', anchor='w', bg='#181922',
                              fg=配色['行号前景'], font=('Microsoft YaHei UI', 9), padx=10, pady=4)
        self.状态文件.pack(side='left')
        self.状态状态 = tk.Label(状态, text='就绪', anchor='e', bg='#181922',
                              fg=配色['成功'], font=('Microsoft YaHei UI', 9), padx=10, pady=4)
        self.状态状态.pack(side='right')
        self.状态光标 = tk.Label(状态, text='行 1, 列 1', anchor='e', bg='#181922',
                              fg=配色['行号前景'], font=('Microsoft YaHei UI', 9), padx=10, pady=4)
        self.状态光标.pack(side='right')

        # ---- 分割：左（文件树） + 右（编辑区 / 输出区）
        外栏 = ttk.Panedwindow(self.根, orient='horizontal')
        外栏.pack(fill='both', expand=True, padx=8, pady=(0, 4))
        self.外栏 = 外栏

        # 左侧文件树：列出子目录下所有 .bridge，双击即开
        侧栏 = tk.Frame(外栏, bg=配色['背景'])
        侧栏头 = tk.Frame(侧栏, bg=配色['背景'])
        侧栏头.pack(side='top', fill='x')
        tk.Label(
            侧栏头, text='桥文件', anchor='w', bg=配色['背景'], fg=配色['行号前景'],
            font=('Microsoft YaHei UI', 9), padx=4,
        ).pack(side='left')
        tk.Button(
            侧栏头, text='刷新', command=self.刷新文件树, bd=0, relief='flat',
            bg='#2f3242', fg=配色['前景'], activebackground='#3d4157',
            activeforeground='#ffffff', padx=6, pady=1, cursor='hand2',
            font=('Microsoft YaHei UI', 8),
        ).pack(side='right', padx=2)
        搜索框 = tk.Frame(侧栏, bg=配色['背景'])
        搜索框.pack(side='top', fill='x', padx=2, pady=(2, 0))
        tk.Label(搜索框, text='搜', bg=配色['背景'], fg=配色['注释'],
                 font=('Microsoft YaHei UI', 8)).pack(side='left')
        self.树搜索 = tk.Entry(
            搜索框, bg='#2f3242', fg=配色['前景'], insertbackground=配色['前景'],
            bd=0, relief='flat', font=('Microsoft YaHei UI', 9),
        )
        self.树搜索.pack(side='left', fill='x', expand=True, padx=(2, 0))
        self.树搜索.bind('<KeyRelease>', lambda e: self.刷新文件树())
        self.树搜索.bind('<Escape>', lambda e: (self.树搜索.delete(0, 'end'),
                                                self.刷新文件树()))
        tk.Label(
            侧栏, text='双击打开 · Ctrl+P 快速跳', anchor='w', bg=配色['背景'],
            fg=配色['注释'], font=('Microsoft YaHei UI', 8), padx=4,
        ).pack(side='top', fill='x')

        样式 = ttk.Style(self.根)
        try:
            样式.theme_use('clam')
        except tk.TclError:
            pass
        样式.configure('Treeview', background=配色['行号背景'],
                       fieldbackground=配色['行号背景'], foreground=配色['前景'],
                       borderwidth=0, rowheight=20)
        样式.map('Treeview', background=[('selected', 配色['选中'])],
                 foreground=[('selected', '#ffffff')])
        样式.configure('Sash', sashthickness=6)

        树框 = tk.Frame(侧栏, bg=配色['背景'])
        树框.pack(side='top', fill='both', expand=True)
        self.文件树 = ttk.Treeview(树框, show='tree', selectmode='browse')
        树滚动 = tk.Scrollbar(树框, command=self.文件树.yview, width=10)
        self.文件树.configure(yscrollcommand=树滚动.set)
        self.文件树.pack(side='left', fill='both', expand=True)
        树滚动.pack(side='right', fill='y')
        self.文件树.tag_configure('目录', foreground=配色['模块'])
        self.文件树.tag_configure('当前', foreground=配色['成功'])
        self.文件树.bind('<Double-Button-1>', self._树双击)
        self.文件树.bind('<Return>', self._树双击)
        self.侧栏 = 侧栏
        外栏.add(侧栏, weight=1)

        # ---- 分割：编辑区 / 输出区（用 ttk.Panedwindow，按 weight 分配，不会被内容撑破）
        分栏 = ttk.Panedwindow(外栏, orient='vertical')
        外栏.add(分栏, weight=6)

        # 编辑区（行号 + 正文）
        编辑框 = tk.Frame(分栏, bg=配色['背景'])
        self.行号 = tk.Text(
            编辑框, width=5, padx=6, takefocus=0, bd=0, relief='flat',
            bg=配色['行号背景'], fg=配色['行号前景'], font=('Consolas', self.字号),
            state='disabled', cursor='arrow',
        )
        self.行号.pack(side='left', fill='y')

        self.编辑区 = tk.Text(
            编辑框, wrap='none', undo=True, bd=0, relief='flat',
            bg=配色['背景'], fg=配色['前景'], insertbackground=配色['关键字'],
            insertwidth=2, selectbackground=配色['选中'], selectforeground='#ffffff',
            font=('Consolas', self.字号), padx=8, pady=6,
        )
        self.编辑区.pack(side='left', fill='both', expand=True)

        编辑滚动 = tk.Scrollbar(编辑框, command=self.编辑区.yview, width=12)
        编辑滚动.pack(side='right', fill='y')
        self.编辑区.configure(yscrollcommand=self._编辑滚动)
        分栏.add(编辑框, weight=3)

        # 输出区
        输出框 = tk.Frame(分栏, bg=配色['背景'])
        self.输出标题 = tk.Label(
            输出框, text='输出  ·  点带“第 N 行”的报错可直接跳到源码行', anchor='w',
            bg=配色['背景'], fg=配色['行号前景'],
            font=('Microsoft YaHei UI', 9), padx=4,
        )
        self.输出标题.pack(side='top', fill='x')
        self.输出区 = tk.Text(
            输出框, height=6, wrap='word', bd=0, relief='flat',
            bg=配色['行号背景'], fg=配色['前景'], font=('Consolas', self.字号 - 1),
            padx=8, pady=6, state='disabled',
        )
        self.输出区.pack(side='left', fill='both', expand=True)
        命令栏 = tk.Frame(输出框, bg=配色['背景'])
        命令栏.pack(side='bottom', fill='x')
        tk.Label(命令栏, text='输入（回车发送）', bg=配色['背景'], fg=配色['注释'],
                 font=('Microsoft YaHei UI', 8), padx=4).pack(side='left')
        self.调试命令框 = tk.Entry(
            命令栏, bg='#2f3242', fg=配色['前景'], insertbackground=配色['前景'],
            bd=0, relief='flat', font=('Consolas', self.字号 - 1),
        )
        self.调试命令框.pack(side='left', fill='x', expand=True, padx=(0, 4), pady=2)
        self.调试命令框.bind('<Return>', self.发送调试命令)
        tk.Button(
            命令栏, text='发送', command=self.发送调试命令, bd=0, relief='flat',
            bg='#2f3242', fg=配色['前景'], activebackground='#3d4157',
            activeforeground='#ffffff', padx=6, cursor='hand2',
            font=('Microsoft YaHei UI', 8),
        ).pack(side='right', padx=(0, 4))
        输出滚动 = tk.Scrollbar(输出框, command=self.输出区.yview, width=12)
        输出滚动.pack(side='right', fill='y')
        self.输出区.configure(yscrollcommand=输出滚动.set)
        分栏.add(输出框, weight=1)

        # 标签
        配置 = self.编辑区
        配置.tag_configure('关键字', foreground=配色['关键字'])
        配置.tag_configure('内建', foreground=配色['内建'])
        配置.tag_configure('模块', foreground=配色['模块'])
        配置.tag_configure('方法', foreground=配色['方法'])
        配置.tag_configure('字符串', foreground=配色['字符串'])
        配置.tag_configure('注释', foreground=配色['注释'], font=('Consolas', self.字号, 'italic'))
        配置.tag_configure('数字', foreground=配色['数字'])
        配置.tag_configure('当前行', background=配色['当前行'])
        配置.tag_configure('错误行', background='#4a2626', underline=True)
        配置.tag_configure('断点行', background='#4a2f2f')
        配置.tag_configure('断点行', underline=True)
        配置.tag_configure('悬停', underline=True)
        配置.tag_lower('当前行')
        配置.tag_lower('错误行')

        self.输出区.tag_configure('错误', foreground=配色['错误'])
        self.输出区.tag_configure('成功', foreground=配色['成功'])
        self.输出区.tag_configure('产物', foreground=配色['产物'])
        self.输出区.tag_configure('提示', foreground=配色['行号前景'])

        self.刷新文件树()

    # ---------------------------------------------------------------- 文件树
    def 刷新文件树(self) -> None:
        """重建左侧树：子目录里的 .bridge 全列出来（默认根是桥语言目录）"""
        树 = getattr(self, '文件树', None)
        if 树 is None:
            return
        根 = 项目根
        for 项 in 树.get_children(''):
            树.delete(项)
        全部 = 列出桥文件(根)
        词 = self.树搜索.get().strip() if hasattr(self, '树搜索') else ''
        self.文件路径们 = 过滤文件(全部, 根, 词) if 词 else 全部
        已建目录: set[str] = set()
        for 路径 in self.文件路径们:
            相对 = 路径.relative_to(根)
            上级 = ''
            for 段 in 相对.parts[:-1]:
                标识 = f'{上级}/{段}' if 上级 else 段
                if 标识 not in 已建目录:
                    树.insert(上级, 'end', iid=标识, text=段, open=True, tags=('目录',))
                    已建目录.add(标识)
                上级 = 标识
            名 = 相对.parts[-1]
            标记 = '  ' if 路径.suffix == '.bridge' else '  ·'
            树.insert(上级, 'end', iid=str(路径), text=f'{标记}{名}')
        self._选中当前文件()

    def _选中当前文件(self) -> None:
        树 = getattr(self, '文件树', None)
        if 树 is None or self.路径 is None:
            return
        标识 = str(self.路径)
        if 树.exists(标识):
            树.selection_set(标识)
            树.see(标识)

    def _树双击(self, 事件=None):
        树 = self.文件树
        选中 = 树.selection()
        if not 选中:
            return 'break'
        标识 = 选中[0]
        if '目录' in 树.item(标识, 'tags'):
            树.item(标识, open=not 树.item(标识, 'open'))
            return 'break'
        路径 = Path(标识)
        if 路径.is_file():
            self.打开(路径)
        return 'break'

    def 快速打开(self) -> None:
        """Ctrl+P：输入几个字就能跳到子目录里的任意 .bridge"""
        根 = 项目根
        文件们 = getattr(self, '文件路径们', None) or 列出桥文件(根)
        窗口 = tk.Toplevel(self.根)
        窗口.title('快速打开（Ctrl+P）')
        窗口.configure(bg=配色['背景'])
        窗口.geometry('640x420+180+120')
        窗口.transient(self.根)

        输入 = tk.Entry(
            窗口, bg='#2f3242', fg=配色['前景'], insertbackground=配色['前景'],
            bd=0, relief='flat', font=('Microsoft YaHei UI', 11),
        )
        输入.pack(fill='x', padx=8, pady=8)
        列表 = tk.Listbox(
            窗口, bg=配色['行号背景'], fg=配色['前景'], bd=0, relief='flat',
            font=('Consolas', 10), selectbackground=配色['选中'],
            selectforeground='#ffffff', activestyle='none',
        )
        列表.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        当前: list[Path] = []

        def 重填(*_):
            非文本 = 输入.get()
            当前.clear()
            当前.extend(过滤文件(文件们, 根, 非文本)[:200])
            列表.delete(0, 'end')
            for 路径 in 当前:
                try:
                    相对 = 路径.relative_to(根)
                except ValueError:
                    相对 = 路径
                列表.insert('end', str(相对).replace('\\', '/'))
            if 当前:
                列表.selection_set(0)

        def 打开选中(*_):
            选中 = 列表.curselection()
            if not 选中:
                return
            目标 = 当前[选中[0]]
            窗口.destroy()
            self.打开(目标)

        输入.bind('<KeyRelease>', 重填)
        输入.bind('<Return>', 打开选中)
        输入.bind('<Escape>', lambda e: 窗口.destroy())
        列表.bind('<Double-Button-1>', 打开选中)
        列表.bind('<Return>', 打开选中)
        重填()
        输入.focus_set()
        窗口.grab_set()

    def 切换侧栏(self):
        """Ctrl+B：收起/展开左侧文件树"""
        外栏 = getattr(self, '外栏', None)
        if 外栏 is None:
            return 'break'
        已显示 = str(self.侧栏) in {str(p) for p in 外栏.panes()}
        if 已显示:
            外栏.forget(self.侧栏)
        else:
            外栏.insert(0, self.侧栏, weight=1)
        return 'break'

    def _填充欢迎示例(self) -> None:
        示例 = 项目根 / '示例' / '示例1.bridge'
        内容 = 示例.read_text(encoding='utf-8-sig') if 示例.is_file() else (
            '# 新建 .bridge 文件，F5 运行\n\n'
            '函数 打招呼(名字):\n'
            '    如果 名字:\n'
            '        输出（“你好，” ＋ 名字）\n'
            '    否则:\n'
            '        输出（“你好，陌生人”）\n\n'
            '对于 i 在 范围(3):\n'
            '    打招呼（“爸爸” ＋ 字符串(i)）\n'
        )
        self.编辑区.insert('1.0', 内容)
        self.编辑区.edit_modified(False)
        if 示例.is_file():
            self.路径 = 示例
            self._刷新标题()
        self.更新行号()

    # ------------------------------------------------------------------ 绑定
    def _绑定(self) -> None:
        self.编辑区.bind('<KeyRelease>', self._按键)
        self.编辑区.bind('<ButtonRelease-1>', self._按键)
        self.编辑区.bind('<<Modified>>', self._改动)
        self.编辑区.bind('<Control-Return>', lambda e: self.试跑选区())
        self.编辑区.bind('<Control-KP_Enter>', lambda e: self.试跑选区())
        self.编辑区.bind('<Control-s>', lambda e: self.保存())
        self.编辑区.bind('<Control-S>', lambda e: self.另存为())
        self.编辑区.bind('<Control-o>', lambda e: self.打开())
        self.编辑区.bind('<Control-p>', lambda e: self.快速打开())
        self.编辑区.bind('<Control-b>', lambda e: self.切换侧栏())
        self.根.bind('<Control-p>', lambda e: self.快速打开())
        self.根.bind('<Control-b>', lambda e: self.切换侧栏())
        self.编辑区.bind('<Control-e>', lambda e: self.预览转译())
        self.编辑区.bind('<Control-MouseWheel>', self._缩放)
        self.编辑区.bind('<Control-equal>', lambda e: self._缩放(缩放=1))
        self.编辑区.bind('<Control-minus>', lambda e: self._缩放(缩放=-1))
        self.根.bind('<F5>', lambda e: self.运行())
        self.根.bind('<F9>', lambda e: self.切换断点())
        self.根.bind('<Control-F5>', lambda e: self.调试运行())
        self.根.bind('<Control-Shift-F5>', lambda e: self.外部终端运行())
        self.根.bind('<Control-Shift-F>', lambda e: self.格式化文档())
        self.编辑区.bind('<F9>', lambda e: self.切换断点())
        self.编辑区.bind('<Control-F5>', lambda e: self.调试运行())
        self.根.bind('<Escape>', lambda e: self.停止())
        self.根.protocol('WM_DELETE_WINDOW', self.退出)
        # 输出区点一下 → 跳到报错行；编辑区悬停 → 看映射
        self.输出区.bind('<Double-Button-1>', self._点击输出)
        self.输出区.bind('<Control-c>', self._复制选中)
        self.输出区.bind('<Button-3>', self._输出菜单)
        self.编辑区.bind('<Motion>', self._悬停)
        self.编辑区.bind('<Leave>', lambda e: self._藏提示())
        self.编辑区.bind('<KeyPress>', lambda e: self._藏提示())

    def _编辑滚动(self, 首, 尾):
        self.编辑区.yview_moveto(首)
        self.行号.yview_moveto(首)

    def _缩放(self, 事件=None, 缩放: int = 0):
        if 事件 is not None:
            缩放 = 1 if 事件.delta > 0 else -1
        self.字号 = max(8, min(28, self.字号 + 缩放))
        self.编辑区.configure(font=('Consolas', self.字号))
        self.行号.configure(font=('Consolas', self.字号))
        self.输出区.configure(font=('Consolas', max(8, self.字号 - 1)))
        self.更新行号()
        self.高亮()
        return 'break'

    def _按键(self, 事件=None):
        self.更新行号()
        self.更新光标()
        self._安排高亮()
        return None

    def _改动(self, 事件=None):
        if self.编辑区.edit_modified():
            self.脏 = True
            self._刷新标题()
            self.编辑区.edit_modified(False)
            self._安排自动保存()
        return None

    def _安排自动保存(self) -> None:
        if not self.自动保存 or self.路径 is None:
            return
        if self._自动保存任务:
            self.根.after_cancel(self._自动保存任务)
        self._自动保存任务 = self.根.after(1200, self._自动保存)

    def _自动保存(self) -> None:
        self._自动保存任务 = None
        if self.自动保存 and self.脏 and self.路径 is not None:
            self.保存()

    def _安排高亮(self) -> None:
        if getattr(self, '_高亮任务', None):
            self.根.after_cancel(self._高亮任务)
        self._高亮任务 = self.根.after(120, self.高亮)

    # ------------------------------------------------------------------ 高亮
    def _偏移到索引(self, 偏移: int) -> str:
        return self.编辑区.index(f'1.0 + {偏移}c')

    def 高亮(self) -> None:
        self._高亮任务 = None
        区 = self.编辑区
        for 标签 in ('关键字', '内建', '模块', '方法', '字符串', '注释', '数字'):
            区.tag_remove(标签, '1.0', 'end')

        源码 = 区.get('1.0', 'end-1c')
        偏移 = 0
        for 种类, 文本 in 分段(源码):
            起 = 偏移
            偏移 += len(文本)
            if 种类 == '注释':
                区.tag_add('注释', self._偏移到索引(起), self._偏移到索引(偏移))
                continue
            if 种类 in ('字符串', '中文引号'):
                区.tag_add('字符串', self._偏移到索引(起), self._偏移到索引(偏移))
                continue

            # 代码段：逐类打标签
            for 匹配 in 汉字.finditer(文本):
                词 = 匹配.group(0)
                标签 = None
                if 词 in 方法表:
                    标签 = '方法'
                elif 词 in 模块表:
                    标签 = '模块'
                elif 词 in 词表:
                    标签 = '关键字' if 词 in 规则['关键字'] else '内建'
                if 标签:
                    区.tag_add(标签, self._偏移到索引(起 + 匹配.start()),
                              self._偏移到索引(起 + 匹配.end()))
            for 匹配 in 英文关键字.finditer(文本):
                区.tag_add('关键字', self._偏移到索引(起 + 匹配.start()),
                          self._偏移到索引(起 + 匹配.end()))
            for 匹配 in 英文内建.finditer(文本):
                区.tag_add('内建', self._偏移到索引(起 + 匹配.start()),
                          self._偏移到索引(起 + 匹配.end()))
            for 匹配 in 数字.finditer(文本):
                区.tag_add('数字', self._偏移到索引(起 + 匹配.start()),
                          self._偏移到索引(起 + 匹配.end()))

        self.高亮当前行()

    def 高亮当前行(self) -> None:
        self.编辑区.tag_remove('当前行', '1.0', 'end')
        行 = self.编辑区.index('insert').split('.')[0]
        self.编辑区.tag_add('当前行', f'{行}.0', f'{行}.end+1c')

    # ------------------------------------------------------------------ 行号 / 状态
    def 更新行号(self) -> None:
        总行 = int(self.编辑区.index('end-1c').split('.')[0])
        self.行号.configure(state='normal')
        self.行号.delete('1.0', 'end')
        self.行号.insert('1.0', '\n'.join(str(i) for i in range(1, 总行 + 1)))
        self.行号.configure(state='disabled')
        self.行号.yview_moveto(self.编辑区.yview()[0])

    def 更新光标(self) -> None:
        行, 列 = self.编辑区.index('insert').split('.')
        self.状态光标.configure(text=f'行 {行}, 列 {int(列) + 1}')

    def _刷新标题(self) -> None:
        名 = self.路径.name if self.路径 else '未命名.bridge'
        self.根.title(f'{"*" if self.脏 else ""}桥语言编辑器 · {名}')
        self.状态文件.configure(text=str(self.路径) if self.路径 else '未命名.bridge（未保存）')

    def _置状态(self, 文本: str, 颜色: str | None = None) -> None:
        self.状态状态.configure(text=文本, fg=颜色 or 配色['成功'])

    # ------------------------------------------------------------------ 文件
    def 打开(self, 路径: Path | None = None) -> None:
        if self.运行中 and not messagebox.askyesno('还在运行', '运行还没结束，先停掉再打开？'):
            return
        self.停止()
        if 路径 is None:
            初始 = 示例目录 if (示例目录 := 项目根 / '示例').is_dir() else 项目根
            选择 = filedialog.askopenfilename(
                title='打开 .bridge 文件',
                initialdir=str(初始),
                filetypes=[('桥语言源码', '*.bridge'), ('Python 源码', '*.py'), ('全部文件', '*.*')],
            )
            if not 选择:
                return
            路径 = Path(选择)
        try:
            内容 = 路径.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
        except OSError as 错误:
            messagebox.showerror('打开失败', str(错误))
            return
        self.编辑区.delete('1.0', 'end')
        self.编辑区.insert('1.0', 内容)
        self.编辑区.edit_modified(False)
        self.路径 = Path(路径)
        self.脏 = False
        旧文件 = str(getattr(self, '_断点文件', ''))
        if 旧文件 and 旧文件 != str(self.路径):
            self.断点表[旧文件] = set(self.断点)      # 存下上一个文件的断点
        self._断点文件 = str(self.路径)
        self.断点 = set(self.断点表.get(str(self.路径), set()))
        self._重画断点()
        self._刷新标题()
        self.更新行号()
        self.高亮()
        self._置状态(f'已打开 {self.路径.name}')
        for 项 in self.文件树.get_children(''):
            self.文件树.item(项, open=True)
        self._选中当前文件()

    def 保存(self) -> bool:
        if self.路径 is None:
            return self.另存为()
        try:
            self.路径.write_text(self.编辑区.get('1.0', 'end-1c'), encoding='utf-8')
        except OSError as 错误:
            messagebox.showerror('保存失败', str(错误))
            return False
        self.脏 = False
        self._刷新标题()
        self._置状态(f'已保存 {self.路径.name}')
        self._保存时检查()
        return True

    def 另存为(self) -> bool:
        选择 = filedialog.asksaveasfilename(
            title='另存为', defaultextension='.bridge',
            initialfile=self.路径.name if self.路径 else '未命名.bridge',
            filetypes=[('桥语言源码', '*.bridge'), ('Python 源码', '*.py')],
        )
        if not 选择:
            return False
        self.路径 = Path(选择)
        return self.保存()


    def 格式化文档(self):
        """Tab→4 空格、去行尾空白、结尾留一个换行（不改结构，只清脏东西）"""
        原文 = self.编辑区.get('1.0', 'end-1c')
        行们 = [行.expandtabs(4).rstrip() for 行 in 原文.splitlines()]
        新文 = '\n'.join(行们) + '\n'
        if 新文 == 原文 + ('\n' if not 原文.endswith('\n') else ''):
            self._置状态('格式已经很干净')
            return 'break'
        位置 = self.编辑区.index('insert')
        self.编辑区.delete('1.0', 'end')
        self.编辑区.insert('1.0', 新文)
        self.编辑区.mark_set('insert', 位置)
        self.脏 = True
        self._刷新标题()
        self._置状态('已格式化（Tab→4 空格，去行尾空白）', 配色['成功'])
        return 'break'

    # ------------------------------------------------------------------ 调试
    def 切换断点(self):
        """F9：在当前行打/取消断点"""
        行 = int(self.编辑区.index('insert').split('.')[0])
        if 行 in self.断点:
            self.断点.discard(行)
            self._置状态(f'取消断点 第 {行} 行')
        else:
            self.断点.add(行)
            self._置状态(f'断点 第 {行} 行（Ctrl+F5 调试运行）')
        if self.路径 is not None:
            self.断点表[str(self.路径)] = set(self.断点)
        self._重画断点()
        return 'break'

    def _重画断点(self) -> None:
        self.编辑区.tag_remove('断点行', '1.0', 'end')
        for 行 in sorted(self.断点):
            self.编辑区.tag_add('断点行', f'{行}.0', f'{行}.end+1c')

    def _标行(self, 行号: int, 断点: bool = False) -> None:
        标签 = '断点行' if 断点 else '错误行'
        try:
            self.编辑区.tag_add(标签, f'{行号}.0', f'{行号}.end+1c')
            self.编辑区.see(f'{行号}.0')
        except tk.TclError:
            pass

    def 外部终端运行(self):
        """Ctrl+Shift+F5：开一个真终端窗口跑（需要 TTY 的程序用这个）"""
        目标 = self._运行文件()
        if 目标 is None:
            return
        命令 = f'"{sys.executable}" "{项目根 / "桥.py"}" 运行 "{目标}"; echo.; pause'
        创建标志 = getattr(subprocess, 'CREATE_NEW_CONSOLE', 0) if os.name == 'nt' else 0
        try:
            if os.name == 'nt':
                subprocess.Popen(['cmd', '/c', 命令], cwd=str(项目根),
                                 creationflags=创建标志)
            else:
                subprocess.Popen(
                    ['x-terminal-emulator' if os.name != 'darwin' else 'open',
                     '-e', 'bash', '-c', 命令], cwd=str(项目根))
        except OSError as 错误:
            self._置状态(f'开终端失败：{错误}', 配色['错误'])
            return
        self._置状态('已在外部终端运行（输出不在编辑器里）', 配色['内建'])

    def 调试运行(self):
        """Ctrl+F5：按断点调试；没有断点就停在第 1 行"""
        if self.运行中:
            self._置状态('还在跑，先按 Esc 停下', 配色['错误'])
            return
        目标 = self._运行文件()
        if 目标 is None:
            return
        self._启动(目标, 说明='调试', 调试=True)
        self._置状态('调试中：在下面「调试命令」里敲 n / c / p 变量 / l / q',
                    配色['内建'])
        try:
            self.调试命令框.focus_set()
        except tk.TclError:
            pass

    def 发送调试命令(self, 事件=None):
        """把输入框里的一行送进子进程 stdin（运行中输入、调试时敲命令都走这里）"""
        if not self.进程 or not self.进程.stdin:
            self._置状态('没有在跑的程序（先 F5 或 Ctrl+F5）', 配色['错误'])
            return 'break'
        命令 = self.调试命令框.get()
        self.调试命令框.delete(0, 'end')
        try:
            self.进程.stdin.write((命令 + '\n').encode('utf-8'))
            self.进程.stdin.flush()
            已有 = self.输出区.get('1.0', 'end-1c')
            if 已有 and not 已有.endswith('\n'):
                self._写输出('\n', '提示')      # 提示符没换行，先断行再回显
            self._写输出(f'你输入：{命令}\n', '提示')
        except (OSError, ValueError) as 错误:
            self._置状态(f'发送失败：{错误}', 配色['错误'])
        return 'break'

    def _复制选中(self, 事件=None):
        """Ctrl+C：复制输出区的选区"""
        try:
            选中 = self.输出区.get('sel.first', 'sel.last')
        except tk.TclError:
            return 'break'
        self.根.clipboard_clear()
        self.根.clipboard_append(选中)
        self._置状态(f'已复制 {len(选中)} 个字符', 配色['成功'])
        return 'break'

    def _输出菜单(self, 事件):
        """右键菜单：复制 / 全选 / 粘贴并发送 / 清空"""
        菜单 = tk.Menu(self.根, tearoff=0, bg='#2f3242', fg=配色['前景'],
                      activebackground='#3d4157', activeforeground='#ffffff')
        菜单.add_command(label='复制', command=lambda: self._复制选中())
        菜单.add_command(label='全选', command=lambda: self.输出区.tag_add(
            'sel', '1.0', 'end'))
        菜单.add_command(label='粘贴并发送',
                         command=lambda: self._粘贴并发送())
        菜单.add_separator()
        菜单.add_command(label='清空输出', command=self.清空输出)
        try:
            菜单.tk_popup(事件.x_root, 事件.y_root)
        finally:
            菜单.grab_release()

    def _粘贴并发送(self):
        try:
            内容 = self.根.clipboard_get()
        except tk.TclError:
            return
        for 行 in 内容.splitlines() or ['']:
            self.调试命令框.delete(0, 'end')
            self.调试命令框.insert(0, 行)
            self.发送调试命令()

    def _保存时检查(self) -> None:
        """保存后顺手编译一下：有语法错误就标红，但**不阻止保存**"""
        if self.路径 is None:
            return
        try:
            编译(self.编辑区.get('1.0', 'end-1c'), str(self.路径))
        except 方言错误 as 错误:
            行号 = getattr(错误, '行号', None)
            if 行号:
                self._标行(行号)
            self._置状态(f'保存了，但第 {行号} 行有错：{str(错误)[:40]}', 配色['错误'])
        except Exception:                     # noqa: BLE001
            pass

    # ------------------------------------------------------------------ 运行
    def _运行文件(self) -> Path | None:
        """当前要跑的文件：已保存且没改动就直接跑原文件，否则落一个临时副本"""
        内容 = self.编辑区.get('1.0', 'end-1c')
        if self.路径 is not None and not self.脏:
            return self.路径
        临时目录.mkdir(exist_ok=True)
        名 = (self.路径.name if self.路径 else '未命名.bridge')
        if not 名.endswith(('.bridge', '.py')):
            名 += '.bridge'
        临时 = 临时目录 / 名
        try:
            临时.write_text(内容, encoding='utf-8')
        except OSError as 错误:
            messagebox.showerror('无法写临时文件', str(错误))
            return None
        return 临时

    def 运行(self) -> None:
        目标 = self._运行文件()
        if 目标 is not None:
            self._启动(目标)

    def 试跑选区(self) -> None:
        """选中一段跑一段（没选中就跑当前行）——改一行试一行，不用整文件跑"""
        文本 = ''
        try:
            文本 = self.编辑区.get('sel.first', 'sel.last')
        except tk.TclError:
            行 = self.编辑区.index('insert').split('.')[0]
            文本 = self.编辑区.get(f'{行}.0', f'{行}.end')
        if not 文本.strip():
            self._置状态('没有选中任何内容', 配色['错误'])
            return
        try:
            临时 = 选区到临时文件(文本, 临时目录)
        except OSError as 错误:
            messagebox.showerror('无法写临时文件', str(错误))
            return
        self._置状态('试跑选区…', 配色['内建'])
        self._启动(临时, 说明='选区')

    def _启动(self, 目标: Path, 说明: str = '', 调试: bool = False) -> None:
        if self.运行中:
            self._置状态('还在跑，先按 Esc 停下', 配色['错误'])
            return
        if 目标.suffix == '.py':
            命令 = [sys.executable, str(目标)]
        elif 调试:
            断点参数 = ','.join(str(n) for n in sorted(self.断点)) or '1'
            命令 = [sys.executable, str(项目根 / '桥.py'), '调试', str(目标),
                    '--断点', 断点参数]
        else:
            命令 = [sys.executable, str(项目根 / '桥.py'), '运行', str(目标)]

        环境 = os.environ.copy()
        环境['PYTHONIOENCODING'] = 'utf-8'
        环境['PYTHONUTF8'] = '1'

        # 子进程不要弹黑窗：输出全靠管道回传，控制台窗口纯属噪音
        创建标志 = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0

        self.清空输出()
        if 说明:
            self._写输出(f'（{说明}试跑）\n', '提示')
        self._写输出(f'$ {" ".join(命令)}\n\n', '提示')
        try:
            self.进程 = subprocess.Popen(
                命令, cwd=str(项目根), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE, bufsize=0, env=环境,
                creationflags=创建标志,
            )
        except OSError as 错误:
            self._写输出(f'启动失败：{错误}\n', '错误')
            return

        self.运行中 = True
        self._置状态('运行中…', 配色['内建'])
        threading.Thread(target=self._读输出, args=(self.进程,), daemon=True).start()
        self.根.after(40, self._收输出)

    def _读输出(self, 进程: subprocess.Popen) -> None:
        """按字节块读：程序打印 `提示：`（没有换行）时也能立刻显示出来"""
        import codecs
        import os as _os

        解码 = codecs.getincrementaldecoder('utf-8')('replace')
        文件号 = 进程.stdout.fileno()
        try:
            while True:
                块 = _os.read(文件号, 4096)
                if not 块:
                    break
                文本 = 解码.decode(块)
                if 文本:
                    self.输出队列.put(('行', 文本))
            尾巴 = 解码.decode(b'', final=True)
            if 尾巴:
                self.输出队列.put(('行', 尾巴))
        except (OSError, ValueError):
            pass
        finally:
            self.输出队列.put(('结束', 进程.wait()))

    def _收输出(self) -> None:
        while True:
            try:
                种类, 值 = self.输出队列.get_nowait()
            except queue.Empty:
                break
            if 种类 == '行':
                标签 = '错误' if any(k in 值 for k in ('Error', 'Traceback', '错误', '失败')) else None
                self._写输出(值, 标签)
                命中 = re.search(r'第\s*(\d+)\s*行', 值)
                if 命中:
                    行号 = int(命中.group(1))
                    self._标行(行号, 断点=('●' in 值))
            else:
                self.运行中 = False
                self.进程 = None
                if 值 == 0:
                    self._置状态('运行结束（退出码 0）', 配色['成功'])
                    self._写输出('\n[退出码 0]\n', '成功')
                else:
                    self._置状态(f'运行结束（退出码 {值}）', 配色['错误'])
                    self._写输出(f'\n[退出码 {值}]\n', '错误')
        if self.运行中:
            self.根.after(40, self._收输出)

    def 停止(self) -> None:
        if self.进程 and self.进程.poll() is None:
            try:
                self.进程.kill()
            except OSError:
                pass
            self._置状态('已停止', 配色['错误'])
            self._写输出('\n[已手动停止]\n', '错误')
        self.运行中 = False
        self.进程 = None

    # ------------------------------------------------------------------ 输出
    def _写输出(self, 文本: str, 标签: str | None = None) -> None:
        区 = self.输出区
        区.configure(state='normal')
        区.insert('end', 文本, (标签,) if 标签 else ())
        区.see('end')
        区.configure(state='disabled')

    def 清空输出(self) -> None:
        self.输出区.configure(state='normal')
        self.输出区.delete('1.0', 'end')
        self.输出区.configure(state='disabled')

    def 预览转译(self) -> None:
        源码 = self.编辑区.get('1.0', 'end-1c')
        self.清空输出()
        try:
            产物 = 转译(源码)
        except SyntaxError as 错误:
            self._写输出(f'转译失败：{错误}\n', '错误')
            return
        行号 = '\n'.join(f'{i:>3} │ {行}' for i, 行 in enumerate(产物.splitlines(), 1))
        self._写输出('== 转译产物（标准 Python）==\n', '产物')
        self._写输出(行号 + '\n', '产物')
        self._置状态('已生成转译预览', 配色['内建'])

    # ------------------------------------------------------------------ 报错跳行
    def 跳转行(self, 行号: int, 高亮毫秒: int = 2000) -> None:
        行号 = max(1, 行号)
        self.编辑区.mark_set('insert', f'{行号}.0')
        self.编辑区.see(f'{行号}.0')
        self.编辑区.tag_remove('错误行', '1.0', 'end')
        self.编辑区.tag_add('错误行', f'{行号}.0', f'{行号}.end+1c')
        self.编辑区.focus_set()
        self.更新光标()
        self.根.after(高亮毫秒, lambda: self.编辑区.tag_remove('错误行', '1.0', 'end'))

    def _点击输出(self, 事件) -> None:
        索引 = self.输出区.index(f'@{事件.x},{事件.y}')
        行 = int(索引.split('.')[0])
        文本 = self.输出区.get(f'{行}.0', f'{行}.end')
        行号 = 解析行号(文本)
        if 行号:
            self.跳转行(行号)
            self._置状态(f'已跳到第 {行号} 行', 配色['内建'])

    # ------------------------------------------------------------------ 悬停提示
    def _取词(self, x: int, y: int) -> str:
        try:
            索引 = self.编辑区.index(f'@{x},{y}')
        except tk.TclError:
            return ''
        行, 列 = (int(v) for v in 索引.split('.'))
        文本 = self.编辑区.get(f'{行}.0', f'{行}.end')
        if not 文本 or 列 >= len(文本):
            return ''

        def 是词符(c: str) -> bool:
            return ('\u3400' <= c <= '\u9fff') or c.isalnum() or c in '._'

        if not 是词符(文本[列]):
            return ''
        起 = 列
        while 起 > 0 and 是词符(文本[起 - 1]):
            起 -= 1
        止 = 列
        while 止 + 1 < len(文本) and 是词符(文本[止 + 1]):
            止 += 1
        return 文本[起:止 + 1]

    def _悬停(self, 事件) -> None:
        词 = self._取词(事件.x, 事件.y)
        if not 词 or 词 == getattr(self, '_上次悬停词', None):
            if not 词:
                self._藏提示()
            return
        self._上次悬停词 = 词
        映射 = 查映射(词)
        if not 映射:
            self._藏提示()
            return
        self._显示提示(f'{词} → {映射}', 事件.x_root + 16, 事件.y_root + 20)

    def _显示提示(self, 文本: str, x: int, y: int) -> None:
        提示 = getattr(self, '_提示框', None)
        if 提示 is None:
            提示 = tk.Toplevel(self.根)
            提示.overrideredirect(True)
            提示.attributes('-topmost', True)
            标签 = tk.Label(提示, text=文本, bg='#2f3242', fg='#f1fa8c',
                          font=('Microsoft YaHei UI', 9), padx=8, pady=4, bd=1, relief='solid')
            标签.pack()
            self._提示框 = 提示
            self._提示标签 = 标签
        self._提示标签.configure(text=文本)
        提示.geometry(f'+{x}+{y}')
        提示.deiconify()

    def _藏提示(self) -> None:
        self._上次悬停词 = None
        提示 = getattr(self, '_提示框', None)
        if 提示 is not None:
            提示.withdraw()

    # ------------------------------------------------------------------ 退出
    def 退出(self) -> None:
        if self.脏 and not messagebox.askyesno('还没保存', '内容改过了，直接退出？'):
            return
        self.停止()
        self.根.destroy()

    def 运行主循环(self) -> None:
        self.根.mainloop()


def main(argv: list[str]) -> int:
    初始 = argv[1] if len(argv) > 1 else None
    编辑器 = 桥编辑器(初始)
    编辑器.运行主循环()
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
