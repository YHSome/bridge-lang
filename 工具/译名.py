"""英文标识符 → 中文标识符（给 `反向译 --译名` 用）

做法是「词根拼装」：`submit_id` → `提交` + `编号` → `提交编号`。
词根只收**常用词**，拼不出来就返回 `None`（保持英文）——宁可留英文，也不要翻出
`ensure_dirs` → `确保目录们` 这种读起来更费劲的名字。

三条约定：

1. **拼不出来就放过**：`h`、`p`、`r`、`x1`、`LARGE_INTEGER` 这类不翻；
2. **复数按词根表**：`files` / `rows` / `names` 都有单独条目（翻成「文件列表」这类不会更清楚，
   统一翻成「文件」「行」「名字」）；未知复数去掉 `s` 再试；
3. **专有名词不动**：`Handler`、`JSON`、`HTTP`、`sqlite3` 等，`词根` 里刻意**不登记**。
"""

from __future__ import annotations

import re

# 词根：小写词 → 中文
词根: dict[str, str] = {
    # ---- 通用 ----
    'a': '', 'the': '', 'of': '', 'in': '', 'to': '', 'by': '', 'for': '', 'on': '', 'at': '',
    'is': '是', 'has': '有', 'have': '有', 'can': '可', 'all': '全部', 'any': '任意',
    'new': '新', 'old': '旧', 'cur': '当前', 'current': '当前', 'prev': '上一个', 'next': '下一个',
    'first': '第一', 'last': '最后', 'one': '一', 'two': '二', 'three': '三',
    'min': '最小', 'max': '最大', 'mid': '中间', 'low': '低', 'high': '高', 'hi': '高', 'lo': '低',
    'small': '小', 'big': '大', 'large': '大', 'tiny': '微小', 'full': '完整',
    'id': '编号', 'idx': '下标', 'index': '下标', 'pos': '位置', 'offset': '偏移', 'start': '开始',
    'end': '结束', 'begin': '开始', 'from': '起始', 'until': '直到', 'total': '总', 'sum': '和',
    'count': '计数', 'cnt': '计数', 'num': '数量', 'num': '数量', 'n': '数量', 'len': '长度',
    'length': '长度', 'size': '大小', 'sizes': '大小', 'capacity': '容量', 'limit': '上限',
    'limits': '上限', 'cap': '上限', 'cap_': '上限',
    'home': '首页', 'banner': '横幅', 'dispatch': '分发', 'mine': '我的', 'nav': '导航',
    'filter': '筛选', 'filters': '筛选', 'toggle': '切换', 'reorder': '重排', 'rejudge': '重评',
    'import': '导入', 'export': '导出', 'pdf': 'PDF', 'md': 'MD', 'inline': '内联',
    'discard': '丢弃', 'materialize': '落地', 'orphan': '孤儿', 'orphans': '孤儿',
    'recover': '恢复', 'pump': '泵送', 'kill': '终止', 'start': '开始', 'stop': '停止',
    'gen': '生成', 'brief': '简介', 'looks': '看起来', 'like': '像', 'own': '自有',
    'legacy': '旧版', 'daemon': '守护', 'thread': '线程', 'data_': '数据',
    'name': '名字', 'names': '名字', 'title': '标题', 'label': '标签', 'tag': '标签',
    'text': '文本', 'txt': '文本', 'content': '内容', 'body': '正文', 'line': '行', 'lines': '行',
    'row': '行', 'rows': '行', 'col': '列', 'cols': '列', 'cell': '单元格', 'cells': '单元格',
    'item': '数据项', 'items': '条目', 'entry': '条目', 'entries': '条目', 'part': '片段',
    'parts': '片段', 'piece': '片段', 'chunk': '块', 'chunks': '块', 'block': '块',
    'group': '分组', 'groups': '分组', 'pair': '配对', 'pairs': '配对', 'list': '列表',
    'dict': '字典', 'map': '映射', 'set': '集合', 'seq': '序列', 'arr': '数组', 'array': '数组',
    'word': '词', 'words': '词', 'key': '键', 'keys': '键', 'val': '值', 'value': '值',
    'values': '值', 'raw': '原始', 'data': '数据', 'info': '信息', 'detail': '详情',
    'details': '详情', 'desc': '描述', 'description': '描述', 'note': '备注', 'notes': '备注',
    'brief': '简介', 'summary': '摘要', 'spec': '规格', 'config': '配置', 'conf': '配置',
    'cfg': '配置', 'opts': '选项', 'opt': '选项', 'options': '选项', 'default': '默认',
    'defaults': '默认值', 'arg': '参数', 'args': '参数', 'argv': '参数', 'params': '参数',
    'kw': '关键字参数', 'kwargs': '关键字参数',
    # ---- 领域：用户 / 队伍 / 权限 ----
    'user': '用户', 'users': '用户', 'username': '用户名', 'account': '账号', 'accounts': '账号',
    'pwd': '密码', 'password': '密码', 'passwords': '密码', 'salt': '盐值', 'hash': '散列',
    'role': '角色', 'roles': '角色', 'team': '队伍', 'teams': '队伍', 'member': '成员',
    'members': '成员', 'student': '学生', 'staff': '教工', 'jury': '裁判', 'teacher': '教师',
    'admin': '管理员', 'peer': '同行', 'guest': '访客', 'session': '会话', 'sessions': '会话',
    'token': '令牌', 'cookie': '饼干', 'login': '登录', 'logout': '登出', 'auth': '鉴权',
    'csrf': '防伪令牌', 'permission': '权限', 'access': '访问',
    # ---- 领域：题目 / 评测 ----
    'prob': '题目', 'probs': '题目', 'problem': '题目', 'problems': '题目', 'statement': '题面',
    'stmts': '题面', 'stmt': '题面', 'sample': '样例', 'samples': '样例', 'test': '测试',
    'tests': '测试', 'testdata': '测试数据', 'data_': '数据', 'judge': '评测', 'judged': '已评测',
    'sub': '提交', 'subs': '提交', 'submit': '提交', 'submission': '提交', 'submissions': '提交',
    'score': '得分', 'scores': '得分', 'scoreboard': '排行榜', 'rank': '排名', 'ranked': '已排名',
    'rating': '评分', 'verdict': '判定', 'verdicts': '判定', 'lang': '语言', 'langs': '语言',
    'language': '语言', 'languages': '语言', 'code': '代码', 'codes': '代码', 'src': '源码',
    'source': '源码', 'solution': '题解', 'answer': '答案', 'ans': '答案', 'output': '输出',
    'outputs': '输出', 'input': '输入', 'inputs': '输入', 'stdin': '标准输入',
    'stdout': '标准输出', 'stderr': '标准错误', 'compile': '编译', 'compiled': '已编译',
    'run': '运行', 'runs': '运行', 'runner': '运行器', 'sandbox': '沙箱', 'kernel': '内核',
    'exe': '可执行文件', 'executable': '可执行文件', 'limit': '限制', 'timeout': '超时',
    'deadline': '截止', 'time': '时间', 'times': '时间', 'timestamp': '时间戳', 'ts': '时间戳',
    'ms': '毫秒', 'elapsed': '耗时', 'duration': '时长', 'interval': '间隔', 'wait': '等待',
    'sleep': '睡眠', 'delay': '延时', 'memory': '内存', 'mem': '内存', 'mem_': '内存',
    'cpu': '处理器', 'wall': '墙钟', 'peak': '峰值', 'usage': '用量', 'resource': '资源',
    'job': '任务', 'jobs': '任务', 'task': '任务', 'tasks': '任务', 'queue': '队列',
    'pending': '待处理', 'done': '完成', 'finished': '已结束', 'active': '进行中',
    'status': '状态', 'state': '状态', 'stage': '阶段', 'step': '步骤', 'phase': '阶段',
    'result': '结果', 'results': '结果', 'res': '结果', 'rc': '返回码', 'ret': '返回',
    'returncode': '返回码', 'exit': '退出', 'err': '错误', 'error': '错误', 'errors': '错误',
    'msg': '消息', 'msgs': '消息', 'message': '消息', 'warning': '警告', 'warn': '警告',
    'ok': '成功', 'success': '成功', 'fail': '失败', 'failed': '失败', 'failure': '失败',
    'bad': '坏', 'good': '好', 'valid': '有效', 'invalid': '无效', 'missing': '缺失',
    'empty': '空', 'exist': '存在', 'exists': '存在', 'existing': '已有', 'created': '已创建',
    'updated': '已更新', 'deleted': '已删除', 'removed': '已移除', 'added': '已添加',
    'changed': '已变更', 'enabled': '已启用', 'disabled': '已禁用', 'visible': '可见',
    'hidden': '隐藏', 'show': '显示', 'shown': '已显示', 'display': '显示', 'hide': '隐藏',
    # ---- 领域：文件 / 路径 ----
    'path': '路径', 'paths': '路径', 'file': '文件', 'files': '文件', 'filename': '文件名',
    'dir': '目录', 'dirs': '目录', 'folder': '文件夹', 'root': '根', 'base': '基础',
    'ext': '扩展名', 'suffix': '后缀', 'prefix': '前缀', 'stem': '主干', 'stems': '主干',
    'zip': '压缩包', 'archive': '归档', 'upload': '上传', 'download': '下载', 'save': '保存',
    'saved': '已保存', 'load': '读取', 'loaded': '已读取', 'read': '读', 'write': '写',
    'open': '打开', 'close': '关闭', 'copy': '复制', 'move': '移动', 'delete': '删除',
    'remove': '移除', 'create': '创建', 'make': '生成', 'build': '构建', 'ensure': '确保',
    'init': '初始化', 'setup': '装配', 'reset': '重置', 'clear': '清空', 'clean': '清理',
    'migrate': '迁移', 'migration': '迁移', 'schema': '表结构', 'table': '表', 'tables': '表',
    'query': '查询', 'rowcount': '行数', 'fetch': '取回', 'execute': '执行', 'commit': '提交事务',
    # ---- 领域：Web ----
    'web': '网页', 'url': '网址', 'uri': '地址',
    'host': '主机', 'port': '端口', 'endpoint': '端点', 'route': '路由', 'routes': '路由',
    'router': '路由器', 'request': '请求', 'req': '请求', 'response': '响应', 'resp': '响应',
    'header': '请求头', 'headers': '请求头', 'params_': '参数', 'payload': '载荷',
    'form': '表单', 'field': '字段', 'fields': '字段', 'param': '参数', 'value_': '值',
    'page': '页面', 'pages': '页面', 'view': '视图', 'template': '模板', 'render': '渲染',
    'rendered': '已渲染', 'script': '脚本',
    'static': '静态', 'style': '样式', 'color': '颜色', 'font': '字体', 'icon': '图标',
    'img': '图片', 'image': '图片', 'logo': '标志', 'logos': '标志', 'nav': '导航',
    'menu': '菜单', 'button': '按钮', 'btn': '按钮', 'link': '链接', 'href': '链接地址',
    'redirect': '重定向', 'cookie_': '饼干', 'cors': '跨域', 'csrf_': '防伪',

    # ---- 领域：AI ----
    'ai': '智能', 'model': '模型', 'models': '模型', 'prompt': '提示词', 'chat': '对话',
    'messages': '消息', 'reply': '回复', 'generate': '生成', 'generator': '生成器',
    'temperature': '温度', 'max_tokens': '最大词元', 'token_': '词元', 'draft': '草稿',
    'preview': '预览', 'review': '复核', 'check': '检查', 'verify': '校验', 'validate': '校验',
    'normalize': '规范化', 'parse': '解析', 'parsed': '已解析', 'format': '格式化',
    'fmt': '格式化', 'join': '连接', 'split': '拆分', 'merge': '合并', 'concat': '拼接',
    'strip': '去空白', 'stripped': '已去空白', 'escape': '转义', 'esc': '转义',
    'escape_': '转义', 'slug': '短名', 'hash_': '散列', 'digest': '摘要', 'sign': '签名',
    'random': '随机', 'seed': '种子', 'rng': '随机数', 'rnd': '随机',
    'lock': '锁', 'mutex': '互斥锁', 'thread': '线程', 'threads': '线程', 'worker': '工作器',
    'workers': '工作器', 'pool': '池', 'executor': '执行器', 'daemon': '守护',
    'process': '进程', 'proc': '进程', 'pid': '进程编号', 'handle': '句柄', 'handler': '处理器',
    'event': '事件', 'events': '事件', 'callback': '回调', 'hook': '钩子', 'trigger': '触发',
    'watchdog': '看门狗', 'watch': '监视', 'monitor': '监视', 'poll': '轮询', 'retry': '重试',
    'loop': '循环', 'forever': '永久', 'timer': '计时器', 'clock': '时钟', 'now': '现在',
    'today': '今天', 'date': '日期', 'datetime': '日期时间', 'day': '天', 'hour': '小时',
    'minute': '分钟', 'second': '秒', 'sec': '秒', 'msec': '毫秒', 'usec': '微秒',
    'tz': '时区', 'utc': '世界时', 'local': '本地', 'zone': '区域',
    # ---- 领域：统计 / 分数 ----
    'point': '分数', 'points': '分数', 'pts': '分数', 'grade': '等级', 'level': '级别',
    'ac': '通过', 'wa': '答案错', 'tle': '超时', 'mle': '超内存', 're': '运行错', 'ce': '编译错',
    'ole': '输出超限', 'pe': '格式错', 'spj': '特判', 'subtask': '子任务', 'given': '给定',
    'expect': '期望', 'expected': '期望', 'actual': '实际', 'tolerance': '容差', 'tol': '容差',
    'compare': '比较', 'diff': '差异', 'match': '匹配', 'collect': '收集', 'pick': '挑选',
    'choose': '选择', 'choice': '选择', 'select': '选择', 'sort': '排序', 'sorted': '已排序',
    'order': '顺序', 'rank_': '排名', 'roll': '滚榜', 'board': '榜单', 'contest': '比赛',
    'freeze': '封榜', 'frozen': '已封榜', 'announce': '公告', 'notice': '通知',
    'submitters': '提交者', 'submitter': '提交者', 'solved': '已解', 'tried': '尝试过',
    'first_blood': '一血', 'live': '实时', 'recent': '最近', 'history': '历史',
    'stats': '统计', 'stat': '统计', 'metric': '指标', 'metrics': '指标', 'ratio': '比例',
    'percent': '百分比', 'pct': '百分比', 'factor': '系数', 'weight': '权重',
    # ---- 常用动词/形容词 ----
    'add': '添加', 'append': '追加', 'insert': '插入', 'update': '更新', 'edit': '编辑',
    'fetch_': '取回', 'get': '获取', 'set_': '设置', 'has_': '有', 'is_': '是',
    'to': '', 'as': '作为', 'with': '带', 'without': '不带', 'allow': '允许',
    'deny': '拒绝', 'require': '要求', 'optional': '可选', 'required': '必需',
    'available': '可用', 'ready': '就绪', 'busy': '忙碌', 'free': '空闲', 'used': '已用',
    'total_': '总', 'current_': '当前', 'final': '最终', 'temporary': '临时', 'temp': '临时',
    'manual': '手动', 'auto': '自动', 'automatic': '自动', 'quick': '快速', 'fast': '快',
    'slow': '慢', 'early': '提前', 'late': '延迟', 'again': '再次', 'single': '单个',
    'single_line': '单行', 'multi': '多个', 'multi_line': '多行', 'n_': '数量',
}

特例: dict[str, str] = {
    'workdir': '工作目录', 'first_blood': '一血', 'ok': '成功', 'fail': '失败',
    'log': '日志', 'dir': '目录', 'file': '文件', 'path': '路径',
    'csrf': '防伪令牌', 'sqlite': '数据库', 'db': '数据库', 'rowid': '行号',
    # ---- 单字母：读代码时最碍眼的一类 ----
    'h': '处理器', 'p': '题目', 'r': '数据行', 's': '文字', 'i': '序号',
    'n': '数量', 't': '正文', 'd': '目录', 'f': '文件', 'k': '名称',
    'v': '单条', 'm': '匹配', 'c': '次数', 'u': '网址', 'w': '写出口',
    'e': '出错', 'x': '元素', 'y': '附加项', 'z': '末尾项', 'q': '查询串',
    'j': '内序号', 'b': '字节块', 'a': '首项', 'g': '分组',
    # ---- 常见缩写 ----
    'conn': '数据库连接', 'cur': '游标', 'rc': '状态码', 'kw': '附加参数',
    'fmt': '格式串', 'buf': '缓冲区', 'msg': '消息', 'cfg': '配置',
    'src': '源码', 'dst': '目标', 'ans': '答案', 'exe': '可执行文件',
    'pid': '进程号', 'ids': '编号列表', 'tmp': '临时值', 'ret': '结果值',
    'err': '错误', 'exc': '错误对象', 'tb': '追踪信息', 'fn': '函数',
    'cls': '类别', 'arg': '参数', 'val': '数值', 'num': '数量',
    'cnt': '计数', 'sum': '合计', 'avg': '平均', 'max': '最大', 'min': '最小',
    'zf': '压缩包', 'ifile': '读入文件', 'afile': '答案文件', 'pdir': '题目目录',
    'sid': '提交编号', 'uid': '用户编号', 'tl': '时限', 'tl_ms': '时限毫秒',
    'ml': '内存上限', 'ml_mb': '内存兆字节', 'outs': '结果集合', 'cand': '候选',
    'cands': '候选列表', 'ap': '参数解析', 'kernel32': '内核库', 'now': '此刻',
    'work': '工作', 'key': '键名', 'pairs': '配对表', 'item': '数据项',
    'items': '数据项表', 'exc': '错误对象', 'err': '错误', 'tb': '追踪',
    'out': '结果输出', 'stdout': '标准输出', 'draft': '草稿', 'pdf': '文档',
    'head': '头部', 'tail': '尾部', 'cut': '切割', 'plan': '计划', 'got': '得到',
    'sql': '查询语句', 'time_ms': '耗时毫秒', 'ordn': '次序编号', 'sel_v': '选择值',
    'sel_p': '选择题目', 'urow': '用户数据行', 'tcols': '表头列', 'pcols': '题目列',
    'note0': '备注原值', 'lv': '等级', 'rnd': '轮次',
    'connect': '建立连接', 'executescript': '执行脚本', 'q1': '单行查询',
    'execute': '执行语句', 'commit': '提交事务', 'rollback': '回滚',
    'cursor': '游标', 'rowid': '行标识', 'lastrowid': '末行标识',
    'idx': '位次', 'pos': '位置', 'len': '尺寸', 'sz': '尺寸', 'sz_': '尺寸',
    'pp': '像素', 'pk': '主键', 'fk': '外键', 'op': '操作', 'ops': '操作',
    'judge': '评测', 'sandbox': '沙箱', 'ai': '智能', 'board': '榜单',
    'web': '网页', 'ui': '界面', 'interactive': '交互',
    'paths': '路径', 'probs': '题目', 'board_roll': '滚榜',
    'utils': '工具', 'tools': '工具', 'common': '公共', 'core': '核心',
    'base': '基础', 'main': '主', 'app': '应用', 'server': '服务',
    'client': '客户端', 'db_': '数据库', 'sql_': '查询语句',
}

_词边界 = re.compile(r'_+')


def _拆(名: str) -> list[str]:
    部分 = [p.lower() for p in _词边界.split(名) if p]
    # camelCase 也拆一下：ensureDirs → ensure / dirs
    拆好: list[str] = []
    for p in 部分:
        if p.islower():
            拆好.append(p)
            continue
        for 片 in re.findall(r'[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|\d+', 名):
            拆好.append(片.lower())
        break
    return 拆好 or [名.lower()]


def 译(名: str) -> str | None:
    """英文标识符 → 中文；翻不出来就返回 None（保持英文）"""
    if not 名 or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', 名):
        return None
    if 名.startswith('__') and 名.endswith('__'):
        return None                        # 双下划线：Python 的钩子名，绝不能动
    前缀 = ''
    主体 = 名
    if 名.startswith('_'):
        前缀 = '_'
        主体 = 名[1:]
    if 主体.lower() in 特例:
        return 前缀 + 特例[主体.lower()]
    全大写 = 主体.isupper()
    小写名 = 主体.lower()
    部分 = 全大写 and 小写名.split('_') or _拆(主体)
    if len(部分) == 1 and len(部分[0]) <= 2 and 部分[0] not in 特例 and 部分[0] not in 词根:
        return None                        # i/x/h/p 这类单字母变量不翻（翻了更难读）
    中文片: list[str] = []
    for p in 部分:
        if p.isdigit():
            中文片.append(p)
            continue
        中 = 词根.get(p) or 特例.get(p)
        if 中 is None and p.endswith('s') and p[:-1] in 词根:
            中 = 词根[p[:-1]]            # 未知复数：去 s 再试（files→file）
        if 中 is None:
            return None
        中文片.append(中)
    结果 = 前缀 + ''.join(中文片)
    if 结果 in ('', 前缀):
        return None
    return 结果


def 分配(名单) -> tuple[dict[str, str], dict[str, str]]:
    """给一批名字分配中文名，处理"两个英文撞同一个中文"的情况

    返回 (英文→中文, 提示信息)。撞名时：先到的保留原名，后到的加序号（`提交2`）。
    """
    映射: dict[str, str] = {}
    占用: dict[str, str] = {}
    冲突: dict[str, str] = {}
    for 名 in sorted(名单):
        中文 = 译(名)
        if not 中文:
            continue
        if 中文 in 占用:
            序号 = 2
            while f'{中文}{序号}' in 占用:
                序号 += 1
            冲突[名] = f'{中文}{序号}'
            中文 = f'{中文}{序号}'
        占用[中文] = 名
        映射[名] = 中文
    return 映射, 冲突
