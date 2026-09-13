import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
import json
import os
import heapq
from tkinter import simpledialog, messagebox, filedialog, ttk, scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch

# 设置中文字体和负号显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

# 铁路速度设置 (单位: 米/秒)
SPEEDS = {
    'normal': 8,       # 普通铁路
    'high_speed': 12,  # 高速铁路
    'branch': 8        # 支线铁路，使用普通铁路速度
}

# 世界种子与版本号（用于程序化生成海陆底图）。
# 重要说明：Minecraft 基岩版的真实地形生成管线为专有实现，Python 端无法精确复现；
# 以下种子/版本仅用于驱动“确定性程序化近似地貌”，作为地图视觉参考，并非游戏内真实地形。
WORLD_SEED = 6769531640164931490
WORLD_VERSION = "基岩版 26.0-26.23"
SEA_LEVEL = 0.5          # 归一化高度 < SEA_LEVEL 视为海洋
TERRAIN_STEP = 120.0     # 底图采样步长（数据/方块单位），越小越精细、开销越大

class RailwayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("铁路系统地图")
        # 数据文件路径解析（兼容多种运行/部署方式）：
        # 1) 脚本同目录；2) 项目根的 data/；3) 当前工作目录；4) 当前工作目录的 data/；
        # 5) 本地绝对路径兜底。确保克隆/上传后或本地原有方式都能正常加载与保存。
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(_script_dir) if os.path.basename(_script_dir) == 'src' else _script_dir
        _candidates = [
            os.path.join(_script_dir, '线路和车站数据.json'),
            os.path.join(_project_root, 'data', '线路和车站数据.json'),
            os.path.join(os.getcwd(), '线路和车站数据.json'),
            os.path.join(os.getcwd(), 'data', '线路和车站数据.json'),
            r"E:\我的世界railmap\线路和车站数据.json",
        ]
        self.data_file = next((p for p in _candidates if os.path.exists(p)),
                              os.path.join(_project_root, 'data', '线路和车站数据.json'))
        
        # 拖动相关变量
        self.is_dragging = False
        self.start_x = 0
        self.start_y = 0
        
        # 初始化数据存储
        self.stations = {}
        self.connections = {}
        
        # 尝试自动加载数据
        load_success = self.auto_load_data()
        
        # 如果加载失败，显示空地图并提示
        if not load_success:
            messagebox.showwarning("数据加载提示", 
                                 f"未能加载数据文件：\n{self.data_file}\n\n将启动空地图，请添加车站和连接。")
        
        # 高德/地图风格：线路纤细，强调轨道感而非粗线条
        self.tie_spacing_data = 90       # 普通铁路枕木间隔（数据单位）
        self.tie_screen_px = 4           # 枕木半长在屏幕上的像素数
        self.high_speed_linewidth = 2.0  # 高速铁路线宽
        self.normal_linewidth = 1.4      # 普通铁路主线宽（放大显示枕木时）
        self.normal_linewidth_full = 2.0 # 普通铁路主线宽（全图/缩小、仅显示主线时，略加粗保证清晰）
        self.tie_linewidth = 2.2         # 枕木线宽（稍宽于主线以覆盖它）
        self.branch_linewidth = 1.5      # 支线铁路线宽
        # 枕木 LOD：当前视图跨度 / 全图跨度 >= 该阈值时隐藏枕木、只显示主线，
        # 避免缩到全图时密密麻麻白枕木糊成白带把主线淹没。放大到局部才显示枕木纹理。
        self.tie_show_frac = 0.35
        
        # 创建图形
        self.fig = Figure(figsize=(12, 10), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # 创建控制按钮框架
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(side=tk.BOTTOM, pady=5)
        
        # 主功能按钮
        self.station_btn = tk.Button(
            self.control_frame, 
            text="管理车站", 
            command=self.manage_stations,
            width=10
        )
        self.station_btn.pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = tk.Button(
            self.control_frame, 
            text="连接车站", 
            command=self.connect_stations,
            width=10
        )
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_conn_btn = tk.Button(
            self.control_frame, 
            text="删除连接", 
            command=self.delete_connection,
            width=10
        )
        self.delete_conn_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加查询时间按钮
        self.time_query_btn = tk.Button(
            self.control_frame, 
            text="查询时间", 
            command=self.query_travel_time,
            width=10
        )
        self.time_query_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加统计信息按钮
        self.stats_btn = tk.Button(
            self.control_frame, 
            text="统计信息", 
            command=self.show_statistics,
            width=10
        )
        self.stats_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = tk.Button(
            self.control_frame, 
            text="保存数据", 
            command=self.save_data,
            width=10
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.load_btn = tk.Button(
            self.control_frame, 
            text="加载数据", 
            command=self.load_data,
            width=10
        )
        self.load_btn.pack(side=tk.LEFT, padx=5)

        # 海陆轮廓开关（基于世界种子生成程序化近似底图，可显隐）
        self.show_terrain = True
        self.terrain_toggle_btn = tk.Button(
            self.control_frame,
            text="海陆轮廓:开",
            command=self.toggle_terrain,
            width=12
        )
        self.terrain_toggle_btn.pack(side=tk.LEFT, padx=5)

        # 创建画布并添加到Tkinter窗口
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        # 添加工具栏
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.root)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
              
        # 绑定鼠标事件
        self.canvas.mpl_connect('scroll_event', self.on_scroll)       # 滚轮缩放
        self.canvas.mpl_connect('button_press_event', self.on_press)  # 鼠标按下
        self.canvas.mpl_connect('button_release_event', self.on_release)  # 鼠标释放
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)    # 鼠标移动
        
        # 绘制铁路图
        self.draw_railway_map()
        
        # 添加说明文本
        self.info_label = tk.Label(root, text="操作说明：鼠标滚轮放大/缩小，按住左键拖动平移，点击工具栏'家'图标重置视图")
        self.info_label.pack(side=tk.BOTTOM)
        
        # 启动事件循环
        self.canvas.draw()

    def auto_load_data(self):
        """程序启动时自动加载指定路径的数据文件"""
        if not os.path.exists(self.data_file):
            messagebox.showerror("文件不存在", f"数据文件不存在：\n{self.data_file}")
            return False
            
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # 验证数据格式
            if 'stations' in loaded_data and 'connections' in loaded_data:
                # 加载车站数据
                self.stations = loaded_data['stations']
                for key in self.stations:
                    self.stations[key] = tuple(self.stations[key])
                
                # 加载连接数据
                self.connections = {}
                for conn_data in loaded_data['connections']:
                    stations, conn_type = conn_data
                    key = tuple(sorted(stations))
                    self.connections[key] = conn_type
                return True
        except Exception as e:
            messagebox.showerror("加载错误", f"加载数据失败: {str(e)}")
        
        return False

    # 管理车站相关方法
    def manage_stations(self):
        """管理车站：搜索、添加、编辑、删除。

        操作拆成「编辑」「删除」两列，单元格内显示图标 + 文字（✏ 编辑 / ✖ 删除），
        点击对应列即触发对应操作；不再依赖 tree.bbox()+place 嵌按钮（旧实现在滚动/
        首帧 bbox 为空时会崩，导致车站/按钮显示不全）。所有车站与操作均稳定可见。
        """
        manage_window = tk.Toplevel(self.root)
        manage_window.title("车站管理")
        manage_window.geometry("660x520")
        manage_window.transient(self.root)
        manage_window.grab_set()

        # 顶部：搜索框 + 添加按钮
        top_frame = ttk.Frame(manage_window)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text="搜索车站:").pack(side=tk.LEFT, padx=(5, 2))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(top_frame, textvariable=search_var, width=26)
        search_entry.pack(side=tk.LEFT, padx=2)
        search_entry.focus_set()

        ttk.Label(top_frame, text="提示：点击图标列进行编辑 / 删除",
                  foreground="#666666").pack(side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="添加新车站",
                   command=lambda: self.add_station(manage_window)).pack(side=tk.RIGHT, padx=5)

        # 车站列表：操作拆成「编辑」「删除」两列，单元格显示图标
        columns = ("name", "x_coord", "z_coord", "edit", "delete")
        tree = ttk.Treeview(manage_window, columns=columns, show="headings", height=20)

        tree.heading("name", text="车站名称")
        tree.heading("x_coord", text="X坐标")
        tree.heading("z_coord", text="Z坐标")
        tree.heading("edit", text="编辑")
        tree.heading("delete", text="删除")

        tree.column("name", width=200)
        tree.column("x_coord", width=85)
        tree.column("z_coord", width=85)
        tree.column("edit", width=80, anchor=tk.CENTER)
        tree.column("delete", width=80, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(manage_window, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # 刷新列表（仅填充数据；操作通过点击图标列触发，绝不依赖 bbox/place）
        def refresh_list():
            for item in tree.get_children():
                tree.delete(item)
            search_text = search_var.get().strip().lower()
            for name, (x, z) in self.stations.items():
                if search_text in name.lower():
                    tree.insert("", tk.END,
                                values=(name, f"{x:.1f}", f"{z:.1f}", "✏ 编辑", "✖ 删除"))

        # 点击「编辑」「删除」列：直接触发对应操作
        def on_tree_click(event):
            region = tree.identify_region(event.x, event.y)
            if region not in ("cell", "tree", "text"):
                return
            row = tree.identify_row(event.y)
            col = tree.identify_column(event.x)
            if not row:
                return
            values = tree.item(row, "values")
            if not values:
                return
            name = values[0]
            if col == "#4":        # 编辑列
                self.edit_station(name)
            elif col == "#5":      # 删除列
                self.delete_station(name)
            else:
                return
            refresh_list()

        tree.bind("<Button-1>", on_tree_click)

        # 搜索框事件绑定
        search_var.trace_add("write", lambda *args: refresh_list())

        # 初始刷新
        refresh_list()

        # 窗口关闭时刷新地图
        def on_close():
            self.ax.clear()
            self.draw_railway_map()
            self.canvas.draw()
            manage_window.destroy()

        manage_window.protocol("WM_DELETE_WINDOW", on_close)

    def add_station(self, parent_window):
        """添加新车站"""
        # 获取新车站名称
        station_name = simpledialog.askstring("输入", "请输入新车站名称:", parent=parent_window)
        if not station_name or station_name in self.stations:
            messagebox.showerror("错误", "车站名称不能为空或已存在!", parent=parent_window)
            return
        
        # 获取新车站坐标
        try:
            x_coord = simpledialog.askfloat("输入", "请输入X坐标:", parent=parent_window)
            z_coord = simpledialog.askfloat("输入", "请输入Z坐标:", parent=parent_window)
            if x_coord is None or z_coord is None:
                return  # 用户取消输入
        except ValueError:
            messagebox.showerror("错误", "坐标必须是数字!", parent=parent_window)
            return
        
        # 添加新车站
        self.stations[station_name] = (x_coord, z_coord)
        messagebox.showinfo("成功", f"已添加新车站: {station_name}", parent=parent_window)
        
        # 刷新地图
        self.ax.clear()
        self.draw_railway_map()
        self.canvas.draw()

    def edit_station(self, station_name):
        """编辑车站信息"""
        if station_name not in self.stations:
            messagebox.showerror("错误", f"车站 {station_name} 不存在!")
            return
        
        # 获取当前坐标
        current_x, current_z = self.stations[station_name]
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"编辑车站: {station_name}")
        edit_window.geometry("300x200")
        edit_window.transient(self.root)
        
        # 输入框
        ttk.Label(edit_window, text="车站名称:").pack(anchor=tk.W, padx=10, pady=5)
        name_entry = ttk.Entry(edit_window)
        name_entry.insert(0, station_name)
        name_entry.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(edit_window, text="X坐标:").pack(anchor=tk.W, padx=10, pady=5)
        x_entry = ttk.Entry(edit_window)
        x_entry.insert(0, str(current_x))
        x_entry.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(edit_window, text="Z坐标:").pack(anchor=tk.W, padx=10, pady=5)
        z_entry = ttk.Entry(edit_window)
        z_entry.insert(0, str(current_z))
        z_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # 保存按钮
        def save_changes():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showerror("错误", "车站名称不能为空!")
                return
            
            try:
                new_x = float(x_entry.get())
                new_z = float(z_entry.get())
            except ValueError:
                messagebox.showerror("错误", "坐标必须是数字!")
                return
            
            # 如果名称改变，更新连接中的名称
            if new_name != station_name:
                if new_name in self.stations:
                    messagebox.showerror("错误", f"车站 {new_name} 已存在!")
                    return
                
                # 更新连接中的车站名称
                new_connections = {}
                for (s1, s2), conn_type in self.connections.items():
                    new_s1 = new_name if s1 == station_name else s1
                    new_s2 = new_name if s2 == station_name else s2
                    # 保持顺序一致，避免重复
                    key = tuple(sorted([new_s1, new_s2]))
                    new_connections[key] = conn_type
                
                self.connections = new_connections
                # 删除旧名称，添加新名称
                del self.stations[station_name]
            
            # 更新坐标
            self.stations[new_name] = (new_x, new_z)
            
            # 重新绘制地图
            self.ax.clear()
            self.draw_railway_map()
            self.canvas.draw()
            
            edit_window.destroy()
            messagebox.showinfo("成功", f"车站 {new_name} 已更新")
        
        btn_frame = ttk.Frame(edit_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT, padx=5)

    def delete_station(self, station_name):
        """删除车站"""
        # 确认删除
        if not messagebox.askyesno("确认", f"确定要删除车站 {station_name} 吗?\n这将同时删除所有与该车站相关的连接!"):
            return
        
        if station_name not in self.stations:
            messagebox.showerror("错误", f"车站 {station_name} 不存在!")
            return
        
        # 删除与该车站相关的所有连接
        connections_to_remove = []
        for (s1, s2) in self.connections:
            if s1 == station_name or s2 == station_name:
                connections_to_remove.append((s1, s2))
        
        for conn in connections_to_remove:
            del self.connections[conn]
        
        # 删除车站
        del self.stations[station_name]
        
        # 重新绘制地图
        self.ax.clear()
        self.draw_railway_map()
        self.canvas.draw()
        
        messagebox.showinfo("成功", f"车站 {station_name} 已删除")

    def connect_stations(self):
        """连接两个车站，选择铁路类型"""
        if len(self.stations) < 2:
            messagebox.showerror("错误", "至少需要两个车站才能创建连接!")
            return
        
        # 创建连接窗口
        connect_window = tk.Toplevel(self.root)
        connect_window.title("连接车站")
        connect_window.geometry("400x300")
        connect_window.transient(self.root)
        
        # 选择第一个车站
        ttk.Label(connect_window, text="选择第一个车站:").pack(anchor=tk.W, padx=10, pady=5)
        station1_var = tk.StringVar()
        station1_combo = ttk.Combobox(connect_window, textvariable=station1_var, values=sorted(self.stations.keys()), width=30)
        station1_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # 选择第二个车站
        ttk.Label(connect_window, text="选择第二个车站:").pack(anchor=tk.W, padx=10, pady=5)
        station2_var = tk.StringVar()
        station2_combo = ttk.Combobox(connect_window, textvariable=station2_var, values=sorted(self.stations.keys()), width=30)
        station2_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # 选择铁路类型
        ttk.Label(connect_window, text="选择铁路类型:").pack(anchor=tk.W, padx=10, pady=5)
        rail_type_var = tk.StringVar(value="normal")
        
        type_frame = ttk.Frame(connect_window)
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Radiobutton(type_frame, text="普通铁路", variable=rail_type_var, value="normal").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="支线铁路", variable=rail_type_var, value="branch").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="高速铁路（含地铁线路）", variable=rail_type_var, value="high_speed").pack(side=tk.LEFT, padx=10)
        
        # 连接按钮
        def create_connection():
            station1 = station1_var.get().strip()
            station2 = station2_var.get().strip()
            
            if not station1 or not station2:
                messagebox.showerror("错误", "请选择两个车站!", parent=connect_window)
                return
            
            if station1 == station2:
                messagebox.showerror("错误", "不能连接同一个车站!", parent=connect_window)
                return
            
            if station1 not in self.stations or station2 not in self.stations:
                messagebox.showerror("错误", "所选车站不存在!", parent=connect_window)
                return
            
            # 使用排序后的元组作为键，避免重复连接
            key = tuple(sorted([station1, station2]))
            if key in self.connections:
                messagebox.showwarning("提示", "这两个车站已经存在连接!", parent=connect_window)
                return
            
            # 创建连接
            rail_type = rail_type_var.get()
            self.connections[key] = rail_type
            
            # 重新绘制地图
            self.ax.clear()
            self.draw_railway_map()
            self.canvas.draw()
            
            connect_window.destroy()
            messagebox.showinfo("成功", f"已用{['普通', '支线', '高速'][['normal', 'branch', 'high_speed'].index(rail_type)]}铁路连接 {station1} 和 {station2}")
        
        btn_frame = ttk.Frame(connect_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=15)
        
        ttk.Button(btn_frame, text="创建连接", command=create_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=connect_window.destroy).pack(side=tk.RIGHT, padx=5)

    def delete_connection(self):
        """删除两个车站之间的连接"""
        if not self.connections:
            messagebox.showinfo("提示", "当前没有任何连接!")
            return
        
        # 创建删除连接窗口
        delete_window = tk.Toplevel(self.root)
        delete_window.title("删除连接")
        delete_window.geometry("400x300")
        delete_window.transient(self.root)
        
        # 显示所有连接
        ttk.Label(delete_window, text="选择要删除的连接:").pack(anchor=tk.W, padx=10, pady=5)
        
        # 创建连接列表
        conn_listbox = tk.Listbox(delete_window, selectmode=tk.SINGLE, height=10)
        conn_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(delete_window, orient="vertical", command=conn_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        conn_listbox.config(yscrollcommand=scrollbar.set)
        
        # 填充连接列表
        self.connection_items = []  # 存储列表项与连接的映射关系
        for i, ((s1, s2), conn_type) in enumerate(self.connections.items()):
            type_text = {
                'normal': '普通铁路',
                'branch': '支线铁路',
                'high_speed': '高速铁路'
            }[conn_type]
            item_text = f"{s1} - {s2} ({type_text})"
            conn_listbox.insert(tk.END, item_text)
            self.connection_items.append(((s1, s2), conn_type))
        
        # 删除按钮
        def remove_connection():
            selection = conn_listbox.curselection()
            if not selection:
                messagebox.showwarning("提示", "请选择要删除的连接!", parent=delete_window)
                return
            
            index = selection[0]
            (s1, s2), conn_type = self.connection_items[index]
            key = tuple(sorted([s1, s2]))
            
            # 删除连接
            if key in self.connections:
                del self.connections[key]
                
                # 重新绘制地图
                self.ax.clear()
                self.draw_railway_map()
                self.canvas.draw()
                
                delete_window.destroy()
                messagebox.showinfo("成功", f"已删除 {s1} 和 {s2} 之间的连接")
        
        btn_frame = ttk.Frame(delete_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=15)
        
        ttk.Button(btn_frame, text="删除选中连接", command=remove_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=delete_window.destroy).pack(side=tk.RIGHT, padx=5)

    def save_data(self):
        """保存当前的车站和连接数据到文件"""
        # 准备要保存的数据
        data_to_save = {
            'stations': self.stations,  # 所有车站坐标
            'connections': [(list(k), v) for k, v in self.connections.items()]  # 连接关系
        }
        
        # 确保目录存在
        dir_path = os.path.dirname(self.data_file)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建目录: {str(e)}")
                return
        
        try:
            # 写入JSON文件
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("成功", f"数据已成功保存到:\n{self.data_file}")
        except Exception as e:
            messagebox.showerror("错误", f"保存数据失败:\n{str(e)}")

    def load_data(self):
        """从文件加载车站和连接数据"""
        # 让用户选择要加载的文件
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="加载铁路数据",
            initialfile=self.data_file
        )
        
        if not file_path or not os.path.exists(file_path):
            return  # 用户取消或文件不存在
        
        try:
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # 验证数据格式
            required_keys = ['stations', 'connections']
            if not all(key in loaded_data for key in required_keys):
                messagebox.showerror("错误", "数据格式不正确，无法加载")
                return
            
            # 更新数据
            self.stations = loaded_data['stations']
            # 将坐标从列表转换回元组
            for key in self.stations:
                self.stations[key] = tuple(self.stations[key])
                
            # 恢复连接
            self.connections = {}
            for conn_data in loaded_data['connections']:
                stations, conn_type = conn_data
                key = tuple(sorted(stations))  # 保持键的一致性
                self.connections[key] = conn_type
            
            # 更新数据文件路径
            self.data_file = file_path
            
            # 重新绘制地图
            self.ax.clear()
            self.draw_railway_map()
            self.canvas.draw()
            
            messagebox.showinfo("成功", f"已从以下文件加载数据:\n{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"加载数据失败:\n{str(e)}")

    # 查询运行时间功能
    def query_travel_time(self):
        """查询两个车站之间的运行时间"""
        if len(self.stations) < 2:
            messagebox.showerror("错误", "至少需要两个车站才能查询运行时间!")
            return
        
        # 创建查询窗口
        query_window = tk.Toplevel(self.root)
        query_window.title("查询运行时间")
        query_window.geometry("400x300")
        query_window.transient(self.root)
        
        # 选择起点车站
        ttk.Label(query_window, text="选择起点车站:").pack(anchor=tk.W, padx=10, pady=5)
        start_var = tk.StringVar()
        start_combo = ttk.Combobox(query_window, textvariable=start_var, values=sorted(self.stations.keys()), width=30)
        start_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # 选择终点车站
        ttk.Label(query_window, text="选择终点车站:").pack(anchor=tk.W, padx=10, pady=5)
        end_var = tk.StringVar()
        end_combo = ttk.Combobox(query_window, textvariable=end_var, values=sorted(self.stations.keys()), width=30)
        end_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # 查询按钮
        def calculate_time():
            start_station = start_var.get().strip()
            end_station = end_var.get().strip()
            
            if not start_station or not end_station:
                messagebox.showerror("错误", "请选择起点和终点车站!", parent=query_window)
                return
            
            if start_station == end_station:
                messagebox.showinfo("结果", "起点和终点为同一车站，运行时间为0秒", parent=query_window)
                return
            
            if start_station not in self.stations or end_station not in self.stations:
                messagebox.showerror("错误", "所选车站不存在!", parent=query_window)
                return
            
            # 构建铁路网络图形表示
            graph = self._build_railway_graph()
            
            # 使用Dijkstra算法查找最短时间路径
            time, path = self._dijkstra_shortest_path(graph, start_station, end_station)
            
            if time is None:
                messagebox.showinfo("结果", f"{start_station} 和 {end_station} 之间没有可达路径", parent=query_window)
                return
            
            # 格式化时间显示
            hours = int(time // 3600)
            minutes = int((time % 3600) // 60)
            seconds = int(time % 60)
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours}小时"
            if minutes > 0:
                time_str += f"{minutes}分钟"
            time_str += f"{seconds}秒"
            
            # 显示结果
            result_window = tk.Toplevel(query_window)
            result_window.title("查询结果")
            result_window.geometry("400x300")
            result_window.transient(query_window)
            
            ttk.Label(result_window, text=f"{start_station} 到 {end_station} 的运行信息", 
                     font=("SimHei", 12, "bold")).pack(pady=10)
            
            ttk.Label(result_window, text=f"最短运行时间: {time_str}", 
                     font=("SimHei", 10)).pack(anchor=tk.W, padx=20, pady=5)
            
            ttk.Label(result_window, text="路线:", 
                     font=("SimHei", 10, "bold")).pack(anchor=tk.W, padx=20, pady=5)
            
            path_text = " → ".join(path)
            path_label = ttk.Label(result_window, text=path_text, wraplength=350, 
                                 font=("SimHei", 10))
            path_label.pack(anchor=tk.W, padx=20, pady=5)
            
            ttk.Button(result_window, text="关闭", command=result_window.destroy).pack(pady=20)
        
        btn_frame = ttk.Frame(query_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=30)
        
        ttk.Button(btn_frame, text="查询", command=calculate_time).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=query_window.destroy).pack(side=tk.RIGHT, padx=5)

    # 显示统计信息
    def show_statistics(self):
        """显示铁路系统的统计信息，包括各类铁路里程和最长运行时间"""
        if not self.stations:
            messagebox.showinfo("提示", "当前没有车站数据可统计!")
            return
        
        if not self.connections:
            messagebox.showinfo("提示", "当前没有铁路连接数据可统计!")
            return
        
        # 计算各类铁路里程（使用曼哈顿距离）
        total_distance = 0.0
        high_speed_distance = 0.0
        normal_distance = 0.0
        branch_distance = 0.0
        
        for (s1, s2), conn_type in self.connections.items():
            x1, z1 = self.stations[s1]
            x2, z2 = self.stations[s2]
            
            # 计算曼哈顿距离：|x1-x2| + |z1-z2|（只能正向走，不能斜向）
            distance = abs(x2 - x1) + abs(z2 - z1)
            total_distance += distance
            
            if conn_type == 'high_speed':
                high_speed_distance += distance
            elif conn_type == 'branch':
                branch_distance += distance
            else:
                normal_distance += distance
        
        # 查找最长运行时间（单源 Dijkstra：每个起点只跑一次，替代 O(n^2) 全配对，
        # 222 个车站也不会卡死界面；点击“统计信息”时也能很快出结果）
        graph = self._build_railway_graph()
        stations_list = list(self.stations.keys())

        max_time = 0.0
        max_path = []
        max_start = ""
        max_end = ""

        for s in stations_list:
            distances, previous = self._dijkstra_all_from(graph, s)
            for t_node, t in distances.items():
                if t != float('inf') and t > max_time:
                    # 回溯路径 s -> t_node
                    path = []
                    cur = t_node
                    while cur is not None:
                        path.append(cur)
                        cur = previous[cur]
                    path.reverse()
                    max_time = t
                    max_path = path
                    max_start = s
                    max_end = t_node

        # 创建统计信息窗口（可缩放 + 路线滚动，避免超长路线被截断“显示不全”）
        stats_window = tk.Toplevel(self.root)
        stats_window.title("铁路系统统计信息")
        stats_window.geometry("560x480")
        stats_window.resizable(True, True)
        stats_window.transient(self.root)

        content = ttk.Frame(stats_window)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        ttk.Label(content, text="铁路里程统计", font=("SimHei", 12, "bold")).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(content, text=f"总里程: {total_distance:.2f} 米", font=("SimHei", 10)).pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(content, text=f"高速铁路里程: {high_speed_distance:.2f} 米", font=("SimHei", 10)).pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(content, text=f"普通铁路里程: {normal_distance:.2f} 米", font=("SimHei", 10)).pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(content, text=f"支线铁路里程: {branch_distance:.2f} 米", font=("SimHei", 10)).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Label(content, text="最长运行时间", font=("SimHei", 12, "bold")).pack(anchor=tk.W, pady=(10, 6))

        if max_time > 0:
            # 格式化最长时间
            hours = int(max_time // 3600)
            minutes = int((max_time % 3600) // 60)
            seconds = int(max_time % 60)

            time_str = ""
            if hours > 0:
                time_str += f"{hours}小时"
            if minutes > 0:
                time_str += f"{minutes}分钟"
            time_str += f"{seconds}秒"

            ttk.Label(content, text=f"最长时间: {time_str}", font=("SimHei", 10)).pack(anchor=tk.W, padx=10, pady=2)
            ttk.Label(content, text=f"站点: {max_start} 到 {max_end}（共 {len(max_path)} 站）", font=("SimHei", 10)).pack(anchor=tk.W, padx=10, pady=2)
            ttk.Label(content, text="路线:", font=("SimHei", 10, "bold")).pack(anchor=tk.W, padx=10, pady=(6, 2))

            route_text = " → ".join(max_path)
            route_box = scrolledtext.ScrolledText(content, wrap=tk.WORD, height=8, font=("SimHei", 10))
            route_box.insert(tk.END, route_text)
            route_box.configure(state=tk.DISABLED)
            route_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)
        else:
            ttk.Label(content, text="没有可用的运行时间数据", font=("SimHei", 10)).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Button(stats_window, text="关闭", command=stats_window.destroy).pack(pady=10)

    def _build_railway_graph(self):
        """构建铁路网络的图形表示，用于路径查找"""
        graph = {station: [] for station in self.stations}
        
        for (s1, s2), conn_type in self.connections.items():
            # 计算两站之间的曼哈顿距离（只能正向走，不能斜向）
            x1, z1 = self.stations[s1]
            x2, z2 = self.stations[s2]
            distance = abs(x2 - x1) + abs(z2 - z1)
            
            # 根据铁路类型获取速度
            speed = SPEEDS[conn_type]
            
            # 计算时间（秒）
            time = distance / speed if speed > 0 else float('inf')
            
            # 添加到图中（双向连接）
            graph[s1].append((s2, time, distance, conn_type))
            graph[s2].append((s1, time, distance, conn_type))
            
        return graph

    def _dijkstra_shortest_path(self, graph, start, end):
        """使用Dijkstra算法查找最短时间路径"""
        # 初始化距离字典，存储从起点到每个节点的最短时间
        distances = {node: float('inf') for node in graph}
        distances[start] = 0
        
        # 存储路径
        previous_nodes = {node: None for node in graph}
        
        # 使用优先队列（堆）来存储需要处理的节点
        priority_queue = [(0, start)]
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            # 如果到达终点，提前退出
            if current_node == end:
                break
                
            # 如果当前距离大于已知最短距离，跳过
            if current_distance > distances[current_node]:
                continue
                
            # 遍历邻居节点
            for neighbor, time, distance, conn_type in graph[current_node]:
                new_distance = current_distance + time
                
                # 如果找到更短的路径
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous_nodes[neighbor] = current_node
                    heapq.heappush(priority_queue, (new_distance, neighbor))
        
        # 如果终点不可达
        if distances[end] == float('inf'):
            return None, None
            
        # 重建路径
        path = []
        current = end
        while current is not None:
            path.append(current)
            current = previous_nodes[current]
        path.reverse()
        
        return distances[end], path

    def _dijkstra_all_from(self, graph, start):
        """单源 Dijkstra：返回 (distances, previous_nodes)。

        distances 为 start 到各节点的最短时间；previous_nodes 用于回溯路径。
        相比“统计信息”里对每对车站都跑一次 Dijkstra（O(n^2)），单源只需
        对每个起点跑一次（O(n)），222 个车站也能瞬间完成。
        """
        distances = {node: float('inf') for node in graph}
        distances[start] = 0
        previous = {node: None for node in graph}

        priority_queue = [(0, start)]
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            if current_distance > distances[current_node]:
                continue
            for neighbor, time, _distance, _conn_type in graph[current_node]:
                new_distance = current_distance + time
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous[neighbor] = current_node
                    heapq.heappush(priority_queue, (new_distance, neighbor))

        return distances, previous

    # 鼠标事件处理
    def on_press(self, event):
        """鼠标按下事件：开始拖动"""
        if event.button == 1:  # 左键
            self.is_dragging = True
            self.start_x = event.xdata
            self.start_y = event.ydata

    def on_release(self, event):
        """鼠标释放事件：结束拖动"""
        if event.button == 1:  # 左键
            self.is_dragging = False

    def on_motion(self, event):
        """鼠标移动事件：处理拖动"""
        if self.is_dragging and event.xdata is not None and event.ydata is not None:
            # 计算位移
            dx = event.xdata - self.start_x
            dy = event.ydata - self.start_y
            
            # 获取当前视图范围
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            
            # 调整视图范围（平移）
            self.ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
            self.ax.set_ylim(ylim[0] - dy, ylim[1] - dy)
            
            # 更新起始位置
            self.start_x = event.xdata
            self.start_y = event.ydata
            
            # 重绘
            self.canvas.draw()

    def on_scroll(self, event):
        """处理鼠标滚轮事件实现缩放"""
        # 获取当前视图范围
        xlim = self.ax.get_xlim()
        zlim = self.ax.get_ylim()
        
        # 计算缩放因子
        scale_factor = 1.1 if event.button == 'up' else 0.9
        
        # 计算鼠标在数据坐标中的位置
        xdata, zdata = event.xdata, event.ydata
        
        if xdata is None or zdata is None:
            return  # 鼠标在图形外时不处理
        
        # 计算新的视图范围（围绕鼠标位置缩放）
        new_xlim = [
            xdata - (xdata - xlim[0]) * scale_factor,
            xdata + (xlim[1] - xdata) * scale_factor
        ]
        new_zlim = [
            zdata - (zdata - zlim[0]) * scale_factor,
            zdata + (zlim[1] - zdata) * scale_factor
        ]
        
        # 设置新的视图范围
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_zlim)
        
        # 重绘
        self.canvas.draw()

    def _on_view_change(self, *args):
        # 视图（缩放/平移）变化时，刷新枕木长度（保持屏幕像素恒定）与站名 LOD
        self._update_ties()
        self._update_label_visibility()

    def _update_label_visibility(self):
        # 按当前缩放级别决定显示哪些站名与圆点：
        # - 端点站（度=1）无论缩放大小，名称与圆点始终显示；
        # - 缩放越小（frac→1）只显示高连接度枢纽，放大（frac→0）显示越全；
        # - 缩到足够小会省略“途经站(度=2)”的圆点与名称，画面更整洁。
        if not hasattr(self, 'station_labels') or not hasattr(self, '_degree'):
            return
        if not hasattr(self, 'station_scatter'):
            return

        xr = self.ax.get_xlim(); zr = self.ax.get_ylim()
        cur = max(xr[1] - xr[0], abs(zr[1] - zr[0]))
        frac = cur / self._full_span if self._full_span else 1.0

        # 缩放越小越严格：全图只看枢纽，放大后逐步显示更多
        if frac >= 0.6:
            thr = 3
        elif frac >= 0.3:
            thr = 2
        else:
            thr = 1

        xlo, xhi = xr[0], xr[1]
        zlo, zhi = min(zr), max(zr)
        in_view = [n for n, (xi, zi) in self.stations.items()
                   if xlo <= xi <= xhi and zlo <= zi <= zhi]

        endpoints = getattr(self, '_endpoints', set())
        endpoints_in = [n for n in in_view if n in endpoints]

        # 站名：端点名称始终显示；其余按阈值，视口内太少则逐步放宽
        meeting = [n for n in in_view if self._degree.get(n, 0) >= thr]
        while len(meeting) < 3 and thr > 1:
            thr -= 1
            meeting = [n for n in in_view if self._degree.get(n, 0) >= thr]
        show = set(endpoints_in) | set(meeting)

        # 站名可见性
        for name, txt in self.station_labels:
            txt.set_visible(name in show)
        # 圆点可见性：通过 alpha 数组一次性设置（性能更好）
        for i, name in enumerate(self.station_order):
            self._station_alphas[i] = 1.0 if name in show else 0.0
        self.station_scatter.set_alpha(self._station_alphas)

    def _tie_half_length(self):
        """根据当前坐标变换，计算枕木半长在数据坐标中的值，使其在屏幕上保持固定像素数。"""
        xlim = self.ax.get_xlim(); ylim = self.ax.get_ylim()
        cx = (xlim[0] + xlim[1]) / 2.0
        cy = (ylim[0] + ylim[1]) / 2.0
        px, py = self.ax.transData.transform((cx, cy))
        x_left, _ = self.ax.transData.inverted().transform((px - self.tie_screen_px, py))
        _, y_top = self.ax.transData.inverted().transform((px, py - self.tie_screen_px))
        # aspect='equal' 下 x/z 比例相同，取平均更稳健
        data_per_px = (abs(cx - x_left) + abs(cy - y_top)) / (2.0 * self.tie_screen_px)
        return data_per_px * self.tie_screen_px

    def _build_tie_segments(self, tie_half):
        """为所有普通铁路连接生成枕木线段（数据坐标）。"""
        segments = []
        for (s1, s2), conn_type in self.connections.items():
            if conn_type != 'normal':
                continue
            if s1 not in self.stations or s2 not in self.stations:
                continue
            x1, z1 = self.stations[s1]
            x2, z2 = self.stations[s2]
            dx = x2 - x1; dz = z2 - z1
            seg_len = np.hypot(dx, dz)
            if seg_len <= 0:
                continue
            ux, uz = dx / seg_len, dz / seg_len
            nx, nz = -uz, ux  # 垂直于轨道的单位向量
            # 按数据单位间距放置枕木；短线段至少在中点放一根
            steps = np.arange(0, seg_len, self.tie_spacing_data)
            if len(steps) == 0:
                steps = np.array([seg_len / 2.0])
            for d in steps:
                qx = x1 + ux * d
                qz = z1 + uz * d
                segments.append([
                    (qx + nx * tie_half, qz + nz * tie_half),
                    (qx - nx * tie_half, qz - nz * tie_half)
                ])
        return segments

    def _update_ties(self):
        """缩放/平移时刷新枕木与主线：
        - 计算当前视图跨度占全图的比例 frac；
        - frac 较大（全图/缩小）时隐藏枕木、只显主线并略加粗，避免白枕木糊成白带；
        - frac 较小（放大到局部）时显示枕木纹理，且枕木在屏幕上保持恒定像素大小。
        """
        if not hasattr(self, 'tie_collection') or not hasattr(self, 'normal_collection'):
            return
        xr = self.ax.get_xlim(); zr = self.ax.get_ylim()
        span = max(xr[1] - xr[0], abs(zr[1] - zr[0]))
        frac = span / self._full_span if self._full_span else 1.0

        if frac >= self.tie_show_frac:
            # 缩小/全图：只显示主线，隐藏枕木，主线略加粗保证清晰可见
            self.tie_collection.set_visible(False)
            self.normal_collection.set_linewidths(self.normal_linewidth_full)
        else:
            # 放大到局部：显示枕木细节，主线恢复纤细
            self.tie_collection.set_visible(True)
            tie_half = self._tie_half_length()
            self.tie_collection.set_segments(self._build_tie_segments(tie_half))
            self.normal_collection.set_linewidths(self.normal_linewidth)

    def draw_railway_map(self):
        """绘制铁路系统地图（高德/地图风格：纤细线路、轨道感、干净背景）。"""
        # 用于控制图例只显示一次
        normal_legend_added = False
        high_speed_legend_added = False
        branch_legend_added = False

        # 计算地图范围（与末尾 xlim/ylim 保持一致），供海陆底图使用
        if self.stations:
            _ax = [p[0] for p in self.stations.values()]
            _az = [p[1] for p in self.stations.values()]
            _pad = 50
            _xmin, _xmax = min(_ax) - _pad, max(_ax) + _pad
            _zmin, _zmax = min(_az) - _pad, max(_az) + _pad
            _span = max(_xmax - _xmin, _zmax - _zmin)
            _xc = (_xmin + _xmax) / 2
            _zc = (_zmin + _zmax) / 2
            _xmin, _xmax = _xc - _span / 2, _xc + _span / 2
            _zmin, _zmax = _zc - _span / 2, _zc + _span / 2
            self._map_bounds = (_xmin, _xmax, _zmin, _zmax)
        else:
            self._map_bounds = (-1000.0, 1000.0, -1000.0, 1000.0)

        # 分别收集三类铁路的线段，用于 LineCollection（比 ax.plot 更统一、更清爽）
        normal_segments = []
        high_speed_segments = []
        branch_segments = []
        for (s1, s2), conn_type in self.connections.items():
            if s1 not in self.stations or s2 not in self.stations:
                continue
            p1, p2 = self.stations[s1], self.stations[s2]
            seg = [p1, p2]
            if conn_type == 'high_speed':
                high_speed_segments.append(seg)
            elif conn_type == 'branch':
                branch_segments.append(seg)
            else:
                normal_segments.append(seg)

        # 海陆底图（程序化近似，zorder=0，置于所有线路之下）
        self._draw_terrain(self._map_bounds)

        # 普通铁路：深灰主线 + 白色枕木，形成经典轨道效果
        if normal_segments:
            self.normal_collection = LineCollection(
                normal_segments, colors='#222222',
                linewidths=self.normal_linewidth,
                zorder=1, label='普通铁路'
            )
            self.ax.add_collection(self.normal_collection)
            normal_legend_added = True
            # 枕木：初始长度按全图跨度估算，_update_ties 会立即按当前视图修正
            tie_half = self._tie_half_length() if self.ax.has_data() else 50
            self.tie_collection = LineCollection(
                self._build_tie_segments(tie_half),
                colors='#FFFFFF', linewidths=self.tie_linewidth,
                zorder=2
            )
            self.ax.add_collection(self.tie_collection)

        # 高速铁路：橙色-红色实线（高德高铁风格）
        if high_speed_segments:
            self.ax.add_collection(LineCollection(
                high_speed_segments, colors='#F05A28',
                linewidths=self.high_speed_linewidth,
                zorder=3, label='高速铁路'
            ))
            high_speed_legend_added = True

        # 支线铁路：蓝色实线
        if branch_segments:
            self.ax.add_collection(LineCollection(
                branch_segments, colors='#1E88E5',
                linewidths=self.branch_linewidth,
                zorder=3, label='支线铁路'
            ))
            branch_legend_added = True

        # 计算各车站连接度（枢纽程度），用于按缩放级别显示站名/圆点
        degree = {}
        for (s1, s2) in self.connections:
            degree[s1] = degree.get(s1, 0) + 1
            degree[s2] = degree.get(s2, 0) + 1
        self._degree = degree
        # 端点站（度=1 的终点站）：无论缩放级别，其名称与圆点始终显示
        self._endpoints = {n for n, d in degree.items() if d == 1}

        # 站点：按连接度分级大小，合并为单个 scatter（性能更好），通过 alpha 数组控制 LOD
        self.station_order = list(self.stations.keys())
        xs = np.array([self.stations[n][0] for n in self.station_order])
        zs = np.array([self.stations[n][1] for n in self.station_order])
        sizes = []
        for name in self.station_order:
            deg = degree.get(name, 0)
            if deg >= 3:
                sizes.append(55)
            elif deg == 2:
                sizes.append(35)
            else:
                sizes.append(22)
        self.station_scatter = self.ax.scatter(
            xs, zs, s=np.array(sizes),
            facecolor='white', edgecolor='#333333',
            linewidth=0.8, zorder=4)
        self._station_alphas = np.ones(len(self.station_order), dtype=float)

        # 站名：小字、白底、轻微描边感，偏移适度避免糊在线条上
        self.station_labels = []
        for name, (xi, zi) in self.stations.items():
            txt = self.ax.text(xi + 10, zi + 8, name, fontsize=8,
                               color='#222222',
                               bbox=dict(facecolor='white', edgecolor='none',
                                         alpha=0.85, pad=0.5),
                               zorder=5)
            self.station_labels.append((name, txt))

        # 地图风格背景与坐标轴：白底、清晰边框与刻度，但不显示网格（保持干净）
        self.ax.set_facecolor('#FFFFFF')
        self.ax.set_xlabel('东西方向（正方向为东）', fontsize=11, color='#333333')
        self.ax.set_ylabel('南北方向（正方向为南）', fontsize=11, color='#333333')
        self.ax.set_title('铁路线路图', fontsize=13, fontweight='bold', color='#333333', pad=10)
        self.ax.grid(False)
        # 恢复坐标轴刻度与数字（之前为地图感关掉了，现重新开启）
        self.ax.tick_params(left=True, bottom=True,
                            labelleft=True, labelbottom=True,
                            labelsize=9, colors='#555555',
                            direction='out', length=4)
        for spine in self.ax.spines.values():
            spine.set_color('#888888')
            spine.set_linewidth(1.0)

        # 调整坐标范围 - 等比例显示（使用与底图一致的边界，避免失真）
        x_min, x_max, z_min, z_max = self._map_bounds
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(z_max, z_min)  # 反转 z 轴，正方向向下
        self.ax.set_aspect('equal', adjustable='datalim')

        # 图例：小巧、白底、浅色边框（含海陆底图说明）
        if normal_legend_added or high_speed_legend_added or branch_legend_added or self.show_terrain:
            handles, labels = self.ax.get_legend_handles_labels()
            if self.show_terrain:
                handles = list(handles) + [
                    Patch(facecolor='#BCDCF2', alpha=0.55, label='海洋（近似）'),
                    Patch(facecolor='#F3EFE6', alpha=0.45, label='陆地（近似）'),
                ]
            self.ax.legend(handles, [h.get_label() for h in handles], loc='upper right', fontsize=9,
                           frameon=True, facecolor='white', edgecolor='#CCCCCC',
                           framealpha=0.95)

        # ---- LOD / 枕木更新：记录全图跨度，连接缩放事件并首次计算 ----
        xr = self.ax.get_xlim(); zr = self.ax.get_ylim()
        self._full_span = max(xr[1] - xr[0], abs(zr[1] - zr[0]))
        if not getattr(self, '_lod_connected', False):
            self.ax.callbacks.connect('xlim_changed', self._on_view_change)
            self.ax.callbacks.connect('ylim_changed', self._on_view_change)
            self._lod_connected = True
        self._update_ties()
        self._update_label_visibility()

    def toggle_terrain(self):
        """切换海陆底图显示，并重绘地图。"""
        self.show_terrain = not self.show_terrain
        self.terrain_toggle_btn.config(
            text="海陆轮廓:开" if self.show_terrain else "海陆轮廓:关")
        self.ax.clear()
        self.draw_railway_map()
        self.canvas.draw()

    def _draw_terrain(self, bounds):
        """基于世界种子绘制程序化近似海陆底图（非 Minecraft 真实地形）。

        说明：Minecraft 基岩版地形生成管线为专有实现，Python 端无法精确复现。
        此处用确定性 value-noise(fBm) 生成高度场，低于 SEA_LEVEL 填海洋蓝、
        之上填陆地米色，颜色交界即海岸线，仅作地图视觉参考。

        采用 imshow 绘制（纯 numpy + Agg，不依赖 contourpy），兼容性更好。
        """
        if not self.show_terrain:
            self.terrain_artists = []
            return
        x_min, x_max, z_min, z_max = bounds
        step = TERRAIN_STEP
        nx = max(16, int((x_max - x_min) / step) + 1)
        nz = max(16, int((z_max - z_min) / step) + 1)
        xs = np.linspace(x_min, x_max, nx)
        zs = np.linspace(z_min, z_max, nz)
        X, Z = np.meshgrid(xs, zs)

        # 复用缓存（范围不变时避免重复计算）
        key = (nx, nz, round(x_min, 2), round(x_max, 2),
               round(z_min, 2), round(z_max, 2))
        cache = getattr(self, '_terrain_cache', None)
        if cache is None or cache[0] != key:
            H = self._terrain_height(X, Z)
            self._terrain_cache = (key, H)
        else:
            H = cache[1]

        sea = SEA_LEVEL
        # 构建 RGBA 图像：海洋蓝 / 陆地米色，半透明，颜色交界即海岸线
        ocean_rgb = np.array([0xBC / 255.0, 0xDC / 255.0, 0xF2 / 255.0])
        land_rgb = np.array([0xF3 / 255.0, 0xEF / 255.0, 0xE6 / 255.0])
        rgba = np.zeros((nz, nx, 4), dtype=float)
        mask_ocean = H < sea
        rgba[..., :3] = np.where(mask_ocean[..., np.newaxis], ocean_rgb, land_rgb)
        rgba[..., 3] = 0.55

        img = self.ax.imshow(
            rgba, extent=[x_min, x_max, z_min, z_max],
            origin='lower', zorder=0, interpolation='bilinear')
        self.terrain_artists = [img]

    def _terrain_height(self, X, Z):
        """确定性 fBm 高度场（由 WORLD_SEED 驱动），归一化到 [0,1)。"""
        span = max(float(X.max() - X.min()), float(Z.max() - Z.min()))
        base_freq = 1.0 / (span / 3.0)  # 大陆尺度约为地图 1/3
        H = np.zeros_like(X, dtype=float)
        amp = 1.0
        freq = base_freq
        # 把 63 位世界种子拆成两段 31 位，逐倍频参与哈希，确保种子真正决定地貌
        seed_lo = np.int64(WORLD_SEED & 0x7FFFFFFF)
        seed_hi = np.int64((WORLD_SEED >> 31) & 0x7FFFFFFF)
        for o in range(5):
            salt = np.int64((seed_lo + (o + 1) * 1013904223) & 0x7FFFFFFF) ^ seed_hi
            H += amp * self._value_noise(X, Z, freq, salt)
            amp *= 0.5
            freq *= 2.07  # 非整数倍，避免网格对齐伪影
        H -= H.min()
        H /= (H.max() + 1e-9)
        return H

    def _value_noise(self, X, Z, freq, salt):
        """值噪声（平滑插值），返回 [0,1) 的二维数组。"""
        fx = X * freq
        fz = Z * freq
        x0 = np.floor(fx).astype(np.int64)
        z0 = np.floor(fz).astype(np.int64)
        tx = fx - x0
        tz = fz - z0
        ux = tx * tx * (3.0 - 2.0 * tx)
        uz = tz * tz * (3.0 - 2.0 * tz)
        v00 = self._rand2(x0, z0, salt)
        v10 = self._rand2(x0 + 1, z0, salt)
        v01 = self._rand2(x0, z0 + 1, salt)
        v11 = self._rand2(x0 + 1, z0 + 1, salt)
        top = v00 * (1.0 - ux) + v10 * ux
        bot = v01 * (1.0 - ux) + v11 * ux
        return top * (1.0 - uz) + bot * uz

    def _rand2(self, i, j, salt):
        """整数坐标 -> [0,1) 的确定性伪随机（向量化整数哈希，种子驱动）。"""
        i64 = i.astype(np.int64)
        j64 = j.astype(np.int64)
        n = np.bitwise_xor(np.left_shift(i64, 13), j64).astype(np.int64) + salt
        n = np.bitwise_xor(n, np.right_shift(n, 17))
        n = (n * 1274126177).astype(np.int64)
        n = np.bitwise_and(n, np.int64(0x7FFFFFFF))
        return n.astype(np.float64) / float(0x7FFFFFFF)

if __name__ == "__main__":
    root = tk.Tk()
    app = RailwayApp(root)
    root.mainloop()