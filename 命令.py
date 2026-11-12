"""命令行入口（pip 安装后就是 `bridge` / `桥` 两个命令）

setuptools 的 console_scripts 只能调"无参函数"，而 `桥.main` 要收参数列表，
所以这里包一层。
"""

import sys


def 入口() -> None:
    import 桥

    raise SystemExit(桥.main(sys.argv[1:]))


if __name__ == '__main__':
    sys.path.insert(0, '.')
    入口()
