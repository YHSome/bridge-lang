"""方法规则：对象方法名的中文化（只在「点号之后」生效）

这是**独立于「成员」表**的一张表，原因很实际：

| 写法 | 走哪张表 | 结果 |
|---|---|---|
| `数据.排序()` | `方法.排序` → `sort` | `数据.sort()` |
| `排序(数据)` | `内建.排序` → `sorted` | `sorted(数据)` |

同一个中文词，点号后面是**方法**、光着写是**内建函数**，语义不同，所以必须分开。

同样支持**多对一**：`追加 / 添加 / 加进去` 都是 `append`。

适用范围：任意 `对象.中文名` —— 不管是列表、字典、字符串还是你自己类的实例。
代价：如果你自己定义了一个叫 `追加` 的方法，这里也会把它改成 `append`，
所以**别用表里的词给你的方法命名**（详见 架构.md 5.8）。
"""

方法 = {
    # ---------- 列表 ----------
    '追加': 'append',
    '添加': 'append',
    '加进去': 'append',
    '扩展': 'extend',
    '批量添加': 'extend',
    '插入': 'insert',
    '移除': 'remove',
    '去掉': 'remove',
    '弹出': 'pop',
    '取出': 'pop',
    '清空': 'clear',
    '拷贝': 'copy',
    '复制': 'copy',
    '排序': 'sort',
    '反转': 'reverse',
    '倒序': 'reverse',
    '计数': 'count',
    '索引': 'index',
    # ---------- 字典 ----------
    '内容': 'items',
    '条目': 'items',
    '键': 'keys',
    '键列表': 'keys',
    '值': 'values',
    '值列表': 'values',
    '获取': 'get',
    '取值': 'get',
    '更新': 'update',
    '合并更新': 'update',
    '设置默认': 'setdefault',
    # ---------- 字符串 ----------
    '拆分': 'split',
    '分割': 'split',
    '替换': 'replace',
    '去除空白': 'strip',
    '去空格': 'strip',
    '大写': 'upper',
    '转大写': 'upper',
    '小写': 'lower',
    '转小写': 'lower',
    '开头是': 'startswith',
    '结尾是': 'endswith',
    '连接': 'join',
    '格式化': 'format',
    '找到': 'find',
    # ---------- 文件 / 其他 ----------
    '读': 'read',
    '读取': 'read',
    '写': 'write',
    '写入': 'write',
    '关闭': 'close',
    '格式化日期': 'strftime',
    '星期几': 'weekday',
    '日期部分': 'date',
    '天数': 'days',
    '返回码': 'returncode',
    '标准输出': 'stdout',
    '标准错误': 'stderr',
    # ---- 字符串 / 编码 / 对齐 ----
    '编码': 'encode',
    '解码': 'decode',
    '十六进制': 'hex',
    '左对齐': 'ljust',
    '右对齐': 'rjust',
    '居中': 'center',
    '补零': 'zfill',
    '标题化': 'title',
    '首字母大写': 'capitalize',
    '去前缀': 'removeprefix',
    '去后缀': 'removesuffix',
    '是否数字': 'isdigit',
    '是否字母': 'isalpha',
    '是否空白': 'isspace',
    '是否数字字母': 'isalnum',
    '十六进制摘要': 'hexdigest',
    '摘要值': 'digest',
    '出现最多': 'most_common',
    '元素们': 'elements',
    '减去计数': 'subtract',
    '追加左': 'appendleft',
    '左弹出': 'popleft',
    '入队': 'put',
    '出队': 'get',
    '出队不等': 'get_nowait',
    '入队不等': 'put_nowait',
    '任务完成': 'task_done',
    '等待完成队列': 'join',
    '组': 'group',
    '分组': 'group',
    '组们': 'groups',
    '跨度': 'span',
    '开始位置': 'start',
    '结束位置': 'end',
    '查找': 'search',
    '匹配': 'match',
    '全部查找': 'findall',
    '刷新': 'flush',
    '缓冲': 'buffer',
    # ---------- 可读性：对象初始化 ----------
    # `定义 初始化(自己, …)` 由语法糖翻成 def __init__；这里是给 `父类.初始化()` 用的
    '初始化': '__init__',
}
