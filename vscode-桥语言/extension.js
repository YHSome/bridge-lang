const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let 输出通道;

function 激活(context) {
    输出通道 = vscode.window.createOutputChannel('桥语言');
    context.subscriptions.push(输出通道);

    context.subscriptions.push(
        vscode.commands.registerCommand('bridge.运行', () => 跑文件(false)),
        vscode.commands.registerCommand('bridge.调试', () => 跑文件(true)),
        vscode.commands.registerCommand('bridge.打开编辑器', 打开编辑器),
        vscode.commands.registerCommand('bridge.查词', 查词),
        vscode.commands.registerCommand('bridge.设为桥语言', 设为桥语言),
    );
}

function 找根目录(文件) {
    const 配置 = vscode.workspace.getConfiguration('bridge').get('root');
    if (配置) return 配置;
    let 目录 = path.dirname(文件);
    for (let i = 0; i < 20; i += 1) {
        if (fs.existsSync(path.join(目录, '桥.py'))) return 目录;
        const 上级 = path.dirname(目录);
        if (上级 === 目录) break;
        目录 = 上级;
    }
    return '';
}

function 当前文件() {
    const 编辑器 = vscode.window.activeTextEditor;
    if (!编辑器) {
        vscode.window.showWarningMessage('先打开一个 .bridge 文件');
        return null;
    }
    if (编辑器.document.isDirty) 编辑器.document.save();
    return 编辑器.document.fileName;
}

function 跑文件(调试) {
    const 文件 = 当前文件();
    if (!文件) return;
    const 根 = 找根目录(文件);
    if (!根) {
        vscode.window.showErrorMessage('没找到 桥.py：请在设置 bridge.root 里填桥语言根目录');
        return;
    }
    const python = vscode.workspace.getConfiguration('bridge').get('python') || 'python';
    const 参数 = 调试 ? ['桥.py', '调试', 文件] : ['桥.py', '运行', 文件];
    输出通道.clear();
    输出通道.show(true);
    输出通道.appendLine(`$ ${python} ${参数.join(' ')}`);

    const 子 = spawn(python, 参数, {
        cwd: 根,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    });
    子.stdout.on('data', (块) => 输出通道.append(块.toString('utf-8')));
    子.stderr.on('data', (块) => 输出通道.append(块.toString('utf-8')));
    子.on('close', (码) => {
        输出通道.appendLine(`\n[退出码 ${码}]`);
        if (码 !== 0) 输出通道.show(true);
    });
}

function 打开编辑器() {
    const 文件 = 当前文件();
    const 根 = 文件 ? 找根目录(文件) : '';
    if (!根) {
        vscode.window.showErrorMessage('没找到 桥.py：请在设置 bridge.root 里填桥语言根目录');
        return;
    }
    const python = vscode.workspace.getConfiguration('bridge').get('python') || 'python';
    const 目标 = path.join(根, '桥编辑器.pyw');
    const 子 = spawn(python, [目标, ...(文件 ? [文件] : [])], { cwd: 根, detached: true });
    子.on('error', (错) => vscode.window.showErrorMessage(`启动编辑器失败：${错.message}`));
    子.unref();
}

function 查词() {
    const 编辑器 = vscode.window.activeTextEditor;
    if (!编辑器) return;
    const 词 = 编辑器.document.getText(编辑器.selection).trim();
    if (!词) {
        vscode.window.showInformationMessage('先选中一个中文词');
        return;
    }
    const 文件 = 编辑器.document.fileName;
    const 根 = 找根目录(文件);
    const python = vscode.workspace.getConfiguration('bridge').get('python') || 'python';
    const 子 = spawn(python, ['桥.py', '查', 词], {
        cwd: 根 || path.dirname(文件),
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
    let 文本 = '';
    子.stdout.on('data', (块) => { 文本 += 块.toString('utf-8'); });
    子.stderr.on('data', (块) => { 文本 += 块.toString('utf-8'); });
    子.on('close', () => vscode.window.showInformationMessage(文本.trim() || '没有结果'));
}

function 失活() {}

module.exports = { 激活, 失活 };

async function 设为桥语言() {
    const 编辑器 = vscode.window.activeTextEditor;
    if (!编辑器) {
        vscode.window.showWarningMessage('先打开一个文件');
        return;
    }
    await vscode.languages.setTextDocumentLanguage(编辑器.document, 'bridge');
    vscode.window.showInformationMessage('已切换为桥语言语法（bridge）');
}
