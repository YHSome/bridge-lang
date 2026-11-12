# 桥语言 VS Code 扩展

`.bridge` 文件的高亮 + 运行，轻量版（完整 IDE 还是自带的 `桥编辑器.pyw`）。

## 安装（本地）

```bash
# 方式一：软链/复制到扩展目录
# Windows: %USERPROFILE%\.vscode\extensions\bridge-lang-0.1.0
# 方式二：打包成 vsix（需要 npm i -g @vscode/vsce）
vsce package
code --install-extension bridge-lang-0.1.0.vsix
```

## 功能

| 命令 | 快捷键 | 作用 |
| --- | --- | --- |
| 桥语言：运行当前文件 | `F5` | 调 `桥.py 运行`，输出到「桥语言」输出面板 |
| 桥语言：调试当前文件 | — | 调 `桥.py 调试`（断点用命令行加 `--断点`） |
| 桥语言：打开自带编辑器 | `Ctrl+Alt+B` | 启动 `桥编辑器.pyw`（断点/调试/树搜索都在那儿） |
| 桥语言：查选中词的意思 | — | 调 `桥.py 查 词`，弹提示 |

## 设置

| 项 | 默认 | 说明 |
| --- | --- | --- |
| `bridge.python` | `python` | 跑 `桥.py` 的解释器 |
| `bridge.root` | 空 | 桥语言根目录；留空则从当前文件逐级往上找 `桥.py` |

## 语法文件怎么来的

`syntaxes/bridge.tmLanguage.json` 不是手写的，由：

```bash
python 工具/导出语法.py
```

从 `转译器/规则/` 现读关键字/内建/模块/方法生成——**规则一改，重跑一次就同步**。
