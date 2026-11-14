"""桥语言运行时：`运行` / `并行` / `读取文档` / `跳转` 的信号类

这三样是桥语言在 Python 之上加的东西——它们不是"翻译"，而是**语义**，
所以放在运行时里，由转译器把中文名映射到这里：

    `运行("a.bridge")` → 桥运行("a.bridge")   # 等它跑完，拿它的 返回 值
    `并行("a.bridge")` → 桥并行("a.bridge")   # 起线程跑，不等，返回值丢掉
    `读取("a.txt")`   → 桥读取("a.txt")      # 拿到一个"文档"对象
    `跳转到 标记1`     → raise 桥跳转("标记1")  # 由生成的派发循环接住
    `返回 1`（模块级） → raise 桥返回(1)        # 由 桥运行 接住

这几个名字由 桥.py / 运行源码 / 导入钩子 注入到 globals 里，所以用户代码
不需要自己 import。
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path


class 桥返回(Exception):
    """模块级 `返回 X` 的信号（Python 不允许模块级 return，只好用异常带值）"""

    def __init__(self, 值=None) -> None:
        super().__init__(值)
        self.值 = 值


class 桥跳转(Exception):
    """`跳转到 标记` 的信号；派发循环接住它，换成状态再继续"""

    def __init__(self, 标记: str) -> None:
        super().__init__(标记)
        self.标记 = 标记


def 运行时名字() -> dict:
    """要注入到被转译文件的 globals 里的名字"""
    return {
        '桥返回': 桥返回,
        '桥跳转': 桥跳转,
        '桥运行': 桥运行,
        '桥并行': 桥并行,
        '桥读取': 桥读取,
        '桥新建': 桥新建,
        '桥删除': 桥删除,
        '桥等待': 桥等待,
        '桥打开数据库': 桥打开数据库,
        '桥取网页': 桥取网页,
        '桥发请求': 桥发请求,
        '文档': 文档,
        '文件': 文件,
    }


def _执行文件(路径) -> None:
    """跑一个 .bridge 文件（独立命名空间，等价于单独运行一个程序）"""
    from .主转译器 import 编译

    文件 = Path(路径)
    源码 = 文件.read_text(encoding='utf-8-sig')
    代码, _产物 = 编译(源码, str(文件))
    命名空间 = {'__name__': '__main__', '__builtins__': __builtins__}
    命名空间.update(运行时名字())
    try:
        exec(代码, 命名空间)
    except 桥返回:
        return                      # 正常结束（带返回值）


def _定位路径(路径) -> Path:
    """相对路径先按当前目录找，找不到再沿调用栈找**哪个脚本在调**

    这样 `运行("a.bridge")` / `读取("./a.txt")` 写起来跟"同目录"一致，
    不用关心用户从哪个目录敲的 `python 桥.py 运行`。线程里调用时栈上没有
    用户文件，所以 `桥并行` 会先在**调用线程**把路径定死，再交给子线程。
    """
    文件 = Path(路径)
    if 文件.is_absolute() or 文件.is_file():
        return 文件
    建议 = None            # 第一个"目录存在"的候选：新建文件时就用它
    帧 = None
    try:
        帧 = sys._getframe(1)
        while 帧 is not None:
            候选目录 = 帧.f_globals.get('__file__')
            # 只信用户脚本：跳过转译器包自己的帧（否则会先撞上 运行时.py 的 __file__）
            if (候选目录 and not str(帧.f_globals.get('__name__', '')).startswith('转译器')):
                候选 = Path(候选目录).parent / 文件
                if 候选.is_file():
                    return 候选
                if 建议 is None and 候选.parent.is_dir():
                    建议 = 候选
            帧 = 帧.f_back
    except (AttributeError, ValueError):
        pass
    return 建议 or 文件

def 桥运行(路径):
    """运行另一个 .bridge，等它跑完，返回它的 `返回` 值（没有就返回 None）"""
    from .主转译器 import 编译

    文件 = _定位路径(路径)
    if not 文件.is_file():
        raise FileNotFoundError(f'要运行的文件不存在：{文件}')
    源码 = 文件.read_text(encoding='utf-8-sig')
    代码, _产物 = 编译(源码, str(文件))
    命名空间 = {
        '__name__': '__main__',
        '__file__': str(文件),          # 嵌套 运行 时继续按"被调文件目录"找相对路径
        '__builtins__': __builtins__,
    }
    命名空间.update(运行时名字())
    try:
        exec(代码, 命名空间)
    except 桥返回 as 信号:
        return 信号.值
    return None


def _跑并刷新(路径) -> None:
    """子线程里跑完顺手 flush：守护线程被强行终止前，缓冲里的话可能来不及吐出来"""
    try:
        桥运行(路径)
    finally:
        sys.stdout.flush()


def 桥并行(路径) -> threading.Thread:
    """起一个线程跑另一个 .bridge，不等它、也不收它的返回值

    路径先在**调用线程**定死：子线程的栈上没有用户脚本，找不到相对路径的锚点。
    """
    绝对 = _定位路径(路径)
    件 = threading.Thread(target=_跑并刷新, args=(绝对,), daemon=True)
    件.start()
    _并行线程们.append(件)             # `等待完成()` 不带参数时等全部
    return 件


_并行线程们: list[threading.Thread] = []


def 桥并发(路径) -> threading.Thread:
    """同 桥并行，但记下线程句柄，方便 `等待()` 统一等"""
    件 = 桥并行(路径)
    _并行线程们.append(件)
    return 件


def 桥等待(句柄=None) -> None:
    """等并行任务跑完：给句柄就等那个，不给就把所有 并行 的都等一遍"""
    if 句柄 is not None:
        句柄.join()
        return
    for 件 in list(_并行线程们):
        件.join()


class 文件:
    """文件对象：所有"磁盘上的东西"的基类

    - `文件名` 读 / 写（写 = 磁盘改名，也就是你要的"文件类支持改名"）
    - `改名(新名)` 方法形式，效果一样
    - `路径` / `大小` / `存在`
    - `复制到(目标)` / `删除()`
    """

    def __init__(self, 路径) -> None:
        object.__setattr__(self, '_路径', Path(路径))

    # ---- 属性 ----
    @property
    def 路径(self) -> str:
        return str(self._路径)

    @property
    def 文件名(self) -> str:
        return self._路径.name

    @文件名.setter
    def 文件名(self, 新名: str) -> None:
        self.改名(新名)

    @property
    def 大小(self) -> int:
        return self._路径.stat().st_size if self._路径.exists() else 0

    @property
    def 存在(self) -> bool:
        return self._路径.exists()

    @property
    def 后缀(self) -> str:
        return self._路径.suffix

    # ---- 改名 / 复制 / 删除 ----
    def 改名(self, 新名: str) -> '文件':
        """改文件名（同目录内），返回自己，方便链式写"""
        新路径 = self._路径.with_name(新名)
        self._路径.replace(新路径)
        object.__setattr__(self, '_路径', 新路径)
        return self

    def 复制到(self, 目标) -> '文件':
        """复制到目标位置；返回**同类型**对象（文档复制出来还是文档）"""
        import shutil

        目标路径 = _定位路径(目标)
        shutil.copy2(self._路径, 目标路径)
        return self.__class__(目标路径)

    def 删除(self) -> None:
        if self._路径.exists():
            self._路径.unlink()

    # `删除` 是关键字（del），桥语言里用 `删除自己` 或直接 `删除文件(路径)`
    删除自己 = 删除

    def __fspath__(self) -> str:
        return str(self._路径)

    def __repr__(self) -> str:
        return f'文件({self._路径.name})'


class 文档(文件):
    """`读取("a.txt")` 拿到的东西：文件 + 文本内容

    - `内容` 读 / 写（写 = 回写文件）
    - `文档[0]` / `文档[0:5]` 按字符取
    - `文档.追加("…")` 在末尾接一段
    - 用它当字符串：`输出（文档）`、`"世界" 在 文档`
    """

    def __init__(self, 路径) -> None:
        super().__init__(路径)
        内容 = self._路径.read_text(encoding='utf-8-sig')
        object.__setattr__(self, '_内容', 内容)

    # ---- 内容 ----
    @property
    def 内容(self) -> str:
        return self._内容

    @内容.setter
    def 内容(self, 值: str) -> None:
        object.__setattr__(self, '_内容', str(值))
        self._路径.write_text(str(值), encoding='utf-8')

    def 重新读取(self) -> '文档':
        object.__setattr__(self, '_内容', self._路径.read_text(encoding='utf-8-sig'))
        return self

    def 追加(self, 片段: str) -> '文档':
        self.内容 = self._内容 + str(片段)
        return self

    # 方法表会把 `.追加` 翻成 `.append`，挂个别名接住
    append = 追加

    def 改名(self, 新名: str) -> '文档':
        super().改名(新名)
        return self

    # `.内容` 会被方法表翻成 `.items`，这里兼容一下
    def __getattr__(self, 名: str):
        if 名 == 'items':
            return object.__getattribute__(self, '_内容')
        if 名 == 'size':
            return self.大小
        raise AttributeError(f'文档对象没有「{名}」这个属性')

    def __setattr__(self, 名: str, 值) -> None:
        if 名 == 'items':
            self.内容 = 值
            return
        object.__setattr__(self, 名, 值)

    # ---- 像字符串一样用 ----
    def __getitem__(self, 键):
        return self._内容[键]

    def __setitem__(self, 键, 值) -> None:
        if isinstance(键, slice):
            新 = self._内容[:键.start] + str(值) + self._内容[键.stop:]
        else:
            新 = self._内容[:键] + str(值) + self._内容[键 + 1:]
        self.内容 = 新

    def __len__(self) -> int:
        return len(self._内容)

    def __contains__(self, 值) -> bool:
        return 值 in self._内容

    def __str__(self) -> str:
        return self._内容

    def __repr__(self) -> str:
        return f'文档({self._路径.name}, {len(self._内容)} 字)'


class JSON节点:
    """`读取("x.json")` 拿到的东西：能按字段读写的 JSON

    - `节点.字段` / `节点["字段"]` 取；赋值同样两种写法
    - 嵌套对象/数组自动再包一层，所以 `配置.数据库.主机` 能直接点下去
    - `节点.追加(x)`（数组）、`节点.取("a.b")`、`节点.有("字段")`、`节点.条目数`
    - `节点.保存()` 写回文件；`节点.原始()` 拿纯 dict/list
    """

    内部名 = frozenset({'保存', '追加', '取', '有', '原始', '根', '数据'})

    def __init__(self, 根=None, 路径=(), 值=None) -> None:
        object.__setattr__(self, '_根', 根)
        object.__setattr__(self, '_路径', tuple(路径))
        if 值 is not None:
            object.__setattr__(self, '_值', 值)

    # ---------------- 取值 ----------------
    def _当前(self):
        if '_值' in self.__dict__ and not self._路径:
            return self._值
        值 = self._根.原始() if self._根 is not None else self._值
        for 键 in self._路径:
            值 = 值[键]
        return 值

    def _包(self, 值):
        if isinstance(值, (dict, list)):
            return JSON节点(self._根, self._路径, 值) if self._根 is None else JSON节点(self._根, self._路径)
        return 值

    def _包键(self, 键):
        值 = self._当前()[键]
        if isinstance(值, (dict, list)):
            return JSON节点(self._根, self._路径 + (键,)) if self._根 is not None else JSON节点(值=值)
        return 值

    def __getattr__(self, 名: str):
        if 名.startswith('_'):
            raise AttributeError(名)
        if 名 in ('删除自己', '改名') and self._根 is not None:
            return getattr(self._根, 名)
        当前 = self._当前()
        if 名 == 'items' and not (isinstance(当前, dict) and 'items' in 当前):
            # `.内容` 会被方法表翻成 `.items`；对 JSON 来说"内容"就是整份数据
            return 当前
        if isinstance(当前, dict) and 名 in 当前:
            值 = 当前[名]
            if isinstance(值, (dict, list)):
                return JSON节点(self._根, self._路径 + (名,)) if self._根 is not None else JSON节点(值=值)
            return 值
        raise AttributeError(f'JSON 里没有「{名}」这一项')

    def __setattr__(self, 名: str, 值) -> None:
        if 名.startswith('_') or 名 in type(self).内部名 or hasattr(type(self), 名):
            object.__setattr__(self, 名, 值)
            return
        当前 = self._当前()
        if not isinstance(当前, dict):
            raise TypeError('这个 JSON 值不是对象，不能按字段赋值')
        当前[名] = _转纯(值)

    def __getitem__(self, 键):
        return self._包键(键)

    def __setitem__(self, 键, 值) -> None:
        当前 = self._当前()
        if isinstance(当前, dict):
            当前[键] = _转纯(值)
        elif isinstance(当前, list):
            当前[键] = _转纯(值)
        else:
            raise TypeError('这个 JSON 值不支持下标赋值')

    def __len__(self) -> int:
        return len(self._当前())

    def __iter__(self):
        当前 = self._当前()
        for 键 in 当前:
            yield 键

    def __contains__(self, 键) -> bool:
        return 键 in self._当前()

    # ---------------- 方法 ----------------
    def 追加(self, 值) -> 'JSON节点':
        当前 = self._当前()
        if not isinstance(当前, list):
            raise TypeError('只有数组能追加')
        当前.append(_转纯(值))
        return self

    append = 追加

    def 取(self, 路径文本: str, 默认=None):
        当前 = self._当前()
        for 段 in str(路径文本).split('.'):
            if isinstance(当前, dict):
                if 段 not in 当前:
                    return 默认
                当前 = 当前[段]
            elif isinstance(当前, list):
                try:
                    当前 = 当前[int(段)]
                except (ValueError, IndexError):
                    return 默认
            else:
                return 默认
        return 当前

    def 有(self, 键: str) -> bool:
        当前 = self._当前()
        if isinstance(当前, dict):
            return 键 in 当前
        if isinstance(当前, list):
            try:
                return 0 <= int(键) < len(当前)
            except ValueError:
                return False
        return False

    @property
    def 条目数(self) -> int:
        return len(self._当前())

    def 原始(self):
        return self._当前()

    def 保存(self, 文件=None) -> str:
        if self._根 is not None:
            return self._根.保存(文件)
        件 = _定位路径(文件) if 文件 else Path('数据.json')
        件.write_text(json.dumps(self._值, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(件)

    def __str__(self) -> str:
        return json.dumps(self._当前(), ensure_ascii=False, indent=2)

    def __repr__(self) -> str:
        return f'JSON节点({len(self)} 项)'


def _转纯(值):
    """把 JSON节点 拆成纯 dict/list（保存时用）"""
    if isinstance(值, JSON节点):
        return 值.原始()
    if isinstance(值, dict):
        return {k: _转纯(v) for k, v in 值.items()}
    if isinstance(值, list):
        return [_转纯(v) for v in 值]
    return 值


class 结构化:
    """`读取("x.json")` 返回的**根**对象：带文件名 / 保存能力"""

    def __init__(self, 路径) -> None:
        object.__setattr__(self, '_路径', Path(路径))
        初始 = None
        if self._路径.is_file():
            文本 = self._路径.read_text(encoding='utf-8-sig').strip()
            if 文本:
                初始 = json.loads(文本)
        if 初始 is None:
            初始 = {}
        object.__setattr__(self, '_节点', JSON节点(值=初始))

    # 文件信息
    @property
    def 文件名(self) -> str:
        return self._路径.name

    @property
    def 路径(self) -> str:
        return str(self._路径)

    @property
    def 大小(self) -> int:
        return self._路径.stat().st_size if self._路径.is_file() else 0

    @property
    def 存在(self) -> bool:
        return self._路径.is_file()

    # 转发到节点
    def __getattr__(self, 名: str):
        if 名.startswith('_'):
            raise AttributeError(名)
        if 名 in ('保存', '追加', '取', '有', '原始'):
            return getattr(self._节点, 名)
        return getattr(self._节点, 名)

    def __setattr__(self, 名: str, 值) -> None:
        if 名.startswith('_'):
            object.__setattr__(self, 名, 值)
            return
        setattr(self._节点, 名, 值)

    def __getitem__(self, 键):
        return self._节点[键]

    def __setitem__(self, 键, 值) -> None:
        self._节点[键] = 值

    def __len__(self) -> int:
        return len(self._节点)

    def __iter__(self):
        return iter(self._节点)

    def __contains__(self, 键) -> bool:
        return 键 in self._节点

    @property
    def 条目数(self) -> int:
        return len(self._节点)

    def 原始(self):
        return self._节点.原始()

    def 追加(self, 值):
        return self._节点.追加(值)

    append = 追加

    def 取(self, 路径文本: str, 默认=None):
        return self._节点.取(路径文本, 默认)

    def 有(self, 键: str) -> bool:
        return self._节点.有(键)

    def 保存(self, 文件=None) -> str:
        目标 = Path(文件) if 文件 else self._路径
        目标.write_text(json.dumps(self.原始(), ensure_ascii=False, indent=2),
                        encoding='utf-8', newline='\n')
        return str(目标)

    def 改名(self, 新名: str) -> '结构化':
        新路径 = self._路径.with_name(新名)
        self._路径.replace(新路径)
        object.__setattr__(self, '_路径', 新路径)
        return self

    def 删除自己(self) -> None:
        if self._路径.is_file():
            self._路径.unlink()

    def __str__(self) -> str:
        return str(self._节点)

    def __repr__(self) -> str:
        return f'结构化({self._路径.name}, {len(self)} 项)'


class 表格:
    """`读取("x.csv")` 拿到的二维表：按行/列取值、追加、保存

    - `表.表头` 第一行；`表.行数` / `表.条目数`
    - `表[0]` 第一行（列表）；`表[0][1]` 第一行第二列
    - `表.行(0)` 同上；`表.列("分数")` 按表头取一整列
    - `表.追加行([...])`；`表.保存()`
    """

    内部名 = frozenset({'保存', '追加行', '行', '列', '表头', '行数', '条目数', '原始',
                       '删除自己', '改名', '复制到'})

    def __init__(self, 路径, 行们=None) -> None:
        object.__setattr__(self, '_路径', Path(路径))
        if 行们 is None:
            行们 = []
            if self._路径.is_file():
                文本 = self._路径.read_text(encoding='utf-8-sig').strip()
                行们 = [行 for 行 in 文本.splitlines() if 行 != ''] if 文本 else []
        object.__setattr__(self, '_行们', [list(行) for 行 in 行们])

    @property
    def 表头(self):
        return list(self._行们[0]) if self._行们 else []

    @property
    def 行数(self) -> int:
        return len(self._行们)

    条目数 = 行数

    def 行(self, 序: int):
        return list(self._行们[序])

    def 列(self, 名):
        if not self._行们:
            return []
        表头 = self.表头
        if isinstance(名, int):
            序 = 名
        else:
            if 名 not in 表头:
                raise AttributeError(f'表里没有「{名}」这一列')
            序 = 表头.index(名)
        return [行[序] if 序 < len(行) else '' for 行 in self._行们[1:]]

    def 追加行(self, 行) -> '表格':
        self._行们.append([str(值) for 值 in 行])
        return self

    def 原始(self):
        return [list(行) for 行 in self._行们]

    def 保存(self, 文件=None) -> str:
        目标 = Path(文件) if 文件 else self._路径
        目标.write_text('\n'.join(','.join(行) for 行 in self._行们) + '\n',
                        encoding='utf-8', newline='\n')
        return str(目标)

    def 改名(self, 新名: str) -> '表格':
        新路径 = self._路径.with_name(新名)
        self._路径.replace(新路径)
        object.__setattr__(self, '_路径', 新路径)
        return self

    def 删除自己(self) -> None:
        if self._路径.exists():
            self._路径.unlink()

    def __getitem__(self, 键):
        return list(self._行们[键])

    def __len__(self) -> int:
        return len(self._行们)

    def __iter__(self):
        for 行 in self._行们:
            yield list(行)

    def __getattr__(self, 名: str):
        if 名.startswith('_'):
            raise AttributeError(名)
        raise AttributeError(f'表格没有「{名}」这项')

    def __str__(self) -> str:
        return '\n'.join(','.join(行) for 行 in self._行们)

    def __repr__(self) -> str:
        return f'表格({self._路径.name}, {len(self._行们)} 行)'


def _读CSV(路径) -> '表格':
    行们 = []
    for 行 in 路径.read_text(encoding='utf-8-sig').splitlines():
        if 行.strip() == '':
            continue
        行们.append(行.split(','))
    return 表格(路径, 行们)


class 数据库表:
    """`库.表("图书")` 拿到的东西：一张 SQLite 表

    - `插入({...})` / `插入多([...])` / `更新({...}, 条件, 参数)` / `删除行(条件, 参数)`
    - `查询(条件="", 参数=(), 字段="*", 排序="", 条数=None)` → list[dict]
    - `全部()` / `行数` / `结构()` / `加列(名, 类型)`
    """

    内部名 = frozenset({'插入', '插入多', '更新', '删除行', '查询', '全部', '行数',
                       '结构', '加列', '建索引', '名字', '原始', 'insert', 'update'})

    def __init__(self, 库, 名: str) -> None:
        object.__setattr__(self, '_库', 库)
        object.__setattr__(self, '_名字', str(名))

    @property
    def 名字(self) -> str:
        return self._名字

    @property
    def 行数(self) -> int:
        return self.查询(字段='COUNT(*) AS 数')[0]['数']

    def 插入(self, 行: dict) -> int:
        列们 = ', '.join(f'"{c}"' for c in 行)
        占位 = ', '.join('?' for _ in 行)
        return self._库.执行(
            f'INSERT INTO "{self._名字}" ({列们}) VALUES ({占位})', tuple(行.values()))

    insert = 插入

    def 插入多(self, 行们: list[dict]) -> int:
        """一条 SQL 批量插入（executemany），比逐条快一个数量级"""
        行们 = [dict(行) for 行 in 行们]
        if not 行们:
            return 0
        列们 = list(行们[0].keys())
        列文本 = ', '.join(f'"{c}"' for c in 列们)
        占位 = ', '.join('?' for _ in 列们)
        序列 = [tuple(行.get(c) for c in 列们) for 行 in 行们]
        self._库.执行多(
            f'INSERT INTO "{self._名字}" ({列文本}) VALUES ({占位})', 序列)
        return len(行们)

    def 更新(self, 值: dict, 条件: str = '', 参数=()) -> int:
        赋值 = ', '.join(f'"{c}" = ?' for c in 值)
        语句 = f'UPDATE "{self._名字}" SET {赋值}'
        if 条件:
            语句 += f' WHERE {条件}'
        return self._库.执行(语句, tuple(值.values()) + tuple(参数))

    update = 更新

    def 删除行(self, 条件: str = '', 参数=()) -> int:
        语句 = f'DELETE FROM "{self._名字}"'
        if 条件:
            语句 += f' WHERE {条件}'
        return self._库.执行(语句, tuple(参数))

    def 查询(self, 条件: str = '', 参数=(), 字段: str = '*',
             排序: str = '', 条数=None) -> list[dict]:
        语句 = f'SELECT {字段} FROM "{self._名字}"'
        if 条件:
            语句 += f' WHERE {条件}'
        if 排序:
            语句 += f' ORDER BY {排序}'
        if 条数 is not None:
            语句 += f' LIMIT {int(条数)}'
        return self._库.查询(语句, tuple(参数))

    def 全部(self) -> list[dict]:
        return self.查询()

    all = 全部

    def 结构(self) -> list[dict]:
        return self._库.查询(f'PRAGMA table_info("{self._名字}")')

    def 加列(self, 名: str, 类型: str = 'TEXT') -> '数据库表':
        self._库.执行(f'ALTER TABLE "{self._名字}" ADD COLUMN "{名}" {类型}')
        return self

    def 建索引(self, 列们, 唯一: bool = False) -> '数据库表':
        列们 = [列们] if isinstance(列们, str) else list(列们)
        名 = f'idx_{self._名字}_' + '_'.join(列们)
        修饰 = 'UNIQUE ' if 唯一 else ''
        self._库.执行(f'CREATE {修饰}INDEX IF NOT EXISTS "{名}" '
                     f'ON "{self._名字}" (' + ', '.join(f'"{c}"' for c in 列们) + ')')
        return self

    def __repr__(self) -> str:
        return f'数据库表({self._名字})'


class 事务:
    """`带 库.事务():` 的上下文管理器：正常结束提交，出异常回滚

    进入时把库标成"事务中"，`执行/执行多` 就不再每句自动 commit。
    """

    def __init__(self, 库) -> None:
        object.__setattr__(self, '_库', 库)

    def __enter__(self) -> '事务':
        self._库._事务中 += 1
        try:
            self._库._连接.execute('BEGIN')
        except Exception:
            pass
        return self

    def __exit__(self, 类型, 值, 栈) -> bool:
        self._库._事务中 = max(0, self._库._事务中 - 1)
        if 类型 is None:
            self._库._连接.commit()
        else:
            self._库._连接.rollback()
        return False


class 数据库:
    """`读取("x.db")` / `打开数据库("x.db")` 拿到的东西

    - `表("名")` / `建表("名", {"列": "TEXT"})` / `表们()` / `执行(sql, 参数)` / `查询(sql, 参数)`
    - `提交()` / `关闭()`
    """

    内部名 = frozenset({'表', '建表', '表们', '执行', '执行多', '查询', '提交',
                       '关闭', '事务', '开启WAL', '路径', '删除自己',
                       'close', 'commit'})

    def __init__(self, 路径) -> None:
        import sqlite3

        object.__setattr__(self, '_路径', Path(路径))
        object.__setattr__(self, '_连接',
                           sqlite3.connect(str(self._路径)))
        self._连接.row_factory = sqlite3.Row
        object.__setattr__(self, '_事务中', 0)

    @property
    def 路径(self) -> str:
        return str(self._路径)

    def 执行(self, 语句: str, 参数=()) -> int:
        游标 = self._连接.execute(语句, tuple(参数))
        if not self._事务中:
            self._连接.commit()
        return 游标.lastrowid if 游标.lastrowid is not None else 游标.rowcount

    def 执行多(self, 语句: str, 序列) -> int:
        游标 = self._连接.executemany(语句, [tuple(x) for x in 序列])
        if not self._事务中:
            self._连接.commit()
        return 游标.rowcount

    def 查询(self, 语句: str, 参数=()) -> list[dict]:
        游标 = self._连接.execute(语句, tuple(参数))
        return [dict(行) for 行 in 游标.fetchall()]

    def 事务(self) -> '事务':
        """`带 库.事务():` —— 出异常自动回滚"""
        return 事务(self)

    def 开启WAL(self) -> '数据库':
        self._连接.execute('PRAGMA journal_mode=WAL')
        self._连接.commit()
        return self

    def 表(self, 名: str) -> 数据库表:
        存在 = self.查询(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (名,))
        if not 存在:
            raise ValueError(f'数据库里没有表「{名}」（先 建表("{名}", {{...}})）')
        return 数据库表(self, 名)

    def 建表(self, 名: str, 列们: dict) -> 数据库表:
        定义 = ', '.join(f'"{c}" {t}' for c, t in 列们.items())
        self.执行(f'CREATE TABLE IF NOT EXISTS "{名}" ({定义})')
        return 数据库表(self, 名)

    def 表们(self) -> list[str]:
        return [行['name'] for 行 in self.查询(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    def 提交(self) -> None:
        self._连接.commit()

    commit = 提交

    def 关闭(self) -> None:
        try:
            self._连接.close()
        except Exception:
            pass

    close = 关闭

    def 删除自己(self) -> None:
        self.关闭()
        if self._路径.is_file():
            self._路径.unlink()

    def __repr__(self) -> str:
        return f'数据库({self._路径.name})'


def 桥打开数据库(路径) -> 数据库:
    """打开（或新建）一个 SQLite 数据库（相对路径按调用者脚本目录找）"""
    return 数据库(_定位路径(路径))


class 响应:
    """`取网页("https://…")` 拿到的回复

    - `状态码` / `头部` / `内容`（bytes）/ `文本`（自动按响应编码解码）
    - `JSON`（解析成 dict/list）
    - `保存(路径)`
    """

    内部名 = frozenset({'状态码', '头部', '内容', '文本', 'JSON', '保存', '关闭', '原始'})

    def __init__(self, 原始) -> None:
        object.__setattr__(self, '_原始', 原始)
        object.__setattr__(self, '_内容', None)

    @property
    def 状态码(self) -> int:
        码 = getattr(self._原始, 'status', None) or self._原始.getcode()
        return 码 if 码 is not None else 200      # file:// 没有状态码，按 200 算

    @property
    def 头部(self):
        return self._原始.headers

    @property
    def 内容(self) -> bytes:
        if self._内容 is None:
            object.__setattr__(self, '_内容', self._原始.read())
        return self._内容

    @property
    def 文本(self) -> str:
        编码 = 'utf-8'
        try:
            字符集 = self._原始.headers.get_content_charset()
            if 字符集:
                编码 = 字符集
        except Exception:
            pass
        return self.内容.decode(编码, errors='replace')

    @property
    def JSON(self):
        return JSON节点(值=json.loads(self.文本))   # 给属性访问：响应.JSON.站点名

    def __getattr__(self, 名: str):
        # `.内容` 会被方法表翻成 `.items`，对响应来说"内容"就是 bytes
        if 名 == 'items':
            return object.__getattribute__(self, '内容')
        raise AttributeError(f'响应没有「{名}」这项')

    def 保存(self, 路径) -> str:
        文件 = _定位路径(路径)
        文件.write_bytes(self.内容)
        return str(文件)

    def 关闭(self) -> None:
        try:
            self._原始.close()
        except Exception:
            pass

    @property
    def 正常(self) -> bool:
        return 200 <= self.状态码 < 400

    def __enter__(self) -> '响应':
        return self

    def __exit__(self, 类型, 值, 栈) -> bool:
        self.关闭()
        return False

    def __repr__(self) -> str:
        return f'响应({self.状态码})'


from urllib.error import URLError

_默认UA = 'bridge-lang/0.2 (+https://github.com/bridge-lang)'
_可重试 = (URLError, TimeoutError, ConnectionError)


def _发请求(网址: str, 数据=None, 方法: str = 'GET', 头部: dict | None = None,
           超时: float = 30, 重试: int = 2) -> 响应:
    import time as _time
    import urllib.error
    import urllib.request

    if isinstance(数据, dict):
        数据 = json.dumps(数据, ensure_ascii=False).encode('utf-8')
        头部 = {**(头部 or {}), 'Content-Type': 'application/json; charset=utf-8'}
    elif isinstance(数据, str):
        数据 = 数据.encode('utf-8')

    请求头 = {
        'User-Agent': _默认UA,
        'Accept-Encoding': 'identity',      # 不主动要 gzip，省得响应是压缩字节
        **(头部 or {}),
    }
    最后错误 = None
    for 第几次 in range(max(0, int(重试)) + 1):
        try:
            请求 = urllib.request.Request(网址, data=数据, headers=请求头, method=方法)
            return 响应(urllib.request.urlopen(请求, timeout=超时))
        except urllib.error.HTTPError:
            raise                            # 4xx/5xx 是服务器正常回话，不重试
        except _可重试 as 错误:
            最后错误 = 错误
            if 第几次 >= int(重试):
                break
            _time.sleep(0.4 * (2 ** 第几次))   # 0.4s → 0.8s 退避
    raise URLError(f'请求失败（已重试 {重试} 次）：{最后错误}')


def 桥取网页(网址: str, 头部: dict | None = None, 超时: float = 30,
            重试: int = 2) -> 响应:
    """GET 一个网址（带默认 UA、失败自动退避重试）"""
    return _发请求(网址, 方法='GET', 头部=头部, 超时=超时, 重试=重试)


def 桥发请求(网址: str, 数据=None, 方法: str = 'POST', 头部: dict | None = None,
            超时: float = 30, 重试: int = 2) -> 响应:
    """发一个请求（POST/PUT/PATCH 都行），失败自动退避重试"""
    return _发请求(网址, 数据=数据, 方法=方法, 头部=头部, 超时=超时, 重试=重试)


def 桥读取(路径):
    """读文件：.json 给 JSON 对象，其它给文本文档（相对路径按调用者脚本目录找）"""
    文件 = _定位路径(路径)
    if 文件.suffix.lower() in ('.db', '.sqlite', '.sqlite3'):
        return 桥打开数据库(文件)          # 数据库不存在就新建
    if not 文件.is_file():
        raise FileNotFoundError(f'要读取的文件不存在：{文件}')
    if 文件.suffix.lower() == '.json':
        return 结构化(文件)
    if 文件.suffix.lower() == '.csv':
        return _读CSV(文件)
    return 文档(文件)


def 桥新建(路径, 内容=None):
    """新建文件：.json 收 dict/list（或 JSON 文本），其它收字符串"""
    文件路径 =  _定位路径(路径)
    文件路径.parent.mkdir(parents=True, exist_ok=True)
    if 文件路径.suffix.lower() == '.csv':
        行们 = 内容 if isinstance(内容, list) else ([] if 内容 is None else [str(内容)])
        表 = 表格(文件路径, 行们)
        文件路径.write_text('\n'.join(','.join(行) for 行 in 表.原始()) + ('\n' if 行们 else ''),
                            encoding='utf-8', newline='\n')
        return 表
    if 文件路径.suffix.lower() == '.json':
        if 内容 is None:
            内容 = {}
        elif isinstance(内容, str):
            内容 = json.loads(内容) if 内容.strip() else {}
        文件路径.write_text(json.dumps(内容, ensure_ascii=False, indent=2),
                            encoding='utf-8', newline='\n')
        return 结构化(文件路径)
    if 文件路径.suffix.lower() in ('.db', '.sqlite', '.sqlite3'):
        库 = 桥打开数据库(文件路径)
        if 内容:
            for 表名, 列们 in dict(内容).items():
                库.建表(表名, 列们)
        return 库
    文件路径.write_text('' if 内容 is None else str(内容), encoding='utf-8')
    return 文档(文件路径)


def 桥删除(路径) -> None:
    """删掉一个文件"""
    文件(_定位路径(路径)).删除()
