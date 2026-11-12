"""ASCII 名称的入口（给 bat/快捷方式用，避免命令行代码页把中文文件名吃掉）

    python bridge.py 运行 你的程序.bridge

等价于 `python 桥.py 运行 你的程序.bridge`。
"""

import sys
from pathlib import Path

sys.dont_write_bytecode = True   # 便携包别在用户项目里生 __pycache__

根目录 = Path(__file__).resolve().parent
if str(根目录) not in sys.path:
    sys.path.insert(0, str(根目录))

import 桥  # noqa: E402

if __name__ == '__main__':
    raise SystemExit(桥.main(sys.argv[1:]))
