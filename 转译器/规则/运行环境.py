"""sys 规则：运行环境的中文化

方言写法：

    导入 运行环境

    参数 = 运行环境.参数                      # sys.argv
    数据 = 运行环境.标准输入.缓冲.读()          # sys.stdin.buffer.read()
    运行环境.标准输出.写("你好\\n")            # sys.stdout.write(...)
    运行环境.退出(0)                          # sys.exit(0)

模块别名用「运行环境」而不是「系统」——「系统」已经给了 `os`（系统.创建目录、系统.环境），
一个中文词只能对应一个英文模块，否则 `导入 系统` 会分不清是 os 还是 sys。
"""

模块 = {
    '运行环境': 'sys',
}

成员 = {
    '运行环境': {
        # 输入输出
        '参数': 'argv',
        '标准输入': 'stdin',
        '标准输出': 'stdout',
        '标准错误': 'stderr',
        # 路径与模块
        '导入路径': 'path',
        '模块表': 'modules',
        '已加载': 'modules',
        # 版本与环境
        '版本': 'version',
        '版本号': 'version_info',
        '平台': 'platform',
        '字节序': 'byteorder',
        '最大整数': 'maxsize',
        '可执行文件': 'executable',
        '实现名': 'implementation',
        # 控制
        '退出': 'exit',
        '递归上限': 'getrecursionlimit',
        '设置递归上限': 'setrecursionlimit',
        '默认编码': 'getdefaultencoding',
        '文件系统编码': 'getfilesystemencoding',
        '设置开关': 'setswitchinterval',
        '开关间隔': 'getswitchinterval',
    },
}
