"""导入钩子：让 `.bridge` 文件能像普通模块一样被 `导入`

用法：

    from 转译器 import 安装导入钩子
    安装导入钩子(['示例'])     # 之后 导入 工具 会找到 示例/工具.bridge

实现是标准库 importlib 的 MetaPathFinder + Loader，挂在 sys.meta_path 最前面，
`.bridge` 命中时由桥语言自己转译 + 编译，其余后缀完全不受影响。
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path

from .主转译器 import 编译

后缀 = '.bridge'
_已装钩子: list['桥查找器'] = []


class 桥加载器(importlib.abc.Loader):
    def __init__(self, 路径: Path) -> None:
        self.路径 = Path(路径)

    def create_module(self, spec):          # 用默认的模块对象
        return None

    def exec_module(self, module) -> None:
        源码 = self.路径.read_text(encoding='utf-8-sig')
        代码, _ = 编译(源码, str(self.路径))
        module.__file__ = str(self.路径)
        from .运行时 import 运行时名字

        for 名, 值 in 运行时名字().items():
            module.__dict__.setdefault(名, 值)
        exec(代码, module.__dict__)


class 桥包加载器(importlib.abc.Loader):
    """目录形式的桥语言包：`程序/__init__.bridge` + 同目录下的 *.bridge 子模块"""

    def __init__(self, 目录: Path) -> None:
        self.目录 = Path(目录)

    def create_module(self, spec):
        return None

    def exec_module(self, module) -> None:
        入口 = self.目录 / f'__init__{后缀}'
        module.__path__ = [str(self.目录)]
        module.__file__ = str(入口)
        源码 = 入口.read_text(encoding='utf-8-sig')
        代码, _ = 编译(源码, str(入口))
        from .运行时 import 运行时名字

        for 名, 值 in 运行时名字().items():
            module.__dict__.setdefault(名, 值)
        exec(代码, module.__dict__)


class 桥查找器(importlib.abc.MetaPathFinder):
    def __init__(self, 搜索目录=None) -> None:
        目录 = 搜索目录 or [Path.cwd()]
        if isinstance(目录, (str, Path)):
            目录 = [目录]
        self.搜索目录 = [Path(p) for p in 目录]

    def find_spec(self, 全名: str, 路径=None, target=None):
        短名 = 全名.rsplit('.', 1)[-1]
        候选目录 = [Path(p) for p in (路径 or [])] or self.搜索目录
        for 目录 in 候选目录:
            # 包优先：<名>/__init__.bridge
            包目录 = 目录 / 短名
            if (包目录 / f'__init__{后缀}').is_file():
                return importlib.util.spec_from_loader(
                    全名, 桥包加载器(包目录),
                    origin=str(包目录 / f'__init__{后缀}'), is_package=True,
                )
            候选 = 目录 / f'{短名}{后缀}'
            if 候选.is_file():
                return importlib.util.spec_from_loader(
                    全名, 桥加载器(候选), origin=str(候选)
                )
        return None


def 安装导入钩子(搜索目录=None):
    """把钩子挂到 sys.meta_path 最前面；重复调用会替换掉旧钩子"""
    for 旧 in list(_已装钩子):
        if 旧 in sys.meta_path:
            sys.meta_path.remove(旧)
    _已装钩子.clear()
    钩子 = 桥查找器(搜索目录)
    sys.meta_path.insert(0, 钩子)
    _已装钩子.append(钩子)
    return 钩子
