import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import math
from collections import defaultdict, deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime

# 设置中文字体和负号显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

# QIXIA_STATION是一个常量
QIXIA_STATION = "栖霞"

"""铁路系统类，管理车站和线路信息"""
class RailwaySystem:
    def __init__(self, file_path):
        """初始化铁路系统，加载数据"""
        self.file_path = file_path
        self.stations = {}  # 车站及其坐标
        self.connections = defaultdict(list)  # 车站连接关系
        self.load_data()
    
    def load_data(self):
        """从JSON文件加载数据"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.stations = data['stations']
            
            # 构建连接关系图
            for connection in data['connections']:
                stations_pair, line_type = connection
                station1, station2 = stations_pair
                # 添加双向连接
                self.connections[station1].append((station2, line_type))
                self.connections[station2].append((station1, line_type))
                
        except Exception as e:
            print(f"加载数据出错: {e}")
            raise
    
    def get_distance(self, station1, station2):
        """计算两个车站之间的直线距离（米）"""
        if station1 not in self.stations or station2 not in self.stations:
            return 0
        
        x1, y1 = self.stations[station1]
        x2, y2 = self.stations[station2]
        
        # 计算欧几里得距离
        distance = abs(x2 - x1) + abs(y2 - y1)
        return distance
    
    def get_travel_time(self, station1, station2, line_type):
        """计算两个车站之间的行驶时间（秒）"""
        distance = self.get_distance(station1, station2)
        if distance == 0:
            return 0
            
        # 根据线路类型确定速度
        if line_type == "high_speed":
            speed = 12  # m/s
        else:  # normal 或 branch
            speed = 8   # m/s
            
        # 计算时间（秒），向上取整
        return math.ceil(distance / speed)
    
    def find_shortest_path(self, start, end):
        """查找从起点到终点的最短路径（按距离）"""
        if start not in self.stations or end not in self.stations:
            return []
            
        # Dijkstra算法寻找最短路径
        distances = {station: float('inf') for station in self.stations}
        distances[start] = 0
        predecessors = {station: None for station in self.stations}
        visited = set()
        
        while visited != set(self.stations):
            # 找到未访问的距离最近的节点
            current_station = None
            min_distance = float('inf')
            for station in self.stations:
                if station not in visited and distances[station] < min_distance:
                    min_distance = distances[station]
                    current_station = station
                    
            if current_station is None:
                break  # 无法到达
            
            if current_station == end:
                break  # 已到达终点
            
            visited.add(current_station)
            
            # 更新邻居的距离
            for neighbor, _ in self.connections[current_station]:
                if neighbor not in visited:
                    new_distance = distances[current_station] + self.get_distance(current_station, neighbor)
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        predecessors[neighbor] = current_station
        
        # 重建路径
        path = []
        current = end
        while current is not None:
            path.append(current)
            current = predecessors[current]
        
        return path[::-1]  # 反转路径

    def get_all_possible_paths(self, start, end):
        """获取起点到终点所有可能的路径"""
        if start not in self.stations or end not in self.stations:
            return []
            
        paths = []
        queue = deque([(start, [start])])
        
        while queue:
            current, path = queue.popleft()
            
            if current == end:
                paths.append(path)
                continue
                
            for neighbor, _ in self.connections[current]:
                if neighbor not in path:  # 避免循环
                    new_path = path.copy()
                    new_path.append(neighbor)
                    queue.append((neighbor, new_path))
        
        return paths
    
    def get_line_type(self, station1, station2):
        """获取两站之间的线路类型"""
        for neighbor, line_type in self.connections[station1]:
            if neighbor == station2:
                return line_type
        return "normal"  # 默认类型
    
    def get_section(self, station1, station2):
        """获取两个车站之间的区间（按字母顺序排序，避免重复）"""
        return tuple(sorted([station1, station2]))


"""列车调度器类，用于生成列车时刻表"""
class TrainScheduler:
    def __init__(self, railway_system):
        self.railway = railway_system
        self.start_station = None
        self.end_station = None
        self.all_possible_routes = []
        self.selected_route = []
        self.selected_stations = []
        self.stop_times = {}  # 站点停靠时间（秒）
        self.departure_time = None
        self.timetable = []
        self.train_id = None
    
    def set_stations(self, start, end):
        """设置起点和终点车站"""
        if start in self.railway.stations and end in self.railway.stations:
            self.start_station = start
            self.end_station = end
            self.all_possible_routes = self.railway.get_all_possible_paths(start, end)
            return True
        return False
    
    def set_selected_route(self, route_index):
        """选择一条路径"""
        if 0 <= route_index < len(self.all_possible_routes):
            self.selected_route = self.all_possible_routes[route_index]
            return True
        return False
    
    def get_route_stations(self):
        """获取所选路径上的所有站点"""
        return self.selected_route.copy()
    
    def set_stop_stations(self, stations):
        """设置停靠站点"""
        # 检查所选站点是否都在路线上
        for station in stations:
            if station not in self.selected_route:
                return False
        
        # 确保起点和终点在停靠站点中
        if self.start_station not in stations:
            stations.insert(0, self.start_station)
        if self.end_station not in stations:
            stations.append(self.end_station)
        
        # 按路线顺序排序停靠站点
        self.selected_stations = [station for station in self.selected_route if station in stations]
        return True
    
    def set_stop_time(self, station, time):
        """设置站点停靠时间（秒）"""
        if station in self.selected_stations:
            self.stop_times[station] = time
            return True
        return False
    
    def set_departure_time(self, time_str):
        """设置出发时间（HH:MM格式）"""
        try:
            self.departure_time = datetime.datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False
    
    def calculate_timetable(self):
        """计算时刻表"""
        if not all([self.start_station, self.end_station, self.selected_stations, self.departure_time]):
            return False
        
        self.timetable = []
        current_time = self.departure_time
        total_distance = 0
        
        # 添加起点站
        self.timetable.append({
            "station": self.start_station,
            "arrival": "-",
            "departure": current_time.strftime("%H:%M"),
            "distance": total_distance
        })
        
        # 计算后续各站的时间
        for i in range(1, len(self.selected_stations)):
            prev_station = self.selected_stations[i-1]
            curr_station = self.selected_stations[i]
            
            # 计算两站之间的距离和行驶时间
            distance = self.railway.get_distance(prev_station, curr_station)
            total_distance += distance
            line_type = self.railway.get_line_type(prev_station, curr_station)
            travel_time = self.railway.get_travel_time(prev_station, curr_station, line_type)
            
            # 到达当前站的时间
            current_time += datetime.timedelta(seconds=travel_time)
            arrival_time = current_time.strftime("%H:%M")
            
            # 如果是终点站，没有出发时间
            if curr_station == self.end_station:
                self.timetable.append({
                    "station": curr_station,
                    "arrival": arrival_time,
                    "departure": "-",
                    "distance": total_distance
                })
                break
            
            # 停靠时间（默认60秒）
            stop_time = self.stop_times.get(curr_station, 60)
            current_time += datetime.timedelta(seconds=stop_time)
            departure_time = current_time.strftime("%H:%M")
            
            self.timetable.append({
                "station": curr_station,
                "arrival": arrival_time,
                "departure": departure_time,
                "distance": total_distance
            })
        
        return True
    
    def to_dict(self):
        """转换为字典，用于保存到JSON"""
        return {
            "train_id": self.train_id,
            "start_station": self.start_station,
            "end_station": self.end_station,
            "departure_time": self.departure_time.strftime("%H:%M") if self.departure_time else "",
            "stop_times": self.stop_times,
            "selected_stations": self.selected_stations,
            "timetable": self.timetable,
            "selected_route": self.selected_route
        }
    
    def from_dict(self, data):
        """从字典加载数据"""
        self.train_id = data.get("train_id")
        self.start_station = data.get("start_station")
        self.end_station = data.get("end_station")
        self.stop_times = data.get("stop_times", {})
        self.selected_stations = data.get("selected_stations", [])
        self.timetable = data.get("timetable", [])
        self.selected_route = data.get("selected_route", [])
        
        departure_time_str = data.get("departure_time")
        if departure_time_str:
            self.departure_time = datetime.datetime.strptime(departure_time_str, "%H:%M")
        
        # 重新计算可能的路线（虽然不会使用，但保持数据一致性）
        if self.start_station and self.end_station:
            self.all_possible_routes = self.railway.get_all_possible_paths(self.start_station, self.end_station)
        
        return self


"""列车类，用于管理单列车的信息和运行计划"""
class Train:
    """列车类，用于管理单列车的信息和运行计划"""
    def __init__(self, train_id, scheduler):
        self.train_id = train_id  # 现在这里存储的是用户定义的车次
        self.scheduler = scheduler
        self.railway = scheduler.railway
        self.section_occupation = []  # 记录区间占用情况 (section, start_time, end_time)
        self.calculate_section_occupation()  # 初始化时计算区间占用
        
    def get_section_occupation(self):
        """获取列车的区间占用情况"""
        return self.section_occupation
        
    def calculate_section_occupation(self):
        """计算列车对各区间的占用时间"""
        self.section_occupation = []
        timetable = self.scheduler.timetable
        
        for i in range(len(timetable) - 1):
            # 当前站信息
            curr_entry = timetable[i]
            curr_station = curr_entry["station"]
            depart_time = datetime.datetime.strptime(curr_entry["departure"], "%H:%M")
            
            # 下一站信息
            next_entry = timetable[i+1]
            next_station = next_entry["station"]
            arrive_time = datetime.datetime.strptime(next_entry["arrival"], "%H:%M")
            
            # 获取区间
            section = self.railway.get_section(curr_station, next_station)
            
            # 记录区间占用
            self.section_occupation.append({
                "section": section,
                "start_time": depart_time,
                "end_time": arrive_time
            })


"""列车管理器类，用于管理多列车并检测冲突"""
class TrainManager:
    def __init__(self, railway_system):
        self.railway = railway_system
        self.trains = []  # 存储所有列车对象
        self.SAFE_INTERVAL = datetime.timedelta(seconds=30)  # 安全间隔时间（可调整）
    
    def add_train(self, scheduler, prefix):
        """添加列车并检查冲突，返回列车ID和冲突信息"""
        # 生成列车ID
        train_id = self.generate_train_id(scheduler, prefix)
        if not train_id:
            return None, None
        
        # 创建列车对象
        new_train = Train(train_id, scheduler)
        
        # 检查冲突
        conflicts = self.check_conflicts(new_train)
        if conflicts:
            return train_id, conflicts
        
        # 没有冲突，添加列车
        self.trains.append(new_train)
        return train_id, None
    
    def generate_train_id(self, scheduler, prefix):
        """根据终点站与起点站到栖霞站的距离生成列车ID"""
        if not scheduler.start_station or not scheduler.end_station:
            return None
    
        # 计算起点站到栖霞站的最短路径距离（以站点数-1作为距离）
        start_to_qixia = self.railway.find_shortest_path(scheduler.start_station, QIXIA_STATION)
        start_dist = len(start_to_qixia) - 1 if start_to_qixia else float('inf')  # 无路径时设为无穷大
    
        # 计算终点站到栖霞站的最短路径距离
        end_to_qixia = self.railway.find_shortest_path(scheduler.end_station, QIXIA_STATION)
        end_dist = len(end_to_qixia) - 1 if end_to_qixia else float('inf')
    
        # 判断规则：
        # 终点站比起点站近栖霞站 → 双数
        # 终点站比起点站远栖霞站 → 单数
        is_farther = end_dist > start_dist  # 更远则用单数
        is_closer = end_dist < start_dist   # 更近则用双数
    
        # 处理距离相等的情况（可根据实际需求调整）
        if end_dist == start_dist:
        # 距离相等时默认按单数处理，可根据业务需求修改
            is_farther = True
            is_closer = False
    
        # 查找同方向已有列车数量
        count = 0
        for train in self.trains:
            if train.train_id.startswith(prefix):
                count += 1
    
    # 生成车次号（单数或双数）
        if is_farther:
            number = count * 2 + 1  # 单数
        elif is_closer:
            number = (count + 1) * 2  # 双数
        else:
            return None  # 理论上不会走到这里
    
        return f"{prefix}{number}"

    
    def check_conflicts(self, new_train):
        """检查新列车与现有列车的区间占用冲突"""
        conflicts = []
        
        # 检查与每列现有列车的冲突
        for existing_train in self.trains:
            # 检查每个区间的占用情况
            for new_occ in new_train.section_occupation:
                for existing_occ in existing_train.section_occupation:
                    # 区间相同才可能冲突
                    if new_occ["section"] == existing_occ["section"]:
                        # 提取时间并添加安全间隔
                        new_start = new_occ["start_time"]
                        new_end = new_occ["end_time"]
                        existing_start = existing_occ["start_time"]
                        existing_end = existing_occ["end_time"]
                        
                        # 检查时间重叠（包含安全间隔）
                        if (new_end + self.SAFE_INTERVAL > existing_start and 
                            new_start < existing_end + self.SAFE_INTERVAL):
                            # 发现冲突
                            conflicts.append({
                                "section": new_occ["section"],
                                "existing_train": existing_train.train_id,
                                "existing_time": (existing_occ["start_time"], existing_occ["end_time"]),
                                "new_train": new_train.train_id,
                                "new_time": (new_occ["start_time"], new_occ["end_time"])
                            })
        
        return conflicts if conflicts else None
    
    def update_train(self, old_train_id, new_scheduler):
        """更新现有列车信息"""
        # 查找要更新的列车
        for i, train in enumerate(self.trains):
            if train.train_id == old_train_id:
                # 创建新的列车对象
                new_train = Train(old_train_id, new_scheduler)
                
                # 检查与其他列车的冲突（排除自身）
                conflicts = []
                for existing_train in self.trains:
                    if existing_train.train_id == old_train_id:
                        continue
                        
                    # 检查每个区间的占用情况
                    for new_occ in new_train.section_occupation:
                        for existing_occ in existing_train.section_occupation:
                            if new_occ["section"] == existing_occ["section"]:
                                # 提取时间并添加安全间隔
                                new_start = new_occ["start_time"]
                                new_end = new_occ["end_time"]
                                existing_start = existing_occ["start_time"]
                                existing_end = existing_occ["end_time"]
                                
                                # 检查时间重叠（包含安全间隔）
                                if (new_end + self.SAFE_INTERVAL > existing_start and 
                                    new_start < existing_end + self.SAFE_INTERVAL):
                                    conflicts.append({
                                        "section": new_occ["section"],
                                        "existing_train": existing_train.train_id,
                                        "existing_time": (existing_occ["start_time"], existing_occ["end_time"]),
                                        "new_train": new_train.train_id,
                                        "new_time": (new_occ["start_time"], new_occ["end_time"])
                                    })
                
                if conflicts:
                    return False, conflicts
                
                # 替换列车
                self.trains[i] = new_train
                return True, None
        
        return False, ["未找到要更新的列车"]


"""GUI类，用户界面"""
class RailwayGUI:
    def __init__(self, root, railway_system):
        self.root = root
        self.root.title("铁路列车调度系统")
        self.root.geometry("1200x800")
        
        self.railway = railway_system
        self.train_manager = TrainManager(railway_system)
        self.current_scheduler = TrainScheduler(railway_system)
        self.all_schedulers = []  # 保存所有列车的调度信息
        self.last_saved_count = 0  # 记录最后一次保存时的列车数量
        self.editing_train_id = None  # 当前正在编辑的列车ID
        
        # 创建主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧控制面板
        self.control_frame = ttk.LabelFrame(self.main_frame, text="列车设置")
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 右侧显示区域
        self.display_frame = ttk.Frame(self.main_frame)
        self.display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 线路图区域
        self.map_frame = ttk.LabelFrame(self.display_frame, text="线路图")
        self.map_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 时刻表区域
        self.timetable_frame = ttk.LabelFrame(self.display_frame, text="时刻表")
        self.timetable_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化线路图
        self.init_map()
        
        # 初始化时刻表表格
        self.init_timetable_table()
        
        # 创建控制组件
        self.create_control_widgets()
        
        # 绘制初始线路图
        self.update_map()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def init_map(self):
        """初始化线路图画布"""
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 绑定点击事件
        self.canvas.mpl_connect('button_press_event', self.on_map_click)
        
        # 存储选中的站点
        self.selected_start = None
        self.selected_end = None
    
    def init_timetable_table(self):
        """初始化时刻表表格"""
        columns = ("station", "arrival", "departure", "distance")
        self.timetable_tree = ttk.Treeview(self.timetable_frame, columns=columns, show="headings")
        
        # 设置列标题
        self.timetable_tree.heading("station", text="车站")
        self.timetable_tree.heading("arrival", text="到达时间")
        self.timetable_tree.heading("departure", text="出发时间")
        self.timetable_tree.heading("distance", text="累计里程(米)")
        
        # 设置列宽
        self.timetable_tree.column("station", width=100)
        self.timetable_tree.column("arrival", width=80)
        self.timetable_tree.column("departure", width=80)
        self.timetable_tree.column("distance", width=100)
        
        self.timetable_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.timetable_frame, orient=tk.VERTICAL, command=self.timetable_tree.yview)
        self.timetable_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_control_widgets(self):
        """创建控制组件，添加车次命名相关控件"""
        # 数据加载区域
        ttk.Label(self.control_frame, text="数据管理:").pack(anchor=tk.W, padx=5, pady=10)
        
        # 加载数据按钮
        self.load_btn = ttk.Button(self.control_frame, text="加载数据", command=self.load_data)
        self.load_btn.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        # 列车选择列表（用于编辑）
        ttk.Label(self.control_frame, text="已加载列车:").pack(anchor=tk.W, padx=5, pady=5)
        self.trains_frame = ttk.Frame(self.control_frame)
        self.trains_frame.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        self.trains_listbox = tk.Listbox(self.trains_frame, selectmode=tk.SINGLE, width=25, height=5)
        self.trains_listbox.pack(side=tk.LEFT, fill=tk.Y)
        
        scrollbar_trains = ttk.Scrollbar(self.trains_frame, orient=tk.VERTICAL, command=self.trains_listbox.yview)
        self.trains_listbox.configure(yscroll=scrollbar_trains.set)
        scrollbar_trains.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 编辑和删除按钮
        self.edit_btn = ttk.Button(self.control_frame, text="编辑选中列车", command=self.select_train_for_editing, state=tk.DISABLED)
        self.edit_btn.pack(anchor=tk.W, padx=5, pady=2, fill=tk.X)
        
        self.delete_btn = ttk.Button(self.control_frame, text="删除选中列车", command=self.delete_selected_train, state=tk.DISABLED)
        self.delete_btn.pack(anchor=tk.W, padx=5, pady=2, fill=tk.X)
        
        ttk.Separator(self.control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=10)
        
        # 1. 起点终点选择
        ttk.Label(self.control_frame, text="始发站:").pack(anchor=tk.W, padx=5, pady=5)
        self.start_var = tk.StringVar()
        self.start_combo = ttk.Combobox(self.control_frame, textvariable=self.start_var, state="readonly", width=20)
        self.start_combo['values'] = sorted(self.railway.stations.keys())
        self.start_combo.pack(anchor=tk.W, padx=5, pady=5)
        
        ttk.Label(self.control_frame, text="终到站:").pack(anchor=tk.W, padx=5, pady=5)
        self.end_var = tk.StringVar()
        self.end_combo = ttk.Combobox(self.control_frame, textvariable=self.end_var, state="readonly", width=20)
        self.end_combo['values'] = sorted(self.railway.stations.keys())
        self.end_combo.pack(anchor=tk.W, padx=5, pady=5)
        
        # 车次前缀输入
        ttk.Label(self.control_frame, text="车次前缀 (如G、D):").pack(anchor=tk.W, padx=5, pady=5)
        self.train_prefix_var = tk.StringVar(value="G")
        self.train_prefix_entry = ttk.Entry(self.control_frame, textvariable=self.train_prefix_var, width=5)
        self.train_prefix_entry.pack(anchor=tk.W, padx=5, pady=5)
        
        # 显示车次规则说明
        ttk.Label(
            self.control_frame, 
            text=f"车次规则:\n开往{QIXIA_STATION}方向为单数\n驶离{QIXIA_STATION}方向为双数",
            justify=tk.LEFT
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # 第一步：获取可行路径按钮
        self.get_routes_btn = ttk.Button(self.control_frame, text="第一步：获取可行路径", command=self.get_possible_routes)
        self.get_routes_btn.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        # 可行路径列表
        ttk.Label(self.control_frame, text="可选路径:").pack(anchor=tk.W, padx=5, pady=5)
        self.routes_frame = ttk.Frame(self.control_frame)
        self.routes_frame.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        self.routes_listbox = tk.Listbox(self.routes_frame, selectmode=tk.SINGLE, width=25, height=5)
        self.routes_listbox.pack(side=tk.LEFT, fill=tk.Y)
        
        scrollbar_routes = ttk.Scrollbar(self.routes_frame, orient=tk.VERTICAL, command=self.routes_listbox.yview)
        self.routes_listbox.configure(yscroll=scrollbar_routes.set)
        scrollbar_routes.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 选择路径按钮
        self.select_route_btn = ttk.Button(self.control_frame, text="选择此路径", command=self.confirm_route_selection)
        self.select_route_btn.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        # 第二步：获取路径站点按钮
        self.get_route_stations_btn = ttk.Button(self.control_frame, text="第二步：获取路径站点", command=self.get_route_stations, state=tk.DISABLED)
        self.get_route_stations_btn.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        # 停靠站点列表
        ttk.Label(self.control_frame, text="可选停靠站点:").pack(anchor=tk.W, padx=5, pady=5)
        self.stations_frame = ttk.Frame(self.control_frame)
        self.stations_frame.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        self.stations_listbox = tk.Listbox(self.stations_frame, selectmode=tk.MULTIPLE, width=25, height=10)
        self.stations_listbox.pack(side=tk.LEFT, fill=tk.Y)
        
        scrollbar = ttk.Scrollbar(self.stations_frame, orient=tk.VERTICAL, command=self.stations_listbox.yview)
        self.stations_listbox.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 其他按钮
        self.set_stop_times_btn = ttk.Button(self.control_frame, text="设置停靠时间", command=self.set_stop_times)
        self.set_stop_times_btn.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        self.time_entry_label = ttk.Label(self.control_frame, text="出发时间 (HH:MM):")
        self.time_entry_label.pack(anchor=tk.W, padx=5, pady=5)
        self.time_entry = ttk.Entry(self.control_frame, width=20)
        self.time_entry.insert(0, "08:00")
        self.time_entry.pack(anchor=tk.W, padx=5, pady=5)
        
        # 计算/更新按钮（根据是否编辑状态显示不同文本）
        self.calculate_btn = ttk.Button(self.control_frame, text="计算时刻表", command=self.calculate_and_display)
        self.calculate_btn.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        self.save_btn = ttk.Button(self.control_frame, text="保存结果", command=self.save_results)
        self.save_btn.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        self.reset_btn = ttk.Button(self.control_frame, text="重置", command=self.reset_all)
        self.reset_btn.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        # 列车信息显示
        self.train_info_var = tk.StringVar(value="当前无列车")
        ttk.Label(self.control_frame, textvariable=self.train_info_var).pack(anchor=tk.W, padx=5, pady=20)
        
        # 已创建列车数量显示
        self.train_count_var = tk.StringVar(value="已创建列车: 0")
        ttk.Label(self.control_frame, textvariable=self.train_count_var).pack(anchor=tk.W, padx=5, pady=5)
        
        # 绑定列车列表选择事件
        self.trains_listbox.bind('<<ListboxSelect>>', self.on_train_select)
    
    def update_map(self, highlight_route=None):
        """更新线路图"""
        self.ax.clear()
    
        # 绘制所有线路（保持不变）
        drawn_connections = set()
        for station1 in self.railway.connections:
            for station2, line_type in self.railway.connections[station1]:
                if (station1, station2) in drawn_connections or (station2, station1) in drawn_connections:
                    continue
                drawn_connections.add((station1, station2))
            
                if line_type == "high_speed":
                    color = "red"
                    linewidth = 2
                elif line_type == "branch":
                    color = "green"
                    linewidth = 1.5
                else:
                    color = "blue"
                    linewidth = 1.5
            
                x1, y1 = self.railway.stations[station1]
                x2, y2 = self.railway.stations[station2]
                y1 = -y1  # 向上为负
                y2 = -y2  # 向下为正
            
                self.ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth, zorder=1)
    
        # 绘制所有车站（修改坐标和名称显示）
        for station, (x, y) in self.railway.stations.items():
            # Y轴取反，保持显示一致
            display_y = -y
        
            # 绘制车站点（保持不变）
            if station == self.selected_start:
                self.ax.scatter(x, display_y, color="green", s=20, zorder=3, label="始发站")
            elif station == self.selected_end:
                self.ax.scatter(x, display_y, color="red", s=20, zorder=3, label="终到站")
            elif station == QIXIA_STATION:
                self.ax.scatter(x, display_y, color="purple", s=20, zorder=3, label=f"{QIXIA_STATION}站")
            else:
                self.ax.scatter(x, display_y, color="black", s=10, zorder=2)
        
            # 只显示端点车站名称（起点、终点、栖霞站）
            if station in [self.selected_start, self.selected_end, QIXIA_STATION]:
                self.ax.text(x+100, display_y+50, station, fontsize=8, zorder=4)
    
    # 高亮显示选中的路线（保持不变）
        if highlight_route and len(highlight_route) > 1:
            for i in range(len(highlight_route)-1):
                station1 = highlight_route[i]
                station2 = highlight_route[i+1]
                x1, y1 = self.railway.stations[station1]
                x2, y2 = self.railway.stations[station2]
                self.ax.plot([x1, x2], [-y1, -y2], color="orange", linewidth=3, zorder=5)
    
        self.ax.set_title("铁路线路图")
        self.ax.set_aspect('equal', adjustable='box')
        self.ax.grid(True, linestyle='--', alpha=0.7)
    
        handles, labels = self.ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        self.ax.legend(by_label.values(), by_label.keys())
    
        self.canvas.draw()

    
    def on_map_click(self, event):
        """处理线路图点击事件"""
        if event.inaxes != self.ax:
            return
        
        # 查找最近的车站（修正y坐标计算）
        min_distance = float('inf')
        selected_station = None
    
        for station, (x, y) in self.railway.stations.items():
            # 对车站y坐标取反，与显示坐标保持一致
            display_y = -y
            # 计算与点击位置的距离
            distance = math.hypot(x - event.xdata, display_y - event.ydata)
            if distance < min_distance and distance < 500:  # 设置点击阈值
                min_distance = distance
                selected_station = station
    
        if selected_station:
            # 点击逻辑：第一点起点，第二点终点，第三点取消
            if self.selected_start is None:
                self.selected_start = selected_station
                self.start_var.set(selected_station)
            elif self.selected_end is None:
                self.selected_end = selected_station
                self.end_var.set(selected_station)
            else:
                self.selected_start = None
                self.selected_end = None
                self.start_var.set("")
                self.end_var.set("")
        
            self.update_map()
    
    def get_possible_routes(self):
        """第一步：获取所有可行路径"""
        start = self.start_var.get()
        end = self.end_var.get()
        
        if not start or not end:
            messagebox.showwarning("警告", "请先选择始发站和终到站")
            return
        
        if not self.current_scheduler.set_stations(start, end):
            messagebox.showerror("错误", "设置车站失败，请检查车站是否存在")
            return
        
        # 获取所有可能路径
        possible_routes = self.current_scheduler.all_possible_routes
        if not possible_routes:
            messagebox.showwarning("警告", "没有找到可行的路线")
            return
        
        # 清空并填充路径列表
        self.routes_listbox.delete(0, tk.END)
        for i, route in enumerate(possible_routes):
            route_str = " → ".join(route)  # 用箭头连接站点表示路径
            self.routes_listbox.insert(tk.END, f"路径{i+1}: {route_str}")
        
        # 高亮显示最短路径作为参考
        shortest_path = self.railway.find_shortest_path(start, end)
        self.update_map(shortest_path)
    
    def confirm_route_selection(self):
        """确认选择的路径"""
        selected_indices = self.routes_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "请先选择一条路径")
            return
        
        # 获取选中的路径索引
        route_index = selected_indices[0]
        if self.current_scheduler.set_selected_route(route_index):
            selected_route = self.current_scheduler.selected_route
            route_str = " → ".join(selected_route)
            messagebox.showinfo("提示", f"已选择路径：{route_str}")
            self.update_map(selected_route)
            # 启用第二步按钮
            self.get_route_stations_btn.config(state=tk.NORMAL)
        else:
            messagebox.showerror("错误", "选择路径失败")
    
    def get_route_stations(self):
        """第二步：获取所选路径上的站点"""
        if not self.current_scheduler.selected_route:
            messagebox.showwarning("警告", "请先选择路径")
            return
        
        # 获取路径上的所有站点
        route_stations = self.current_scheduler.get_route_stations()
        if not route_stations:
            messagebox.showwarning("警告", "路径上没有站点")
            return
        
        # 填充站点列表
        self.stations_listbox.delete(0, tk.END)
        start = self.current_scheduler.start_station
        end = self.current_scheduler.end_station
        for station in route_stations:
            if station == start:
                self.stations_listbox.insert(tk.END, f"{station} (始发站)")
                self.stations_listbox.selection_set(tk.END)  # 默认选中始发站
            elif station == end:
                self.stations_listbox.insert(tk.END, f"{station} (终到站)")
                self.stations_listbox.selection_set(tk.END)  # 默认选中终到站
            elif station == QIXIA_STATION:
                self.stations_listbox.insert(tk.END, f"{station} (方向站)")
            else:
                self.stations_listbox.insert(tk.END, station)
    
    def set_stop_times(self):
        """设置停靠时间"""
        selected_indices = self.stations_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "请先选择停靠站点")
            return
        
        # 提取选中的站点（去除括号内容）
        selected_stations = []
        for i in selected_indices:
            station_text = self.stations_listbox.get(i)
            # 去除括号及其中的内容
            station = station_text.split('(')[0].strip()
            selected_stations.append(station)
        
        # 设置停靠站点
        if not self.current_scheduler.set_stop_stations(selected_stations):
            messagebox.showerror("错误", "所选站点无法组成有效路线")
            return
        
        # 询问每个站点的停靠时间
        for station in self.current_scheduler.selected_stations:
            if station == self.current_scheduler.start_station or station == self.current_scheduler.end_station:
                continue  # 跳过起点和终点
            
            # 如果已有停靠时间，显示当前值
            current_time = self.current_scheduler.stop_times.get(station, 60)
            while True:
                stop_time_str = simpledialog.askstring(
                    "停靠时间", 
                    f"请输入 {station} 的停靠时间（秒）:", 
                    parent=self.root,
                    initialvalue=str(current_time)
                )
                
                if stop_time_str is None:  # 用户取消
                    return
                    
                if not stop_time_str:  # 空输入使用默认值
                    self.current_scheduler.set_stop_time(station, 60)
                    break
                    
                try:
                    stop_time = int(stop_time_str)
                    if stop_time >= 0:
                        self.current_scheduler.set_stop_time(station, stop_time)
                        break
                    else:
                        messagebox.showwarning("警告", "停靠时间不能为负数")
                except ValueError:
                    messagebox.showwarning("警告", "请输入有效的数字")
    
    def calculate_and_display(self):
        """计算并显示时刻表，同时检查冲突"""
        # 获取车次前缀
        train_prefix = self.train_prefix_var.get().strip()
        if not train_prefix and not self.editing_train_id:
            messagebox.showwarning("警告", "请输入车次前缀")
            return
        
        # 设置出发时间
        time_str = self.time_entry.get()
        if not self.current_scheduler.set_departure_time(time_str):
            messagebox.showerror("错误", "时间格式错误，请使用HH:MM格式")
            return
        
        # 计算时刻表
        if not self.current_scheduler.calculate_timetable():
            messagebox.showerror("错误", "计算时刻表失败，请检查设置")
            return
        
        # 处理编辑模式
        if self.editing_train_id:
            # 更新现有列车
            success, conflicts = self.train_manager.update_train(self.editing_train_id, self.current_scheduler)
            
            if not success:
                messagebox.showerror("错误", "\n".join(conflicts) if isinstance(conflicts, list) else str(conflicts))
                return
                
            if conflicts:
                # 显示冲突信息
                conflict_msg = "检测到列车冲突：\n"
                for conflict in conflicts:
                    section = " - ".join(conflict["section"])
                    existing_start = conflict["existing_time"][0].strftime("%H:%M")
                    existing_end = conflict["existing_time"][1].strftime("%H:%M")
                    new_start = conflict["new_time"][0].strftime("%H:%M")
                    new_end = conflict["new_time"][1].strftime("%H:%M")
                    
                    conflict_msg += (f"区间 {section}：\n"
                                    f"  现有列车 {conflict['existing_train']}：{existing_start}-{existing_end}\n"
                                    f"  新列车 {conflict['new_train']}：{new_start}-{new_end}\n\n")
                
                messagebox.showerror("冲突警告", conflict_msg)
                return
            
            # 更新调度器列表
            for i, scheduler in enumerate(self.all_schedulers):
                if scheduler.train_id == self.editing_train_id:
                    self.all_schedulers[i] = self.current_scheduler
                    break
            
            messagebox.showinfo("成功", f"列车 {self.editing_train_id} 已更新")
            train_id = self.editing_train_id
            # 退出编辑模式
            self.editing_train_id = None
            self.calculate_btn.config(text="计算时刻表")
        else:
            # 创建当前调度器的副本
            scheduler_copy = TrainScheduler(self.railway)
            scheduler_copy.__dict__.update(self.current_scheduler.__dict__)
            
            # 添加新列车
            train_id, conflicts = self.train_manager.add_train(scheduler_copy, train_prefix)
            
            if conflicts:
                # 显示冲突信息
                conflict_msg = "检测到列车冲突：\n"
                for conflict in conflicts:
                    section = " - ".join(conflict["section"])
                    existing_start = conflict["existing_time"][0].strftime("%H:%M")
                    existing_end = conflict["existing_time"][1].strftime("%H:%M")
                    new_start = conflict["new_time"][0].strftime("%H:%M")
                    new_end = conflict["new_time"][1].strftime("%H:%M")
                    
                    conflict_msg += (f"区间 {section}：\n"
                                    f"  现有列车 {conflict['existing_train']}：{existing_start}-{existing_end}\n"
                                    f"  新列车 {conflict['new_train']}：{new_start}-{new_end}\n\n")
                
                messagebox.showerror("冲突警告", conflict_msg)
                return
            
            if not train_id:
                messagebox.showerror("错误", "无法添加列车，请检查设置")
                return
            
            # 保存列车ID
            scheduler_copy.train_id = train_id
            self.all_schedulers.append(scheduler_copy)
        
        # 更新显示信息
        self.train_info_var.set(f"当前列车: {train_id}")
        self.train_count_var.set(f"已创建列车: {len(self.all_schedulers)}")
        
        # 显示当前列车的时刻表
        self.timetable_tree.delete(*self.timetable_tree.get_children())
        for entry in self.current_scheduler.timetable:
            self.timetable_tree.insert("", tk.END, values=(
                entry["station"],
                entry["arrival"],
                entry["departure"],
                entry["distance"]
            ))
        
        # 高亮显示所选路线
        self.update_map(self.current_scheduler.selected_stations)
        
        # 更新列车列表
        self.update_trains_listbox()
        
        # 重置当前调度器，为下一次列车编组做准备（编辑模式除外）
        if not self.editing_train_id:
            self.current_scheduler = TrainScheduler(self.railway)
        
        if self.editing_train_id:
            messagebox.showinfo("成功", f"列车 {train_id} 已更新")
        else:
            messagebox.showinfo("成功", f"列车 {train_id} 已添加，无冲突\n可继续添加其他列车")
    
    def save_results(self):
        """保存生成的结果到JSON文件"""
        if not self.all_schedulers:
            messagebox.showwarning("警告", "没有可保存的列车信息")
            return
        
        # 保存路径
        save_path = r"E:\我的世界railmap\列车数据.json"
        
        try:
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 准备要保存的数据
            all_trains_data = [scheduler.to_dict() for scheduler in self.all_schedulers]
            
            # 保存到文件
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(all_trains_data, f, ensure_ascii=False, indent=4)
            
            # 更新最后保存的列车数量
            self.last_saved_count = len(self.all_schedulers)
            messagebox.showinfo("成功", f"所有列车数据已保存到 {save_path}\n共保存 {len(self.all_schedulers)} 列列车信息")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def load_data(self):
        """加载JSON文件数据"""
        # 加载路径
        load_path = r"E:\我的世界railmap\列车数据.json"
        
        if not os.path.exists(load_path):
            messagebox.showwarning("警告", f"文件不存在: {load_path}")
            return
        
        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 清空现有数据
            self.all_schedulers = []
            self.train_manager.trains = []
            
            # 加载每个列车的数据
            for train_data in data:
                scheduler = TrainScheduler(self.railway).from_dict(train_data)
                self.all_schedulers.append(scheduler)
                # 同时添加到列车管理器
                self.train_manager.trains.append(Train(scheduler.train_id, scheduler))
            
            # 更新显示
            self.last_saved_count = len(self.all_schedulers)
            self.train_count_var.set(f"已创建列车: {len(self.all_schedulers)}")
            self.update_trains_listbox()
            
            messagebox.showinfo("成功", f"已加载 {len(self.all_schedulers)} 列列车数据")
        except Exception as e:
            messagebox.showerror("错误", f"加载失败: {str(e)}")
    
    def update_trains_listbox(self):
        """更新列车列表框"""
        self.trains_listbox.delete(0, tk.END)
        for scheduler in self.all_schedulers:
            if scheduler.train_id:
                self.trains_listbox.insert(tk.END, f"{scheduler.train_id}: {scheduler.start_station}→{scheduler.end_station}")
        
        # 禁用编辑和删除按钮
        self.edit_btn.config(state=tk.DISABLED)
        self.delete_btn.config(state=tk.DISABLED)
    
    def on_train_select(self, event):
        """处理列车选择事件"""
        selected_indices = self.trains_listbox.curselection()
        if selected_indices:
            self.edit_btn.config(state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
        else:
            self.edit_btn.config(state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)
    
    def select_train_for_editing(self):
        """选择要编辑的列车"""
        selected_indices = self.trains_listbox.curselection()
        if not selected_indices:
            return
        
        index = selected_indices[0]
        if 0 <= index < len(self.all_schedulers):
            # 获取选中的列车调度器
            selected_scheduler = self.all_schedulers[index]
            self.editing_train_id = selected_scheduler.train_id
            
            # 创建一个新的调度器副本用于编辑
            self.current_scheduler = TrainScheduler(self.railway)
            self.current_scheduler.__dict__.update(selected_scheduler.__dict__)
            
            # 填充编辑表单
            self.start_var.set(selected_scheduler.start_station)
            self.end_var.set(selected_scheduler.end_station)
            
            # 设置出发时间
            if selected_scheduler.departure_time:
                self.time_entry.delete(0, tk.END)
                self.time_entry.insert(0, selected_scheduler.departure_time.strftime("%H:%M"))
            
            # 更新车次前缀
            if selected_scheduler.train_id:
                prefix = ''.join([c for c in selected_scheduler.train_id if not c.isdigit()])
                self.train_prefix_var.set(prefix)
            
            # 获取路径
            self.get_possible_routes()
            
            # 选择对应的路径
            if selected_scheduler.selected_route and selected_scheduler.all_possible_routes:
                for i, route in enumerate(selected_scheduler.all_possible_routes):
                    if route == selected_scheduler.selected_route:
                        self.routes_listbox.selection_set(i)
                        self.confirm_route_selection()
                        break
            
            # 更新按钮文本
            self.calculate_btn.config(text="更新时刻表")
            
            # 显示当前编辑的列车
            self.train_info_var.set(f"正在编辑: {self.editing_train_id}")
            
            # 显示时刻表
            self.timetable_tree.delete(*self.timetable_tree.get_children())
            for entry in selected_scheduler.timetable:
                self.timetable_tree.insert("", tk.END, values=(
                    entry["station"],
                    entry["arrival"],
                    entry["departure"],
                    entry["distance"]
                ))
    
    def delete_selected_train(self):
        """删除选中的列车"""
        selected_indices = self.trains_listbox.curselection()
        if not selected_indices:
            return
        
        index = selected_indices[0]
        if 0 <= index < len(self.all_schedulers):
            train_id = self.all_schedulers[index].train_id
            if messagebox.askyesno("确认", f"确定要删除列车 {train_id} 吗？"):
                # 从调度器列表中删除
                del self.all_schedulers[index]
                
                # 从列车管理器中删除
                self.train_manager.trains = [
                    train for train in self.train_manager.trains 
                    if train.train_id != train_id
                ]
                
                # 更新显示
                self.update_trains_listbox()
                self.train_count_var.set(f"已创建列车: {len(self.all_schedulers)}")
                messagebox.showinfo("成功", f"列车 {train_id} 已删除")
    
    def reset_all(self):
        """重置所有设置，准备创建新列车"""
        self.start_var.set("")
        self.end_var.set("")
        self.time_entry.delete(0, tk.END)
        self.time_entry.insert(0, "08:00")
        self.routes_listbox.delete(0, tk.END)
        self.stations_listbox.delete(0, tk.END)
        
        # 退出编辑模式
        self.editing_train_id = None
        self.calculate_btn.config(text="计算时刻表")
        
        # 创建新的调度器
        self.current_scheduler = TrainScheduler(self.railway)
        self.selected_start = None
        self.selected_end = None
        
        # 禁用相关按钮
        self.get_route_stations_btn.config(state=tk.DISABLED)
        
        # 清空时刻表显示
        self.timetable_tree.delete(*self.timetable_tree.get_children())
        
        self.update_map()
        self.train_info_var.set("当前无列车")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        # 检查是否有未保存的数据
        if len(self.all_schedulers) > self.last_saved_count:
            result = messagebox.askyesnocancel("提示", "有未保存的列车数据，是否保存？")
            if result is None:  # 取消关闭
                return
            elif result:  # 保存
                self.save_results()
        
        # 确认关闭
        self.root.destroy()


def main():
    # 文件路径（请根据实际情况修改）
    file_path = r"E:\我的世界railmap\线路和车站数据.json"
    
    try:
        # 初始化铁路系统
        railway = RailwaySystem(file_path)
        
        # 创建GUI
        root = tk.Tk()
        app = RailwayGUI(root, railway)
        root.mainloop()
        
    except Exception as e:
        print(f"程序出错: {e}")
        messagebox.showerror("错误", f"无法加载数据: {str(e)}")


if __name__ == "__main__":
    main()