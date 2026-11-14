# 桥语言 VS Code 扩展

`.bridge` 文件的**语法高亮 + 代码片段 + 运行/调试**，轻量版（完整 IDE 还是自带的 `桥编辑器.pyw`）。

## 安装

### 方式一：直接装 vsix（推荐）

```bash
code --install-extension 桥语言-vscode-0.2.0.vsix
```

或者 VS Code 里 `Ctrl+Shift+P` → `Extensions: Install from VSIX…` 选文件。

### 方式二：复制目录

把 `vscode-桥语言/` 复制/软链到：

- Windows：`%USERPROFILE%\.vscode\extensions\bridge-lang-0.2.0`
- macOS / Linux：`~/.vscode/extensions/bridge-lang-0.2.0`

重启 VS Code，打开任意 `.bridge` 就能看到高亮。

## 功能

| 能力 | 说明 |
| --- | --- |
| 语法高亮 | 关键字 / 内建 / 异常 / 模块 / 方法 / 句式糖 / 定义名 / 字符串（含三引号）/ 注释 / 数字 / 全角标点 |
| 代码片段 | 输入 `如果`、`定义`、`类`、`尝试执行`、`对于`、`读取`… 按 Tab 展开 |
| 运行 | `F5`：调 `桥.py 运行`，输出到「桥语言」面板 |
| 调试 | 命令面板「桥语言：调试当前文件」，输出到面板 |
| 打开自带编辑器 | `Ctrl+Alt+B`：启动 `桥编辑器.pyw`（断点/一行一步/变量面板都在那儿） |
| 查词 | 选中中文词 → 命令面板「桥语言：查选中词的意思」 |

## 设置

| 项 | 默认 | 说明 |
| --- | --- | --- |
| `bridge.python` | `python` | 跑 `桥.py` 的解释器 |
| `bridge.root` | 空 | 桥语言根目录；留空则从当前文件逐级往上找 `桥.py` |

## 高亮/片段怎么来的

**不手写词表**。`syntaxes/bridge.tmLanguage.json` 和 `snippets/bridge.code-snippets` 由：

```bash
python 工具/导出VSCode高亮.py
```

从 `转译器/规则/` 现读关键字/内建/异常/模块成员/方法/句式糖生成——规则一改，重跑一次就同步，
高亮和转译器永远不会打架。

打安装包：

```bash
python 工具/打包VSCode插件.py     # 生成 发布/桥语言-vscode-<版本>.vsix
```
