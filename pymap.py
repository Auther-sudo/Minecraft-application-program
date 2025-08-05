import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
import json
import os
import heapq
from tkinter import simpledialog, messagebox, filedialog, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

# 设置中文字体和负号显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

# 铁路速度设置 (单位: 米/秒)
SPEEDS = {
    'normal': 8,       # 普通铁路
    'high_speed': 12.4,  # 高速铁路
    'branch': 8        # 支线铁路，使用普通铁路速度
}

class RailwayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("铁路系统地图")
        # 使用用户指定的JSON文件路径
        self.data_file = r"C:\Users\Lenovo\Desktop\railmap\线路和车站数据.json"
        
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
        
        # 设定线段样式参数
        self.segment_length = 50  # 普通铁路黑白段长度
        self.high_speed_linewidth = 4  # 高速铁路线宽
        self.normal_linewidth = 4      # 普通铁路线宽
        self.branch_linewidth = 3      # 支线铁路线宽
        
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
        """管理车站：添加、编辑、删除"""
        # 创建管理窗口
        manage_window = tk.Toplevel(self.root)
        manage_window.title("车站管理")
        manage_window.geometry("600x500")
        manage_window.transient(self.root)
        manage_window.grab_set()
        
        # 顶部操作按钮
        top_btn_frame = ttk.Frame(manage_window)
        top_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(top_btn_frame, text="添加新车站", command=lambda: self.add_station(manage_window)).pack(side=tk.RIGHT, padx=5)
        
        # 创建搜索框
        search_frame = ttk.Frame(manage_window)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="搜索车站:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # 创建车站列表
        columns = ("name", "x_coord", "z_coord", "actions")
        tree = ttk.Treeview(manage_window, columns=columns, show="headings")
        
        # 定义列
        tree.heading("name", text="车站名称")
        tree.heading("x_coord", text="X坐标")
        tree.heading("z_coord", text="Z坐标")
        tree.heading("actions", text="操作")
        
        # 设置列宽
        tree.column("name", width=150)
        tree.column("x_coord", width=100)
        tree.column("z_coord", width=100)
        tree.column("actions", width=150)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(manage_window, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 刷新列表函数
        def refresh_list():
            # 清空现有数据
            for item in tree.get_children():
                tree.delete(item)
            
            # 添加数据
            search_text = search_var.get().lower()
            for name, (x, z) in self.stations.items():
                if search_text in name.lower():
                    item = tree.insert("", tk.END, values=(name, x, z, ""))
                    
                    # 创建操作按钮
                    x_pos, y_pos, width, height = tree.bbox(item, "actions")
                    frame = ttk.Frame(tree)
                    
                    # 编辑按钮
                    edit_btn = ttk.Button(
                        frame, 
                        text="编辑", 
                        width=6,
                        command=lambda n=name: [self.edit_station(n), refresh_list()]
                    )
                    edit_btn.pack(side=tk.LEFT, padx=2)
                    
                    # 删除按钮
                    delete_btn = ttk.Button(
                        frame, 
                        text="删除", 
                        width=6,
                        command=lambda n=name: [self.delete_station(n), refresh_list()]
                    )
                    delete_btn.pack(side=tk.LEFT, padx=2)
                    
                    frame.place(x=x_pos+5, y=y_pos+2, width=width-10, height=height-4)
        
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
        ttk.Radiobutton(type_frame, text="高速铁路", variable=rail_type_var, value="high_speed").pack(side=tk.LEFT, padx=10)
        
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
        
        # 查找最长运行时间
        max_time = 0.0
        max_path = []
        max_start = ""
        max_end = ""
        
        # 构建铁路网络图形表示
        graph = self._build_railway_graph()
        
        # 获取所有车站列表
        stations_list = list(self.stations.keys())
        
        # 检查所有可能的车站对
        for i in range(len(stations_list)):
            for j in range(i + 1, len(stations_list)):
                start = stations_list[i]
                end = stations_list[j]
                
                time, path = self._dijkstra_shortest_path(graph, start, end)
                if time and time > max_time:
                    max_time = time
                    max_path = path
                    max_start = start
                    max_end = end
        
        # 创建统计信息窗口
        stats_window = tk.Toplevel(self.root)
        stats_window.title("铁路系统统计信息")
        stats_window.geometry("500x400")
        stats_window.transient(self.root)
        
        # 显示里程统计
        ttk.Label(stats_window, text="铁路里程统计", font=("SimHei", 12, "bold")).pack(anchor=tk.W, padx=20, pady=10)
        
        ttk.Label(stats_window, text=f"总里程: {total_distance:.2f} 米", font=("SimHei", 10)).pack(anchor=tk.W, padx=30, pady=5)
        ttk.Label(stats_window, text=f"高速铁路里程: {high_speed_distance:.2f} 米", font=("SimHei", 10)).pack(anchor=tk.W, padx=30, pady=5)
        ttk.Label(stats_window, text=f"普通铁路里程: {normal_distance:.2f} 米", font=("SimHei", 10)).pack(anchor=tk.W, padx=30, pady=5)
        ttk.Label(stats_window, text=f"支线铁路里程: {branch_distance:.2f} 米", font=("SimHei", 10)).pack(anchor=tk.W, padx=30, pady=5)
        
        # 显示最长运行时间
        ttk.Label(stats_window, text="\n最长运行时间", font=("SimHei", 12, "bold")).pack(anchor=tk.W, padx=20, pady=10)
        
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
            
            ttk.Label(stats_window, text=f"最长时间: {time_str}", font=("SimHei", 10)).pack(anchor=tk.W, padx=30, pady=5)
            ttk.Label(stats_window, text=f"站点: {max_start} 到 {max_end}", font=("SimHei", 10)).pack(anchor=tk.W, padx=30, pady=5)
            
            ttk.Label(stats_window, text="路线:", font=("SimHei", 10, "bold")).pack(anchor=tk.W, padx=30, pady=5)
            path_text = " → ".join(max_path)
            path_label = ttk.Label(stats_window, text=path_text, wraplength=400, font=("SimHei", 10))
            path_label.pack(anchor=tk.W, padx=30, pady=5)
        else:
            ttk.Label(stats_window, text="没有可用的运行时间数据", font=("SimHei", 10)).pack(anchor=tk.W, padx=30, pady=5)
        
        ttk.Button(stats_window, text="关闭", command=stats_window.destroy).pack(pady=20)

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

    def draw_railway_map(self):
        """绘制铁路系统地图"""
        # 用于控制图例只显示一次
        normal_legend_added = False
        high_speed_legend_added = False
        branch_legend_added = False
        
        # 绘制所有连接
        for (s1, s2), conn_type in self.connections.items():
            if s1 not in self.stations or s2 not in self.stations:
                continue  # 跳过无效连接
                
            x1, z1 = self.stations[s1]
            x2, z2 = self.stations[s2]
            
            # 计算方向向量
            dx_vec = x2 - x1
            dz_vec = z2 - z1
            segment_dist = np.sqrt(dx_vec**2 + dz_vec**2)
            
            if segment_dist <= 0:
                continue  # 跳过零长度线段
            
            dx_normalized = dx_vec / segment_dist
            dz_normalized = dz_vec / segment_dist
            
            # 根据铁路类型绘制不同样式的线路
            if conn_type == 'high_speed':
                # 高速铁路：红色实线
                label = '高速铁路' if not high_speed_legend_added else ""
                self.ax.plot([x1, x2], [z1, z2], color='#FF0000', linewidth=self.high_speed_linewidth, 
                        label=label)
                if not high_speed_legend_added:
                    high_speed_legend_added = True
            elif conn_type == 'branch':
                # 支线铁路：蓝色实线
                label = '支线铁路' if not branch_legend_added else ""
                self.ax.plot([x1, x2], [z1, z2], color='#0000FF',  # 蓝色
                        linewidth=self.branch_linewidth, label=label)
                if not branch_legend_added:
                    branch_legend_added = True
            else:  # normal
                # 普通铁路：黑白相间线段
                current_length = 0
                is_black = True  # 起始为黑色
                
                while current_length < segment_dist:
                    remaining = segment_dist - current_length
                    length = min(self.segment_length, remaining)
                    
                    x_start = x1 + current_length * dx_normalized
                    z_start = z1 + current_length * dz_normalized
                    x_end = x_start + length * dx_normalized
                    z_end = z_start + length * dz_normalized
                    
                    color = 'black' if is_black else 'white'
                    # 只为第一段线段添加图例标签
                    label = '普通铁路' if (not normal_legend_added and current_length == 0) else ""
                    self.ax.plot([x_start, x_end], [z_start, z_end], color=color, 
                            linewidth=self.normal_linewidth, label=label)
                    
                    if not normal_legend_added and current_length == 0:
                        normal_legend_added = True
                        
                    current_length += length
                    is_black = not is_black

        # 绘制所有车站
        for name, (xi, zi) in self.stations.items():
            # 所有车站使用统一样式
            self.ax.scatter(xi, zi, s=200, facecolor='white', edgecolor='black', linewidth=1.5, zorder=3)
            self.ax.scatter(xi, zi, s=100, facecolor='white', edgecolor='none', zorder=4)

        # 标注站点名称
        for name, (xi, zi) in self.stations.items():
            self.ax.text(xi + 15, zi + 15, name, fontsize=10, fontweight='bold',
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.8))

        # 设置坐标轴和样式
        self.ax.set_xlabel('X轴（位置）', fontsize=12)
        self.ax.set_ylabel('Z轴（位置）', fontsize=12)
        self.ax.set_title('铁路线路图', fontsize=14, fontweight='bold')
        self.ax.grid(True, linestyle='--', alpha=0.3, zorder=0)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)

        # 调整坐标范围 - 如果有车站的话
        if self.stations:
            all_x = [p[0] for p in self.stations.values()]
            all_z = [p[1] for p in self.stations.values()]
            x_min, x_max = min(all_x) - 50, max(all_x) + 50
            z_min, z_max = min(all_z) - 50, max(all_z) + 50
            self.ax.set_xlim(x_min, x_max)
            self.ax.set_ylim(z_min, z_max)
        else:
            # 如果没有车站，设置默认范围
            self.ax.set_xlim(-1000, 1000)
            self.ax.set_ylim(-1000, 1000)

        # 添加图例
        self.ax.legend(loc='upper right', fontsize=10, frameon=True, facecolor='white', framealpha=0.8)

if __name__ == "__main__":
    root = tk.Tk()
    app = RailwayApp(root)
    root.mainloop()