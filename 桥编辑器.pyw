"""桥语言编辑器 · 双击启动器（pythonw 运行，不带黑窗）

Windows 把 .pyw 关联给 pythonw.exe，所以双击这个文件就是"点开就能写"。
也可以给它传文件：`桥编辑器.pyw 示例/混写演示.bridge`

真正的界面在 `转译器/编辑器.py`，这里只做三件事：
定位项目根 → 把根塞进 sys.path → 调 main()。
"""

import sys
from pathlib import Path

项目根 = Path(__file__).resolve().parent
if str(项目根) not in sys.path:
    sys.path.insert(0, str(项目根))

try:
    from 转译器.编辑器 import main
except Exception:                     # pythonw 没有控制台，出错要弹个框，不然是"点了没反应"
    import tkinter.messagebox as 消息框

    消息框.showerror('桥语言编辑器启动失败', __import__('traceback').format_exc())
    raise SystemExit(1)

raise SystemExit(main(sys.argv))
