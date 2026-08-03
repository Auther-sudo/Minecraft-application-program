# MC 铁路系统（Minecraft 铁路地图与查询系统）

一个面向 Minecraft 服务器的铁路系统工具集，包含**地图可视化工具**（基于 Python）与**用户端查询应用**（基于 Electron）两部分。

## 功能概览

| 模块 | 文件 | 说明 |
| --- | --- | --- |
| 地图可视化 | `pymap.py` | 基于 matplotlib + tkinter 的铁路线路地图，高德地图风格渲染，支持缩放/拖动、站名按连接度分级显示（LOD）、普通铁路枕木纹理随缩放自适应。 |
| 铁路系统核心 | `raillist.py` | `RailwaySystem` 类，负责加载数据、构建车站连接图与路径规划等逻辑。 |
| 车站名称生成器 | `车站名称.py` | 根据环境（生物群系）批量生成 MC 风格车站名称（调用 OpenAI API）。 |
| 用户端应用 | `用户端.html` / `main.js` / `package.json` | Electron 桌面端列车查询系统。 |
| 打包配置 | `pymap.spec` / `铁路系统地图.spec` | PyInstaller 打包脚本。 |
| 运维说明 | `运维更新.md` | 打包与更新操作记录。 |

## 目录结构

```
.
├── pymap.py                 # 地图可视化主程序
├── raillist.py              # 铁路系统核心类
├── 车站名称.py              # 车站名称生成器
├── 用户端.html              # Electron 用户端界面
├── main.js                  # Electron 主进程
├── package.json             # 用户端依赖与脚本
├── pymap.spec               # PyInstaller 打包配置
├── 铁路系统地图.spec        # PyInstaller 打包配置
├── 运维更新.md              # 运维/打包说明
├── 高铁.ico / 铁路查询.ico  # 程序图标
├── .gitignore
└── README.md
```

## ⚠️ 数据文件（本地私有，不纳入版本库）

以下两个文件包含实际的线路与列车数据，**已在 `.gitignore` 中忽略，不会上传到 GitHub**：

- `线路和车站数据.json`
- `列车数据.json`

> 程序运行需要这两个文件。请在本仓库根目录放置同名数据文件后，再运行 `pymap.py`（程序会优先读取同目录下的 `线路和车站数据.json`）。

## 环境依赖

- **地图工具**：Python 3 + `matplotlib`、`numpy`、`tkinter`
- **用户端**：Node.js + `electron`、`electron-packager`

## 运行方式

### 地图可视化工具

```bash
python pymap.py
```

### 用户端查询应用

```bash
npm install
npm start
```

## 打包

```bash
# 地图工具（生成 exe）
pyinstaller --onefile --windowed --icon=铁路查询.ico pymap.py

# 用户端（生成 Windows 安装包）
npm run package
```

## 许可

仅供学习与服务器自用，数据版权归原作者所有。
