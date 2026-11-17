"""`桥运行.py` 的 ASCII 别名（给 .bat 用）

为什么要有它：cmd 读批处理文件用 OEM 代码页（中文系统是 GBK），
批处理里写中文文件名很容易变乱码，所以启动器脚本一律用 ASCII 名：
`桥.py` ↔ `bridge.py`、`桥运行.py` ↔ `bridge_run.py`。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from 桥运行 import main  # noqa: E402

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
