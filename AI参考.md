# 桥语言参考（写给 AI 的版本）

> 用途：把这份文档（或 `AI速查.txt`）贴进 AI 的 system prompt，AI 就能直接写/改桥语言代码。
> **每次使用前，先看 https://github.com/YHSome/bridge-lang/releases 确认是不是最新版**（本文对应 v0.2.0）；版本旧了先升级，再按旧规则写代码容易翻车。
> 全部内容由 `工具/导出AI参考.py` 从 `转译器/规则/` 生成，**不要在文档里手改规则**。

版本 0.2.0 · 关键字 108 · 内建 78 · 异常 31 · 方法 95 · 模块 18 · 句式糖 44

## 1. 一句话原理

桥语言 = **Python 的源级中文方言**。`.bridge` 先被转译成标准 Python（行号逐行对应），
再交给 CPython 执行。所以：

- 会 Python 就会桥语言；英文写法原样透传（混写合法）；
- 中文关键字是**多对一**（多个中文写法 → 同一个 Python 关键字）；
- 字符串、注释里的中文**不翻译**；
- 报错行号对着 `.bridge` 源码。

## 2. 给 AI 的硬规则（写代码前先读）

1. **不要用规则表里的词当变量名/函数名**（`输出`、`长度`、`删除`、`载入`、`现在` 等），否则会被翻掉；
2. 方法名（点号后）只能用纯中文，**不要带数字/字母**（`以2为底对数` 不行，`以二为底对数` 行）；
3. `.内容` 会被翻成 `.items`、`.追加` → `.append`、`.删除` 是关键字 → 运行时对象要挂英文别名；
4. `标记/跳转到` 只能写在模块顶层或函数/类的第一层，**不能跨函数**；
5. 中文标点（`（）` `，` `：`）与英文标点都支持，但**同一个括号别混用**；
6. 需要 Python 独有语法时直接写英文（`is not None`、`async` 之类），转译器原样透传；
7. 自己新增/修改规则后，跑 `python 桥.py 体检` 和 `python 自检.py`。

## 3. 关键字（语句层）

**同一个 Python 关键字可以有多个中文写法**，下表按 Python 侧归并：

| Python | 桥语言写法（任选） |
| --- | --- |
| `lambda` | `匿名函数` |
| `match` | `配对` |
| `case` | `情形` |
| `if` | `如果` / `若` / `假如` / `倘若` / `假若` |
| `elif` | `否则如果` / `否则若` / `不然如果` |
| `else` | `否则` / `不然` / `其余` |
| `while` | `当` / `只要` |
| `for` | `对于` / `遍历` |
| `in` | `在` |
| `and` | `并且` / `且` / `而且` / `与` |
| `or` | `或者` / `或` |
| `not` | `不是` / `非` / `不成立` |
| `is` | `是` |
| `==` | `等于` / `相等` |
| `!=` | `不等于` / `不相等` |
| `>` | `大于` |
| `<` | `小于` |
| `>=` | `不小于` / `大于等于` / `大于或等于` / `至少` |
| `<=` | `至多` / `小于等于` / `小于或等于` / `不大于` |
| `//` | `整除` |
| `%` | `取模` |
| `**` | `乘方` |
| `&` | `按位与` |
| `|` | `按位或` |
| `^` | `按位异或` |
| `<<` | `左移` |
| `>>` | `右移` |
| `~` | `按位取反` |
| `:=` | `赋值为` |
| `+` | `加上` |
| `-` | `减去` |
| `*` | `乘以` |
| `/` | `除以` |
| `True` | `真` / `真值` / `对` |
| `False` | `假` / `假值` / `错` |
| `None` | `空` / `空值` / `虚无` |
| `def` | `定义` / `函数` / `子程序` |
| `class` | `类` / `类别` |
| `return` | `返回` / `回传` |
| `yield` | `产出` / `交出` |
| `async` | `异步` |
| `await` | `等待` |
| `import` | `导入` / `引入` / `载入` |
| `from` | `从` / `来自` |
| `as` | `作为` / `当作` |
| `try` | `尝试` / `试着` |
| `except` | `捕获` / `捕获到` |
| `finally` | `最终` / `最后` |
| `raise` | `抛出` / `引发` |
| `break` | `中断` / `跳出` / `停止循环` |
| `continue` | `继续` / `下一步` / `跳过` |
| `pass` | `通过` / `占位` |
| `global` | `全局` |
| `nonlocal` | `非局部` |
| `del` | `删除` / `删掉` |
| `with` | `带` / `连同` |
| `assert` | `断言` / `确保` |


### 内建函数

光着写（不加点号）时的函数名。

| 桥语言 | Python |
| --- | --- |
| `输出` | `print` |
| `打印` | `print` |
| `显示` | `print` |
| `输入` | `input` |
| `读取输入` | `input` |
| `整数` | `int` |
| `转整数` | `int` |
| `浮点` | `float` |
| `转浮点` | `float` |
| `字符串` | `str` |
| `转字符串` | `str` |
| `布尔` | `bool` |
| `转布尔` | `bool` |
| `复述` | `repr` |
| `四舍五入` | `round` |
| `类型` | `type` |
| `是实例` | `isinstance` |
| `打开` | `open` |
| `运行` | `桥运行` |
| `并行` | `桥并行` |
| `读取` | `桥读取` |
| `打开数据库` | `桥打开数据库` |
| `取网页` | `桥取网页` |
| `发请求` | `桥发请求` |
| `新建文档` | `桥新建` |
| `删除文件` | `桥删除` |
| `等待完成` | `桥等待` |
| `自己` | `self` |
| `自身` | `self` |
| `排队` | `桥排队` |
| `前几个` | `桥前几个` |
| `最后一个` | `桥最后一个` |
| `第几个到第几个` | `桥切片` |
| `倒过来` | `桥倒过来` |
| `读二进制` | `桥读二进制` |
| `打开压缩包` | `桥打开压缩包` |
| `帮助` | `桥帮助` |
| `迭代` | `iter` |
| `下一个` | `next` |
| `列表` | `list` |
| `字典` | `dict` |
| `集合` | `set` |
| `元组` | `tuple` |
| `长度` | `len` |
| `求长度` | `len` |
| `取长度` | `len` |
| `范围` | `range` |
| `区间` | `range` |
| `绝对值` | `abs` |
| `求绝对值` | `abs` |
| `求和` | `sum` |
| `求总和` | `sum` |
| `合计值` | `sum` |
| `最大` | `max` |
| `求最大值` | `max` |
| `取最大` | `max` |
| `最小` | `min` |
| `求最小值` | `min` |
| `取最小` | `min` |
| `排序` | `sorted` |
| `求排序` | `sorted` |
| `排序结果` | `sorted` |
| `枚举` | `enumerate` |
| `逐个编号` | `enumerate` |
| `映射` | `map` |
| `过滤` | `filter` |
| `任意` | `any` |
| `任一为真` | `any` |
| `全部` | `all` |
| `全为真` | `all` |
| `拉链` | `zip` |
| `打包` | `zip` |
| `商和余` | `divmod` |
| `时间差` | `datetime.timedelta` |
| `真值` | `True` |
| `假值` | `False` |
| `空值` | `None` |
| `没有` | `None` |

### 异常类型

`捕获 值错误 作为 错误` —— 异常名同样可以中文。

| 桥语言 | Python |
| --- | --- |
| `网络错误` | `URLError` |
| `HTTP错误` | `HTTPError` |
| `超时错误` | `TimeoutError` |
| `JSON错误` | `JSONDecodeError` |
| `数据库错误` | `DatabaseError` |
| `完整性错误` | `IntegrityError` |
| `操作错误` | `OperationalError` |
| `权限错误` | `PermissionError` |
| `解码错误` | `UnicodeDecodeError` |
| `编码失败` | `UnicodeEncodeError` |
| `内存错误` | `MemoryError` |
| `递归错误` | `RecursionError` |
| `键错误` | `KeyError` |
| `索引错误` | `IndexError` |
| `属性缺失` | `AttributeError` |
| `类型不符` | `TypeError` |
| `异常` | `Exception` |
| `基础异常` | `BaseException` |
| `名称错误` | `NameError` |
| `名字错误` | `NameError` |
| `值错误` | `ValueError` |
| `类型错误` | `TypeError` |
| `属性错误` | `AttributeError` |
| `除零错误` | `ZeroDivisionError` |
| `除零` | `ZeroDivisionError` |
| `文件未找到错误` | `FileNotFoundError` |
| `文件没找到` | `FileNotFoundError` |
| `断言错误` | `AssertionError` |
| `停止迭代` | `StopIteration` |
| `导入错误` | `ImportError` |
| `溢出错误` | `OverflowError` |

### 对象方法（点号后）

只在 `对象.方法()` 位置生效；与方法同名的内建是两套表。

| 桥语言 | Python |
| --- | --- |
| `追加` | `append` |
| `添加` | `append` |
| `加进去` | `append` |
| `扩展` | `extend` |
| `批量添加` | `extend` |
| `插入` | `insert` |
| `移除` | `remove` |
| `去掉` | `remove` |
| `弹出` | `pop` |
| `取出` | `pop` |
| `清空` | `clear` |
| `拷贝` | `copy` |
| `复制` | `copy` |
| `排序` | `sort` |
| `反转` | `reverse` |
| `倒序` | `reverse` |
| `计数` | `count` |
| `索引` | `index` |
| `内容` | `items` |
| `条目` | `items` |
| `键` | `keys` |
| `键列表` | `keys` |
| `值` | `values` |
| `值列表` | `values` |
| `获取` | `get` |
| `取值` | `get` |
| `更新` | `update` |
| `合并更新` | `update` |
| `设置默认` | `setdefault` |
| `拆分` | `split` |
| `分割` | `split` |
| `替换` | `replace` |
| `去除空白` | `strip` |
| `去空格` | `strip` |
| `大写` | `upper` |
| `转大写` | `upper` |
| `小写` | `lower` |
| `转小写` | `lower` |
| `开头是` | `startswith` |
| `结尾是` | `endswith` |
| `连接` | `join` |
| `格式化` | `format` |
| `找到` | `find` |
| `读` | `read` |
| `读取` | `read` |
| `写` | `write` |
| `写入` | `write` |
| `关闭` | `close` |
| `格式化日期` | `strftime` |
| `星期几` | `weekday` |
| `日期部分` | `date` |
| `天数` | `days` |
| `返回码` | `returncode` |
| `标准输出` | `stdout` |
| `标准错误` | `stderr` |
| `编码` | `encode` |
| `解码` | `decode` |
| `十六进制` | `hex` |
| `左对齐` | `ljust` |
| `右对齐` | `rjust` |
| `居中` | `center` |
| `补零` | `zfill` |
| `标题化` | `title` |
| `首字母大写` | `capitalize` |
| `去前缀` | `removeprefix` |
| `去后缀` | `removesuffix` |
| `是否数字` | `isdigit` |
| `是否字母` | `isalpha` |
| `是否空白` | `isspace` |
| `是否数字字母` | `isalnum` |
| `十六进制摘要` | `hexdigest` |
| `摘要值` | `digest` |
| `出现最多` | `most_common` |
| `元素们` | `elements` |
| `减去计数` | `subtract` |
| `追加左` | `appendleft` |
| `左弹出` | `popleft` |
| `入队` | `put` |
| `出队` | `get` |
| `出队不等` | `get_nowait` |
| `入队不等` | `put_nowait` |
| `任务完成` | `task_done` |
| `等待完成队列` | `join` |
| `组` | `group` |
| `分组` | `group` |
| `组们` | `groups` |
| `跨度` | `span` |
| `开始位置` | `start` |
| `结束位置` | `end` |
| `查找` | `search` |
| `匹配` | `match` |
| `全部查找` | `findall` |
| `刷新` | `flush` |
| `缓冲` | `buffer` |
| `初始化` | `__init__` |

## 4. 模块与成员

`导入 数学` → `import math`；`数学.开方(x)` → `math.sqrt(x)`。

### `哈希` → `hashlib`

| 桥语言 | Python |
| --- | --- |
| `新建摘要` | `new` |
| `二五六` | `sha256` |
| `五一二` | `sha512` |
| `一二八` | `sha1` |
| `常用摘要` | `md5` |
| `文件摘要` | `file_digest` |

### `子进程` → `subprocess`

| 桥语言 | Python |
| --- | --- |
| `运行` | `run` |
| `调用` | `call` |
| `获取输出` | `check_output` |
| `检查调用` | `check_call` |
| `管道` | `PIPE` |
| `标准输出` | `STDOUT` |
| `空设备` | `DEVNULL` |
| `超时错误` | `TimeoutExpired` |
| `完成进程` | `CompletedProcess` |

### `数学` → `math`

| 桥语言 | Python |
| --- | --- |
| `圆周率` | `pi` |
| `自然常数` | `e` |
| `欧拉数` | `e` |
| `全圆周率` | `tau` |
| `无穷` | `inf` |
| `非数` | `nan` |
| `开方` | `sqrt` |
| `平方根` | `sqrt` |
| `立方根` | `cbrt` |
| `幂` | `pow` |
| `指数` | `exp` |
| `指数减一` | `expm1` |
| `连乘` | `prod` |
| `勾股斜边` | `hypot` |
| `对数` | `log` |
| `以二为底对数` | `log2` |
| `常用对数` | `log10` |
| `对数加一` | `log1p` |
| `向下取整` | `floor` |
| `向上取整` | `ceil` |
| `整数部分` | `trunc` |
| `拆分小数` | `modf` |
| `正弦` | `sin` |
| `余弦` | `cos` |
| `正切` | `tan` |
| `反正弦` | `asin` |
| `反余弦` | `acos` |
| `反正切` | `atan` |
| `两参反正切` | `atan2` |
| `双曲正弦` | `sinh` |
| `双曲余弦` | `cosh` |
| `双曲正切` | `tanh` |
| `反双曲正弦` | `asinh` |
| `反双曲余弦` | `acosh` |
| `反双曲正切` | `atanh` |
| `角度转弧度` | `radians` |
| `弧度转角度` | `degrees` |
| `阶乘` | `factorial` |
| `组合数` | `comb` |
| `排列数` | `perm` |
| `最大公约数` | `gcd` |
| `最小公倍数` | `lcm` |
| `整数平方根` | `isqrt` |
| `精确求和` | `fsum` |
| `判断有限` | `isfinite` |
| `判断无穷` | `isinf` |
| `判断非数` | `isnan` |
| `近似相等` | `isclose` |
| `绝对值` | `fabs` |
| `复制符号` | `copysign` |
| `拆分浮点` | `frexp` |
| `拼回浮点` | `ldexp` |
| `浮点余数` | `fmod` |
| `取余` | `remainder` |
| `距离` | `dist` |

### `数据库` → `sqlite3`

| 桥语言 | Python |
| --- | --- |
| `连接` | `connect` |
| `数据错误` | `DatabaseError` |
| `完整性错误` | `IntegrityError` |
| `操作错误` | `OperationalError` |
| `行` | `Row` |

### `日志` → `logging`

| 桥语言 | Python |
| --- | --- |
| `基础配置` | `basicConfig` |
| `取记录器` | `getLogger` |
| `记录调试` | `debug` |
| `记录信息` | `info` |
| `记录警告` | `warning` |
| `记录错误` | `error` |
| `记录严重` | `critical` |
| `异常日志` | `exception` |
| `调试级别` | `DEBUG` |
| `信息级别` | `INFO` |
| `警告级别` | `WARNING` |
| `错误级别` | `ERROR` |

### `日期` → `datetime`

| 桥语言 | Python |
| --- | --- |
| `现在` | `datetime.now` |
| `今天` | `datetime.today` |
| `世界时现在` | `datetime.utcnow` |
| `从时间戳` | `datetime.fromtimestamp` |
| `解析` | `datetime.strptime` |
| `合并` | `datetime.combine` |

### `时间` → `time`

| 桥语言 | Python |
| --- | --- |
| `当前时间戳` | `time` |
| `单调时钟` | `monotonic` |
| `计数` | `perf_counter` |
| `处理器时间` | `process_time` |
| `本地时间` | `localtime` |
| `世界时` | `gmtime` |
| `格式化时间` | `strftime` |
| `解析时间` | `strptime` |
| `转时间戳` | `mktime` |
| `升序时间` | `asctime` |
| `转字符串` | `ctime` |
| `睡眠` | `sleep` |
| `延时` | `sleep` |

### `正则` → `re`

| 桥语言 | Python |
| --- | --- |
| `查找` | `search` |
| `匹配` | `match` |
| `全匹配` | `fullmatch` |
| `全部查找` | `findall` |
| `逐个查找` | `finditer` |
| `替换` | `sub` |
| `替换计数` | `subn` |
| `拆分` | `split` |
| `编译` | `compile` |
| `转义` | `escape` |
| `忽略大小写` | `IGNORECASE` |
| `多行` | `MULTILINE` |
| `点号通配` | `DOTALL` |
| `详细模式` | `VERBOSE` |
| `ASCII模式` | `ASCII` |

### `线程` → `threading`

| 桥语言 | Python |
| --- | --- |
| `线程` | `Thread` |
| `当前线程` | `current_thread` |
| `事件` | `Event` |
| `锁` | `Lock` |
| `递归锁` | `RLock` |
| `条件变量` | `Condition` |
| `定时器` | `Timer` |
| `守护线程` | `daemon` |
| `活跃数` | `active_count` |

### `统计` → `statistics`

| 桥语言 | Python |
| --- | --- |
| `平均` | `mean` |
| `中位数` | `median` |
| `低中位数` | `median_low` |
| `高中位数` | `median_high` |
| `众数` | `mode` |
| `方差` | `variance` |
| `总体方差` | `pvariance` |
| `标准差` | `stdev` |
| `总体标准差` | `pstdev` |
| `调和平均` | `harmonic_mean` |
| `几何平均` | `geometric_mean` |
| `分位数` | `quantiles` |

### `网络` → `urllib.request`

| 桥语言 | Python |
| --- | --- |
| `获取` | `urlopen` |
| `请求` | `Request` |

### `路径` → `os.path`

| 桥语言 | Python |
| --- | --- |
| `拼接` | `join` |
| `存在` | `exists` |
| `是文件` | `isfile` |
| `是目录` | `isdir` |
| `是链接` | `islink` |
| `取目录` | `dirname` |
| `取文件名` | `basename` |
| `拆分` | `split` |
| `拆扩展名` | `splitext` |
| `绝对路径` | `abspath` |
| `真实路径` | `realpath` |
| `规范化` | `normpath` |
| `共通前缀` | `commonprefix` |
| `是绝对` | `isabs` |
| `大小` | `getsize` |
| `修改时间` | `getmtime` |

### `系统` → `os`

| 桥语言 | Python |
| --- | --- |
| `环境` | `environ` |
| `取环境` | `getenv` |
| `当前目录` | `getcwd` |
| `切换目录` | `chdir` |
| `创建目录` | `makedirs` |
| `建目录` | `mkdir` |
| `列出目录` | `listdir` |
| `扫描目录` | `scandir` |
| `删除` | `remove` |
| `删除目录` | `rmdir` |
| `重命名` | `rename` |
| `覆盖重命名` | `replace` |
| `建临时文件` | `mkstemp` |
| `系统名` | `name` |
| `分隔符` | `sep` |
| `换行符` | `linesep` |
| `执行命令` | `system` |
| `取进程号` | `getpid` |

### `运行环境` → `sys`

| 桥语言 | Python |
| --- | --- |
| `参数` | `argv` |
| `标准输入` | `stdin` |
| `标准输出` | `stdout` |
| `标准错误` | `stderr` |
| `导入路径` | `path` |
| `模块表` | `modules` |
| `已加载` | `modules` |
| `版本` | `version` |
| `版本号` | `version_info` |
| `平台` | `platform` |
| `字节序` | `byteorder` |
| `最大整数` | `maxsize` |
| `可执行文件` | `executable` |
| `实现名` | `implementation` |
| `退出` | `exit` |
| `递归上限` | `getrecursionlimit` |
| `设置递归上限` | `setrecursionlimit` |
| `默认编码` | `getdefaultencoding` |
| `文件系统编码` | `getfilesystemencoding` |
| `设置开关` | `setswitchinterval` |
| `开关间隔` | `getswitchinterval` |

### `迭代工具` → `itertools`

| 桥语言 | Python |
| --- | --- |
| `排列` | `permutations` |
| `组合` | `combinations` |
| `组合含重复` | `combinations_with_replacement` |
| `笛卡尔积` | `product` |
| `累计` | `accumulate` |
| `分组` | `groupby` |
| `切片` | `islice` |
| `链` | `chain` |
| `压平` | `chain.from_iterable` |
| `无限计数` | `count` |
| `无限循环` | `cycle` |
| `无限重复` | `repeat` |
| `压缩长` | `zip_longest` |
| `成对` | `pairwise` |

### `队列` → `queue`

| 桥语言 | Python |
| --- | --- |
| `队列` | `Queue` |
| `后进先出队列` | `LifoQueue` |
| `优先队列` | `PriorityQueue` |
| `简单队列` | `SimpleQueue` |
| `队空` | `Empty` |
| `队满` | `Full` |

### `随机` → `random`

| 桥语言 | Python |
| --- | --- |
| `种子` | `seed` |
| `随机浮点` | `random` |
| `均匀随机` | `uniform` |
| `随机整数` | `randint` |
| `选择` | `choice` |
| `多选` | `choices` |
| `样本` | `sample` |
| `洗牌` | `shuffle` |
| `高斯` | `gauss` |
| `打乱顺序` | `shuffle` |

### `集合工具` → `collections`

| 桥语言 | Python |
| --- | --- |
| `计数器` | `Counter` |
| `默认字典` | `defaultdict` |
| `双端队列` | `deque` |
| `有序字典` | `OrderedDict` |
| `命名元组` | `namedtuple` |
| `链映射` | `ChainMap` |

## 5. 句式糖（整行重写）

正则匹配整行，按模板生成一行 Python；行号不变。`«…»` 是占位符。

| 桥语言写法 | 生成的 Python |
| --- | --- |
| `«词» [？]：` | `桥帮助("{词}")` |
| `重复执行直到 «条件» :` | `while not ({条件}):` |
| `重复执行 «次数» 次：` | `for _ in range({次数}):` |
| `重复 «次数» 次：` | `for _ in range({次数}):` |
| `永久循环 / 死循环：` | `while True:` |
| `只要 «条件» 就重复：` | `while {条件}:` |
| `对于 每个 «变量» 在 «序列»：` | `for {变量} in {序列}:` |
| `遍历 «序列» 中的 每个 «变量»：` | `for {变量} in {序列}:` |
| `对 «序列» 中的每一项：` | `for _ in {序列}:` |
| `如果 «条件» 那么 / 则：` | `if {条件}:` |
| `否则如果 «条件» 那么 / 则：` | `elif {条件}:` |
| `否则 的话：` | `else:` |
| `定义函数 «名» «参数»）])：` | `def {名}{参数}:` |
| `尝试执行：` | `try:` |
| `无论如何：` | `finally:` |
| `捕获异常时：` | `except:` |
| `捕获 «类型» 时：` | `except {类型}:` |
| `跳出循环：` | `break` |
| `继续下一次循环：` | `continue` |
| `结束本次循环 / 进入下一次循环：` | `continue` |
| `直到 «条件» 为止 :` | `while not ({条件}):` |
| `一直重复 / 一直循环 :` | `while True:` |
| `等待 «条件» 直到 :` | `while not ({条件}): pass` |
| `当 «条件» 就 «语句»：` | `while {条件}: {语句}` |
| `如果 «条件» 就 «语句»：` | `if {条件}: {语句}` |
| `否则 «语句»：` | `else: {语句}` |
| `把 «目标» 设为 / 设定为 / 赋值成 «值»：` | `{目标} = {值}` |
| `设 «目标» 为 «值»：` | `{目标} = {值}` |
| `将 «目标» 设为 / 设定为 «值»：` | `{目标} = {值}` |
| `将 «目标» 增加 «值»：` | `{目标} += {值}` |
| `将 «目标» 减少 «值»：` | `{目标} -= {值}` |
| `将 «目标» 乘以 «值»：` | `{目标} *= {值}` |
| `将 «目标» 除以 «值»：` | `{目标} /= {值}` |
| `将 «目标» 取模 «值»：` | `{目标} %= {值}` |
| `将 «目标» 乘方 «值»：` | `{目标} **= {值}` |
| `将 «目标» 整除商 «值»：` | `{目标} //= {值}` |
| `给 «目标» 加上 «值»：` | `{目标} += {值}` |
| `给 «目标» 减去 «值»：` | `{目标} -= {值}` |
| `输出 / 打印 «参数»：` | `print({参数})` |
| `如果 / 若 / 假如 / 倘若 / 当 是主程序：` | `if __name__ == '__main__':` |
| `捕获 «类型» 记作 «名»：` | `except {类型} as {名}:` |
| `定义 初始化 «参数»）])：` | `def __init__{参数}:` |
| `定义 显示 «参数»）])：` | `def __str__{参数}:` |
| `定义 表示 «参数»）])：` | `def __repr__{参数}:` |

## 6. 桥语言独有（Python 没有的东西）

| 写法 | 作用 |
| --- | --- |
| `标记` | 声明跳转目标，只能写在模块顶层或函数/类的第一层 |
| `跳转到` | 跳到某个标记（也可写 跳转/goto） |
| `运行` | 运行另一个 .bridge，等它结束并拿返回 |
| `并行` | 开线程跑另一个 .bridge，不等 |
| `等待完成` | 等待并行任务结束 |
| `读取` | .json 返回 JSON 对象、.csv 返回表格，其它返回文档 |
| `新建文档` | 新建文件；.json 收 dict/list，.csv 收二维表 |
| `文件` | 基类：文件名/路径/大小/存在/后缀/改名/复制到/删除自己 |
| `文档` | 文件子类：内容/追加/下标/字符串化 |
| `表格` | CSV 二维表：表头/行数/行/列/追加行/保存 |

示例：

```python
计数 = 0
标记 回头
计数 += 1
如果 计数 小于 3:
    跳转到 回头

甲 = 运行("子程序.bridge")      # 等它跑完，拿 `返回` 值
并行("子程序.bridge")           # 开线程，不等
等待完成()                      # 等上面那些收尾

文档 = 读取("./a.txt")           # .txt → 文档对象
文档.追加("一行")                # .内容/@items 已接好
配置 = 读取("./c.json")          # .json → 可按字段点的对象
配置.端口 = 8080
配置.保存()
表 = 读取("./x.csv")             # .csv → 表格
输出（表.列("分数")）
```

## 7. 常见错误 → 改法

| 现象 | 原因 | 改法 |
| --- | --- | --- |
| `名字错误：name XXX is not defined` | 变量名撞了规则词被翻掉 | 换个名字，或 `python 桥.py 查 XXX` 看它被翻成什么 |
| `属性错误：… 没有 append` | 你在自己的类/模块上用了 `.追加` | 要么改名（`.新增`），要么类里挂 `append = 追加` |
| `expected '('` 指到 `定义 现在()` | `现在` 是 `日期.现在` 的成员词 | 函数改名（`此刻`） |
| `标记写在了 if 里面` | 标签缩进太深 | 挪到函数/模块第一层 |
| `该标记不存在` | 拼错或跨函数 | 检查拼写；跳转不能跨函数 |
| REPL 里 `标记` 不生效 | REPL 不保留标签状态 | 写进 `.bridge` 文件跑 |

## 8. 完整小例子

```python
导入 数学

定义 圆面积(半径):
    返回 数学.圆周率 * 半径 ** 2

输出（"面积：", 圆面积(2)）

尝试执行:
    输出（1 / 0）
捕获 除零错误 作为 错误:
    输出（"算错了：", 错误）
```

对应 Python：

```python
import math

def 圆面积(半径):
    return math.pi * 半径 ** 2

print("面积：", 圆面积(2))

try:
    print(1 / 0)
except ZeroDivisionError as 错误:
    print("算错了：", 错误)
```

## 9. 机器可读

- `docs/桥语言规则.json`：上面所有映射的 JSON 版；
- `python 桥.py 查 <词>` / `python 桥.py 规则`：命令行查询；
- `python 桥.py 查看 <文件.bridge>`：看转译后的 Python（对照调试最快）。

