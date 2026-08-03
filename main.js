const { app, BrowserWindow } = require('electron');
const path = require('path');

// 确保中文正常显示
app.commandLine.appendSwitch('lang', 'zh-CN');

function createWindow() {
  // 创建窗口
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    title: "MC列车查询系统",
    webPreferences: {
      nodeIntegration: true,      // 允许HTML中使用Node.js API
      contextIsolation: false,    // 关闭上下文隔离
      enableRemoteModule: true    // 允许远程模块
    }
  });

  // 加载你的HTML文件（使用绝对路径）
  const htmlPath = path.join('C:', 'Users', 'Lenovo', 'Desktop', 'railmap', '用户端.html');
  mainWindow.loadFile(htmlPath);

  // 可选：打开开发者工具（调试用）
  // mainWindow.webContents.openDevTools();
}

// 应用启动后创建窗口
app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// 关闭所有窗口时退出应用
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});