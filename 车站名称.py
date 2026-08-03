import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from openai import OpenAI

class MCStationNameGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("MC铁路车站名称生成器")
        self.root.geometry("800x700")
        self.root.configure(bg="#f0f5f9")
        
        # 所有环境选项
        self.environments = [
            "积雪冻原", "冰刺平原", "积雪针叶林", "冻河", "高耸山峰", 
            "覆雪山峰", "积雪山坡", "山地", "繁茂山地", "沙砾山地", 
            "山间草甸", "云杉林", "巨型针叶林", "平原", "向日葵平原", 
            "橡木森林", "繁花森林", "桦木森林", "深色橡木森林", "沼泽", 
            "红树林沼泽", "热带丛林", "竹林", "蘑菇岛", "河流", 
            "普通沙滩", "石岸", "积雪沙滩", "普通沙漠", "沙漠丘陵", 
            "沙漠湖泊", "普通热带草原", "热带高原", "破碎的热带草原", 
            "破碎的热带高原", "恶地", "恶地高原", "恶地高原变种", 
            "繁茂恶地高原", "风蚀恶地", "冻洋", "冷水海洋（深蓝色）", 
            "暖水海洋（浅绿色）", "温水海洋（浅蓝色）", "溶洞", 
            "繁茂洞穴", "深暗之域"
        ]
        
        # 设置字体样式
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("微软雅黑", 10), background="#f0f5f9")
        self.style.configure("TButton", font=("微软雅黑", 10))
        self.style.configure("TCombobox", font=("微软雅黑", 10))
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题
        self.title_label = ttk.Label(
            self.main_frame, 
            text="MC铁路车站名称生成器", 
            font=("微软雅黑", 16, "bold")
        )
        self.title_label.pack(pady=(0, 20))
        
        # 创建偏好设置区域
        self.prefs_frame = ttk.LabelFrame(self.main_frame, text="车站设置", padding="10")
        self.prefs_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 周边环境选择（多选）
        ttk.Label(self.prefs_frame, text="1. 车站周边环境 (可多选，按住Ctrl键选择多个):").pack(anchor=tk.W, pady=(5, 2))
        
        # 创建带滚动条的环境选择列表
        env_frame = ttk.Frame(self.prefs_frame)
        env_frame.pack(anchor=tk.W, pady=(0, 10), fill=tk.X)
        
        self.env_listbox = tk.Listbox(
            env_frame,
            font=("微软雅黑", 10),
            selectmode=tk.EXTENDED,
            width=70,
            height=6
        )
        self.env_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        env_scrollbar = ttk.Scrollbar(
            env_frame,
            orient="vertical",
            command=self.env_listbox.yview
        )
        env_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.env_listbox.config(yscrollcommand=env_scrollbar.set)
        
        # 填充环境选项
        for env in self.environments:
            self.env_listbox.insert(tk.END, env)
        
        # 是否临近村庄
        ttk.Label(self.prefs_frame, text="2. 车站是否临近村庄:").pack(anchor=tk.W, pady=(5, 2))
        self.village_var = tk.StringVar(value="否")
        village_frame = ttk.Frame(self.prefs_frame)
        village_frame.pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Radiobutton(
            village_frame, 
            text="是", 
            variable=self.village_var, 
            value="是"
        ).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Radiobutton(
            village_frame, 
            text="否", 
            variable=self.village_var, 
            value="否"
        ).pack(side=tk.LEFT)
        
        # 特殊元素输入
        ttk.Label(self.prefs_frame, text="3. 希望包含的特殊元素 (可选):").pack(anchor=tk.W, pady=(5, 2))
        self.special_var = tk.StringVar()
        self.special_entry = ttk.Entry(
            self.prefs_frame, 
            textvariable=self.special_var,
            width=60
        )
        self.special_entry.pack(anchor=tk.W, pady=(0, 10))
        
        # 生成按钮
        self.generate_btn = ttk.Button(
            self.main_frame, 
            text="生成车站名称", 
            command=self.generate_names
        )
        self.generate_btn.pack(pady=(0, 15))
        
        # 创建结果显示区域
        self.results_frame = ttk.LabelFrame(self.main_frame, text="生成的车站名称", padding="10")
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        
        # 结果列表
        self.results_listbox = tk.Listbox(
            self.results_frame,
            font=("微软雅黑", 12),
            width=60,
            height=10,
            selectbackground="#a6a6a6"
        )
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        self.scrollbar = ttk.Scrollbar(
            self.results_frame,
            orient="vertical",
            command=self.results_listbox.yview
        )
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_listbox.config(yscrollcommand=self.scrollbar.set)
        
        # 底部按钮区域
        self.buttons_frame = ttk.Frame(self.main_frame)
        self.buttons_frame.pack(fill=tk.X, pady=10)
        
        # 确认按钮
        self.confirm_btn = ttk.Button(
            self.buttons_frame, 
            text="确认选择", 
            command=self.confirm_selection
        )
        self.confirm_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 重新生成按钮
        self.regenerate_btn = ttk.Button(
            self.buttons_frame, 
            text="重新生成", 
            command=self.generate_names
        )
        self.regenerate_btn.pack(side=tk.LEFT)
        
        # 初始化客户端
        self.client = OpenAI(
            api_key="sk-TC2Trp7UQHD8Mo2NBJ2lji60e7KJNwyT6OyhawKITWbzykdg",
            base_url="https://api.moonshot.cn/v1"
        )
        
        # 存储生成的名称
        self.generated_names = []
    
    def generate_names(self):
        """生成车站名称"""
        # 清空列表
        self.results_listbox.delete(0, tk.END)
        self.generated_names = []
        
        # 获取用户选择的环境
        selected_indices = self.env_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("提示", "请至少选择一个周边环境")
            return
            
        selected_environments = [self.environments[i] for i in selected_indices]
        environment_text = ", ".join(selected_environments)
        
        # 获取其他偏好
        near_village = self.village_var.get()
        special = self.special_var.get() or "无"
        
        # 构建提示词
        examples = """
        优秀示例：栖霞、落樱原、百花坡、松树坪、梧桐、绿溪岭、
        草滩、崖头、坝子、点翠湾、火石、湲水坡、萺村、汕村、
        郦庄、塘村、窦官、陈坑、同义、塬城、沚城、林湾、
        沧澄、枰阳、萝卜农场、石盘营、滨海矿区、白庙、草堂、
        分水关、雪峰关、平安渡、青桥
        """
        
        prompt = f"""
        请为Minecraft游戏中的铁路系统生成8个车站名称。
        要求如下：
        1. 符合用户设置：
           - 周边环境：{environment_text}
           - 是否临近村庄：{near_village}
           - 特殊元素：{special}
        
        2. 参考以下优秀示例的命名风格，但要有新意，避免重复：
           {examples}
        
        3. 名称要简洁易记，有新意有特色，长度适中（3-5个字为宜），3-5个字都尽量都尝试一下，适合作为游戏中的车站名称。
        4. 每个名称单独一行，不要编号和额外解释。
        5. 确保名称多样化，能体现所选环境的特点。
        """
        
        try:
            # 调用API
            completion = self.client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[
                    {"role": "system", "content": "你是一个Minecraft游戏车站名称创意生成专家，擅长结合环境特点和游戏风格创造合适的名称。"},
                    {"role": "user", "content": prompt.strip()}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            # 解析结果
            result = completion.choices[0].message.content.strip()
            self.generated_names = [name.strip() for name in result.split('\n') if name.strip()]
            
            # 过滤掉可能的编号
            self.generated_names = [name for name in self.generated_names if not (name and name[0].isdigit())]
            
            # 显示结果
            for name in self.generated_names:
                self.results_listbox.insert(tk.END, name)
                
        except Exception as e:
            messagebox.showerror("错误", f"生成名称时出错：{str(e)}")
    
    def confirm_selection(self):
        """确认选择的名称"""
        if not self.generated_names:
            messagebox.showwarning("提示", "请先生成车站名称")
            return
            
        selected_indices = self.results_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("提示", "请先选择一个车站名称")
            return
            
        selected_name = self.generated_names[selected_indices[0]]
        messagebox.showinfo("确认", f"已选择车站名称：{selected_name}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MCStationNameGenerator(root)
    root.mainloop()
    
    