# MC 铁路系统（Minecraft 铁路地图与查询系统）

一个面向 Minecraft 服务器的铁路系统工具集，包含**地图可视化工具**（基于 Python）与**用户端查询应用**（基于 Electron）两部分。

## 功能概览

| 模块 | 文件 | 说明 |
| --- | --- | --- |
| 地图可视化 | `src/pymap.py` | 基于 matplotlib + tkinter 的铁路线路地图，高德地图风格渲染，支持缩放/拖动、站名按连接度分级显示（LOD）、普通铁路枕木纹理随缩放自适应。 |
| 铁路系统核心 | `src/raillist.py` | `RailwaySystem` 类，负责加载数据、构建车站连接图与路径规划等逻辑。 |
| 车站名称生成器 | `src/车站名称.py` | 根据环境（生物群系）批量生成 MC 风格车站名称（调用 OpenAI API）。 |
| 用户端应用 | `electron/用户端.html` / `electron/main.js` / `electron/package.json` | Electron 桌面端列车查询系统。 |
| 打包配置 | `specs/pymap.spec` / `specs/铁路系统地图.spec` | PyInstaller 打包脚本。 |
| 运维说明 | `docs/运维更新.md` | 打包与更新操作记录。 |

## 目录结构

```
.
├── src/                     # Python 源码
│   ├── pymap.py             # 地图可视化主程序
│   ├── raillist.py          # 铁路系统核心类
│   └── 车站名称.py          # 车站名称生成器
├── electron/                # 用户端查询应用（Electron）
│   ├── main.js              # 主进程
│   ├── 用户端.html          # 界面
│   ├── package.json         # 依赖与脚本
│   └── package-lock.json
├── assets/                  # 图标等资源
│   ├── 高铁.ico
│   └── 铁路查询.ico
├── specs/                   # PyInstaller 打包配置
│   ├── pymap.spec
│   └── 铁路系统地图.spec
├── docs/                    # 文档
│   └── 运维更新.md
├── data/                    # 本地私有数据（git 忽略，见下）
│   ├── 线路和车站数据.json
│   └── 列车数据.json
├── .gitignore
├── LICENSE
└── README.md
```

## ⚠️ 数据文件（本地私有，不纳入版本库）

以下两个文件包含实际的线路与列车数据，**位于 `data/` 目录，已在 `.gitignore` 中忽略，不会上传到 GitHub**：

- `data/线路和车站数据.json`
- `data/列车数据.json`

> 程序运行需要这两个文件。`src/pymap.py` 会自动按以下顺序查找数据：`src/` 同目录 → 项目根 `data/` → 当前工作目录 → 当前工作目录 `data/` → 旧本地绝对路径兜底。请将同名数据文件放在仓库根目录的 `data/` 下即可。

## 环境依赖

- **地图工具**：Python 3 + `matplotlib`、`numpy`、`tkinter`
- **用户端**：Node.js + `electron`、`electron-packager`

## 运行方式

### 地图可视化工具

```bash
# 在仓库根目录执行
python src/pymap.py
```

### 用户端查询应用

```bash
cd electron
npm install
npm start
```

## 打包

```bash
# 地图工具（生成 exe）
pyinstaller specs/pymap.spec
# 或等价命令：
pyinstaller --onefile --windowed --icon=assets/铁路查询.ico src/pymap.py

# 用户端（生成 Windows 安装包，输出至 electron/app）
cd electron
npm run package
```

## 许可

本项目采用 [MIT License](./LICENSE)。数据版权归原作者所有，仅供学习与服务器自用。
