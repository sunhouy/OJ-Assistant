import atexit
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import ttk, scrolledtext, messagebox

import psutil
import pystray
import requests
from PIL import Image, ImageDraw

from __init__ import version
from core.server import ServerManager
from gui.input_test import TestInputDialog
from gui.language_manager import LanguageManager
from gui.update_window import UpdateWindow
from utils.config import ConfigManager

PYSTRAY_AVAILABLE = True

from utils.extension_setup import main as run_extension_setup


class EducoderGUI:
    def __init__(self, root, username, token, machine_code=None, parent_window=None, current_version=None):
        self.remote_assist_dialog = None
        self.root = root
        self.username = username
        self.token = token
        self.machine_code = machine_code  # 保存机器码
        self.parent_window = parent_window  # 保存父窗口引用

        self.CURRENT_VERSION = version()

        # 初始化变量
        self.server_manager = None
        self.log_queue = queue.Queue()
        self.use_copy_paste = tk.BooleanVar(value=False)
        self.config_manager = ConfigManager()
        self.show_log_var = tk.BooleanVar(value=False)  # 默认不显示日志
        self.autostart_var = tk.BooleanVar(value=False)  # 开机自启选项
        self.minimize_to_tray_var = tk.BooleanVar(value=False)  # 关闭时最小化到托盘选项
        self.is_closing = False  # 标记是否正在关闭
        self.remote_assist_server = None  # 远程协助服务器

        # 托盘图标相关变量
        self.tray_icon = None
        self.tray_icon_thread = None
        self.is_minimized_to_tray = False

        # 会员状态相关变量
        self.is_member = False
        self.member_expire_date = ""
        self.member_check_thread = None
        self.member_status_checked = False
        self.member_expired = False  # 新增：标记会员是否到期

        # API基础URL
        self.BASE_URL = 'http://yhsun.cn/server/index.php'

        # 模型管理服务器基础URL
        self.MODEL_BASE_URL = 'http://yhsun.cn/server/api_manager_interface.php'
        # 管理员认证信息
        self.ADMIN_USERNAME = 'admin'
        self.ADMIN_PASSWORD = '127127sun'
        self.auth = (self.ADMIN_USERNAME, self.ADMIN_PASSWORD)

        # 模型管理相关变量
        self.selected_model = tk.StringVar(value="")  # 当前选择的模型
        self.model_list = []  # 模型列表
        self.model_info = {}  # 模型详细信息字典
        self.model_base_url = ""  # 模型API基础URL
        self.model_api_key = ""  # 模型API密钥
        self.model_name = ""  # 模型名称
        self.custom_models = []  # 用户自定义模型列表

        # 注册退出时的清理函数
        atexit.register(self.cleanup_processes)

        # 语言选择变量 - 默认C语言
        self.selected_language = tk.StringVar(value="C")

        # 语言管理器
        self.language_manager = LanguageManager(self.config_manager, log_callback=self.log)

        # 设置窗口属性
        self.root.title("Educoder助手")
        self.root.geometry("1000x750")
        self.root.resizable(True, True)

        # 设置关闭窗口的处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 加载配置
        self.load_config()

        # 设置基础UI
        self.setup_ui()

        # 确保窗口可见
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        # 先检查会员状态，然后根据状态决定是否启动服务器
        self.check_member_status_and_start()

    def load_config(self):
        """加载配置设置"""
        # 加载复制粘贴模式设置
        copy_paste_state = self.config_manager.get_setting('use_copy_paste', 'False')
        self.use_copy_paste.set(copy_paste_state.lower() == 'true')

        # 加载显示日志设置
        show_log_state = self.config_manager.get_setting('show_log', 'False')
        self.show_log_var.set(show_log_state.lower() == 'true')

        # 加载开机自启设置
        autostart_state = self.config_manager.get_setting('autostart', 'False')
        self.autostart_var.set(autostart_state.lower() == 'true')

        # 加载最小化到托盘设置
        minimize_to_tray_state = self.config_manager.get_setting('minimize_to_tray', 'False')
        self.minimize_to_tray_var.set(minimize_to_tray_state.lower() == 'true')

        # 语言管理器会自动加载自定义语言

        # 加载自定义模型
        self.load_custom_models()  # 保持原来的方法

        # 加载选中的语言
        saved_language = self.config_manager.get_setting('selected_language', 'C')
        self.selected_language.set(saved_language)

        # 加载选中的模型
        saved_model = self.config_manager.get_setting('selected_model', '')
        self.selected_model.set(saved_model)

    def save_config(self):
        """保存配置设置"""
        # 保存复制粘贴模式
        self.config_manager.set_setting('use_copy_paste', str(self.use_copy_paste.get()))

        # 保存显示日志设置
        self.config_manager.set_setting('show_log', str(self.show_log_var.get()))

        # 保存开机自启设置
        self.config_manager.set_setting('autostart', str(self.autostart_var.get()))

        # 保存最小化到托盘设置
        self.config_manager.set_setting('minimize_to_tray', str(self.minimize_to_tray_var.get()))

        # 保存选中的语言
        self.config_manager.set_setting('selected_language', self.selected_language.get())

        # 保存选中的模型
        self.config_manager.set_setting('selected_model', self.selected_model.get())

        # 保存自定义语言（在需要的时候手动调用，而不是在这里自动保存）
        # 因为自定义语言只在对话框中修改，我们在对话框中调用save_custom_languages()


    def load_custom_models_config(self):
        """从配置文件加载自定义模型"""
        try:
            custom_models_str = self.config_manager.get_setting('custom_models', '')
            if custom_models_str:
                models_data = json.loads(custom_models_str)
                for model_data in models_data:
                    model_name = model_data.get('model', '')
                    if model_name and model_name not in self.model_info:
                        self.model_info[model_name] = {
                            'model': model_name,
                            'base_url': model_data.get('base_url', ''),
                            'api_key': model_data.get('api_key', ''),
                            'is_custom': True
                        }
                        self.custom_models.append(model_name)
        except Exception as e:
            self.log(f"加载自定义模型配置时发生错误: {e}")

    def save_custom_models_config(self):
        """保存自定义模型到配置文件"""
        try:
            custom_models = []
            for model_name in self.custom_models:
                if model_name in self.model_info:
                    model_info = self.model_info[model_name]
                    if model_info.get('is_custom', False):
                        custom_models.append({
                            'model': model_name,
                            'base_url': model_info['base_url'],
                            'api_key': model_info['api_key']
                        })

            custom_models_json = json.dumps(custom_models)
            self.config_manager.set_setting('custom_models', custom_models_json)
        except Exception as e:
            self.log(f"保存自定义模型配置时发生错误: {e}")

    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")

        style = ttk.Style()
        style.configure("TLabel", foreground="#333", font=('微软雅黑', 10))
        style.configure("TButton", padding=3, relief="flat")

        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)  # 日志区域可扩展

        # 用户信息区域
        user_frame = ttk.Frame(main_frame)
        user_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        user_frame.columnconfigure(0, weight=1)

        ttk.Label(user_frame, text=f"欢迎，{self.username}（版本{self.CURRENT_VERSION}）").grid(row=0, column=0,
                                                                                                 sticky=tk.W)

        # 添加检测更新按钮、输入测试按钮、安装拓展按钮和退出登录按钮
        button_frame = ttk.Frame(user_frame)
        button_frame.grid(row=0, column=1, sticky=tk.E)

        ttk.Button(button_frame, text="输入测试", command=self.open_test_input_dialog, width=10).pack(side=tk.LEFT,
                                                                                                      padx=2)
        ttk.Button(button_frame, text="检测更新", command=self.check_update, width=10).pack(side=tk.LEFT, padx=2)

        ttk.Button(button_frame, text="启动浏览器", command=self.open_extension_setup, width=10).pack(side=tk.LEFT,
                                                                                                      padx=2)
        ttk.Button(button_frame, text="远程协助", command=self.open_remote_assist_dialog, width=10).pack(side=tk.LEFT,
                                                                                                      padx=2)
        ttk.Button(button_frame, text="退出登录", command=self.logout, width=10).pack(side=tk.LEFT, padx=2)

        # 会员状态区域
        member_status_frame = ttk.Frame(main_frame)
        member_status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # 会员状态标签 - 使用红色字体显示到期信息
        self.member_status_var = tk.StringVar(value="正在检查会员状态...")
        self.member_status_label = ttk.Label(
            member_status_frame,
            textvariable=self.member_status_var,
            font=("微软雅黑", 10)
        )
        self.member_status_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        # 开通会员按钮
        self.member_button = ttk.Button(
            member_status_frame,
            text="开通会员",
            command=self.open_member_page,
            width=10,
            state="disabled"  # 初始状态为禁用，等检查完会员状态后再启用
        )
        self.member_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 5))

        # 新增激活会员按钮
        self.activate_button = ttk.Button(
            member_status_frame,
            text="激活会员",
            command=self.open_activate_dialog,
            width=10,
            state="normal"
        )
        self.activate_button.grid(row=0, column=2, sticky=tk.E)

        # 模型选择区域
        model_frame = ttk.LabelFrame(main_frame, text="模型选择", padding="5")
        model_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        model_frame.columnconfigure(1, weight=1)

        # 第一行：模型选择
        ttk.Label(model_frame, text="选择AI模型").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        # 模型选择下拉框
        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.selected_model,
            state="readonly",
            width=30
        )
        self.model_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.model_combo.bind('<<ComboboxSelected>>', self.on_model_changed)

        # 刷新模型列表按钮
        ttk.Button(
            model_frame,
            text="刷新列表",
            command=self.load_models,
            width=10
        ).grid(row=0, column=2, sticky=tk.E)

        # 第二行：添加模型按钮
        ttk.Button(
            model_frame,
            text="添加模型",
            command=self.open_add_model_dialog,
            width=10
        ).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))

        # 第二行：删除模型按钮
        ttk.Button(
            model_frame,
            text="删除模型",
            command=self.delete_selected_model,
            width=10
        ).grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(5, 0))

        # API Key输入框
        ttk.Label(model_frame, text="API Key").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(10, 0))
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(
            model_frame,
            textvariable=self.api_key_var,
            width=50,
            show="*"  # 隐藏输入内容
        )
        self.api_key_entry.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0), padx=(0, 5))
        self.api_key_entry.bind('<KeyRelease>', self.on_api_key_changed)

        # API基础URL输入框
        ttk.Label(model_frame, text="API基础URL").grid(row=3, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.base_url_var = tk.StringVar()
        self.base_url_entry = ttk.Entry(
            model_frame,
            textvariable=self.base_url_var,
            width=50
        )
        self.base_url_entry.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0), padx=(0, 5))
        self.base_url_entry.bind('<KeyRelease>', self.on_base_url_changed)

        # 当前模型信息标签
        self.model_info_var = tk.StringVar(value="请选择模型")
        ttk.Label(
            model_frame,
            textvariable=self.model_info_var,
            font=("微软雅黑", 9)
        ).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # 配置选项区域 - 第一行
        options_frame_row1 = ttk.Frame(main_frame)
        options_frame_row1.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # 复制粘贴模式选项
        ttk.Checkbutton(
            options_frame_row1,
            text="启用复制粘贴模式（一次性输入完整代码）",
            variable=self.use_copy_paste,
            command=self.on_copy_paste_changed
        ).pack(side=tk.LEFT)

        # 语言选择和自定义语言按钮框架
        lang_frame = ttk.Frame(options_frame_row1)
        lang_frame.pack(side=tk.LEFT, padx=(20, 0))

        ttk.Label(lang_frame, text="选择编程语言").pack(side=tk.LEFT, padx=(0, 5))

        # 获取语言列表（内置语言+自定义语言）
        language_list = self.get_language_list()

        # 语言选择下拉框
        self.language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.selected_language,
            values=language_list,
            state="readonly",
            width=12
        )
        self.language_combo.pack(side=tk.LEFT, padx=(0, 5))

        # 自定义语言按钮
        ttk.Button(
            lang_frame,
            text="自定义语言",
            command=self.open_custom_language_dialog,
            width=10
        ).pack(side=tk.LEFT)

        # 绑定语言改变事件
        self.selected_language.trace('w', self.on_language_changed)

        # 配置选项区域 - 第二行
        options_frame_row2 = ttk.Frame(main_frame)
        options_frame_row2.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        # 新增日志显示复选框
        ttk.Checkbutton(
            options_frame_row2,
            text="显示日志",
            variable=self.show_log_var,
            command=self.on_show_log_changed
        ).pack(side=tk.LEFT, padx=(0, 20))

        # 新增开机自启复选框
        ttk.Checkbutton(
            options_frame_row2,
            text="开机自启",
            variable=self.autostart_var,
            command=self.on_autostart_changed
        ).pack(side=tk.LEFT, padx=(0, 20))

        # 关闭时最小化到托盘复选框
        ttk.Checkbutton(
                options_frame_row2,
                text="关闭时最小化到托盘",
                variable=self.minimize_to_tray_var,
                command=self.on_minimize_to_tray_changed
        ).pack(side=tk.LEFT)

        # 服务器控制区域
        server_frame = ttk.LabelFrame(main_frame, text="服务器控制", padding="5")
        server_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        server_frame.columnconfigure(1, weight=1)

        self.server_status_var = tk.StringVar(value="服务器状态: 等待会员状态检查...")
        ttk.Label(server_frame, textvariable=self.server_status_var).grid(row=0, column=0, sticky=tk.W)

        self.start_button = ttk.Button(server_frame, text="启动服务器", command=self.start_server, state="disabled")
        self.start_button.grid(row=0, column=1, padx=5)

        self.stop_button = ttk.Button(server_frame, text="停止服务器", command=self.stop_server, state="disabled")
        self.stop_button.grid(row=0, column=2, padx=5)

        # 连接信息
        ttk.Label(server_frame, text="使用浏览器拓展前必须启动本地服务器").grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=2
        )

        # 当前语言显示
        self.current_lang_label = ttk.Label(
            server_frame,
            text=f"当前语言: {self.selected_language.get().upper()}"
        )
        self.current_lang_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=2)

        # 状态显示
        self.status_var = tk.StringVar(value="正在检查会员状态...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=5)

        # 日志区域（默认隐藏）
        self.log_frame = ttk.LabelFrame(main_frame, text="日志输出", padding="5")
        self.log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, state='disabled', height=8)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 根据设置显示或隐藏日志区域
        if self.show_log_var.get():
            self.log_frame.grid()
        else:
            self.log_frame.grid_remove()

        # 添加超链接区域
        links_frame = ttk.Frame(main_frame)
        links_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        # 帮助中心超链接
        help_link = tk.Label(
            links_frame,
            text="帮助中心",
            fg="blue",
            cursor="hand2",
            font=("TkDefaultFont", 10)
        )
        help_link.pack(side=tk.LEFT, padx=(0, 20))
        help_link.bind("<Button-1>", lambda e: webbrowser.open("https://yhsun.cn/educoder/help"))

        # 用户协议与隐私政策超链接
        terms_link = tk.Label(
            links_frame,
            text="用户协议与隐私政策",
            fg="blue",
            cursor="hand2",
            font=("TkDefaultFont", 10)
        )
        terms_link.pack(side=tk.LEFT, padx=(0, 20))
        terms_link.bind("<Button-1>", lambda e: webbrowser.open("https://yhsun.cn/educoder/terms/"))

        # 开放源代码许可超链接
        license_link = tk.Label(
            links_frame,
            text="开放源代码许可",
            fg="blue",
            cursor="hand2",
            font=("TkDefaultFont", 10)
        )
        license_link.pack(side=tk.LEFT)
        license_link.bind("<Button-1>", lambda e: webbrowser.open("https://yhsun.cn/educoder/license"))

        # 快捷键说明超链接
        license_link = tk.Label(
            links_frame,
            text="",
            fg="blue",
            cursor="hand2",
            font=("TkDefaultFont", 10)
        )
        license_link.pack(side=tk.LEFT)
        license_link.bind("<Button-1>", lambda e: webbrowser.open("https://yhsun.cn/educoder/"))

        # 启动日志处理
        self.process_log_queue()

        # 检查当前开机自启状态
        self.check_current_autostart()

        # 记录初始语言设置
        self.log(f"初始语言设置为: {self.selected_language.get().upper()}")

        # 加载模型列表
        self.load_models()

    def get_language_list(self):
        """获取语言列表（内置+自定义），按首字母排序"""
        return self.language_manager.get_language_list()


    def open_custom_language_dialog(self):
        """打开自定义语言设置对话框"""
        self.language_manager.open_custom_language_dialog(
            self.root,
            update_callback=self.update_language_combo
        )

    def update_language_combo(self):
        """更新语言下拉框"""
        try:
            # 获取当前选择
            current_selection = self.selected_language.get()

            # 获取更新后的语言列表（已按首字母排序）
            language_list = self.get_language_list()

            # 更新下拉框的值
            self.language_combo['values'] = language_list

            # 如果当前选择不在新列表中（不区分大小写），选择第一个
            current_lower = current_selection.lower()
            if not any(lang.lower() == current_lower for lang in language_list) and language_list:
                self.selected_language.set(language_list[0])
                self.on_language_changed()

            self.log(f"语言列表已更新，当前有 {len(language_list)} 种语言")
        except Exception as e:
            self.log(f"更新语言下拉框时发生错误: {e}")

    def on_copy_paste_changed(self):
        """复制粘贴模式改变时保存配置"""
        self.save_config()

    def on_show_log_changed(self):
        """显示日志设置改变时保存配置并更新UI"""
        self.save_config()
        self.toggle_log_visibility()

    def on_autostart_changed(self):
        """开机自启设置改变时保存配置并更新系统设置"""
        self.save_config()
        self.toggle_autostart()

    def on_minimize_to_tray_changed(self):
        """最小化到托盘设置改变时保存配置"""
        self.save_config()
        self.toggle_minimize_to_tray()

    def toggle_minimize_to_tray(self):
        """切换最小化到托盘设置"""
        enabled = self.minimize_to_tray_var.get()

        if enabled:
            self.log("已启用关闭时最小化到托盘")
            self.status_var.set("已启用关闭时最小化到托盘")
        else:
            self.log("已禁用关闭时最小化到托盘")
            self.status_var.set("已禁用关闭时最小化到托盘")

    def create_tray_icon(self):
        """创建系统托盘图标"""
        if not PYSTRAY_AVAILABLE or self.tray_icon is not None:
            return

        # 创建图标
        def create_image():
            # 创建一个16x16的图标
            image = Image.new('RGB', (16, 16), color=(50, 120, 200))
            dc = ImageDraw.Draw(image)
            # 在图标中心画一个字母E
            dc.text((4, 2), "E", fill=(255, 255, 255))
            return image

        # 创建菜单项
        menu = (
            pystray.MenuItem("恢复窗口", self.restore_from_tray),
            pystray.MenuItem("退出", self.real_close)
        )

        # 创建托盘图标
        image = create_image()
        self.tray_icon = pystray.Icon("educoder_assistant", image, "Educoder助手", menu)

        # 在新线程中运行托盘图标
        self.tray_icon_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_icon_thread.start()

        self.log("已创建托盘图标")

    def restore_from_tray(self, icon=None, item=None):
        """从托盘恢复窗口"""
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

        # 在UI线程中恢复窗口
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        """恢复窗口的实际操作"""
        if self.is_minimized_to_tray:
            self.root.deiconify()  # 显示窗口
            self.root.lift()  # 将窗口置于顶层
            self.root.focus_force()  # 强制聚焦

            # 如果窗口之前是最小化的，恢复它
            if self.root.state() == 'iconic':
                self.root.state('normal')

            self.is_minimized_to_tray = False
            self.log("已从托盘恢复窗口")

    def minimize_to_tray(self):
        """最小化到系统托盘"""
        try:
            # 隐藏主窗口
            self.root.withdraw()
            self.is_minimized_to_tray = True

            # 创建托盘图标
            self.create_tray_icon()

            self.log("已最小化到托盘")
            return True
        except Exception as e:
            self.log(f"最小化到托盘失败: {e}")
            return False

    def get_models_with_index(self):
        """获取带序号的模型列表"""
        url = f'{self.MODEL_BASE_URL}?path=get_models_with_index'
        try:
            response = requests.get(url, auth=self.auth, timeout=10)
            self.log(f"获取模型列表响应: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"获取模型列表失败: {response.text}")
                return {'models': []}
        except Exception as e:
            self.log(f"获取模型列表时发生错误: {e}")
            return {'models': []}

    def load_models(self):
        """加载模型列表"""
        try:
            self.log("开始加载模型列表...")

            # 获取服务器模型列表
            response = self.get_models_with_index()
            self.log(f"模型列表响应: {response}")

            # 清空当前模型信息
            self.model_info.clear()
            self.custom_models.clear()

            if isinstance(response, dict) and 'models' in response:
                models = response['models']
                self.log(f"获取到 {len(models)} 个服务器模型")

                # 处理每个模型
                for model_data in models:
                    model_name = model_data.get('model', '未知模型')
                    base_url = model_data.get('base_url', '')
                    api_key = model_data.get('api_key', '')

                    # 保存模型信息
                    self.model_info[model_name] = {
                        'model': model_name,
                        'base_url': base_url,
                        'api_key': api_key,
                        'is_custom': False  # 服务器模型
                    }
            else:
                self.log("响应格式不符合预期，没有找到模型列表")

            # 加载自定义模型
            self.load_custom_models_config()

            # 构建模型名称列表
            model_names = list(self.model_info.keys())

            # 更新下拉框
            self.model_combo['values'] = model_names

            # 选择之前保存的模型，如果没有则选择第一个
            saved_model = self.selected_model.get()
            if saved_model and saved_model in model_names:
                self.selected_model.set(saved_model)
            elif model_names:
                # 查找第一个服务器模型（非自定义模型）
                server_models = [name for name, info in self.model_info.items() if not info.get('is_custom', False)]
                if server_models:
                    self.selected_model.set(server_models[0])
                else:
                    self.selected_model.set(model_names[0])

                # 保存选择的模型
                self.save_config()

            # 触发模型改变事件，更新当前模型信息
            self.on_model_changed()

            self.log(f"成功加载 {len(model_names)} 个模型")
            self.status_var.set(f"已加载 {len(model_names)} 个模型")
        except Exception as e:
            self.log(f"加载模型列表时发生错误: {e}")
            import traceback
            error_details = traceback.format_exc()
            self.log(f"详细错误信息:\n{error_details}")
            self.status_var.set(f"加载模型列表失败: {e}")

    def load_custom_models(self):
        """加载自定义模型"""
        try:
            # 从配置文件加载自定义模型
            config = self.config_manager.get_config()
            custom_models = config.get('custom_models', [])

            for model_data in custom_models:
                model_name = model_data.get('model', '')
                if model_name and model_name not in self.model_info:
                    self.model_info[model_name] = {
                        'model': model_name,
                        'base_url': model_data.get('base_url', ''),
                        'api_key': model_data.get('api_key', ''),
                        'is_custom': True  # 自定义模型
                    }
                    self.custom_models.append(model_name)

            self.log(f"加载了 {len(custom_models)} 个自定义模型")
        except Exception as e:
            self.log(f"加载自定义模型时发生错误: {e}")

    def save_custom_models(self):
        """保存自定义模型到配置文件"""
        try:
            # 构建自定义模型列表
            custom_models = []
            for model_name in self.custom_models:
                if model_name in self.model_info:
                    model_info = self.model_info[model_name]
                    custom_models.append({
                        'model': model_name,
                        'base_url': model_info['base_url'],
                        'api_key': model_info['api_key']
                    })

            # 更新配置
            config = self.config_manager.get_config()
            config['custom_models'] = custom_models
            self.config_manager.save_config(config)

            self.log(f"已保存 {len(custom_models)} 个自定义模型")
        except Exception as e:
            self.log(f"保存自定义模型时发生错误: {e}")

    def open_add_model_dialog(self):
        """打开添加模型对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加自定义模型")
        dialog.geometry("630x290")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()

        # 设置窗口居中
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

        # 创建主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 模型名称
        ttk.Label(main_frame, text="模型名称").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        model_name_var = tk.StringVar()
        model_name_entry = ttk.Entry(main_frame, textvariable=model_name_var, width=40)
        model_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 10), padx=(10, 0))
        model_name_entry.focus_set()

        # API基础URL
        ttk.Label(main_frame, text="API基础URL").grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        base_url_var = tk.StringVar()
        base_url_entry = ttk.Entry(main_frame, textvariable=base_url_var, width=40)
        base_url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 10), padx=(10, 0))

        # API Key
        ttk.Label(main_frame, text="API Key").grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(main_frame, textvariable=api_key_var, width=40, show="*")
        api_key_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 10), padx=(10, 0))

        # 状态标签
        status_var = tk.StringVar(value="")
        status_label = ttk.Label(main_frame, textvariable=status_var, foreground="green")
        status_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))

        def add_model():
            """添加模型"""
            model_name = model_name_var.get().strip()
            base_url = base_url_var.get().strip()
            api_key = api_key_var.get().strip()

            if not model_name:
                status_var.set("请输入模型名称！")
                return

            if not base_url:
                status_var.set("请输入API基础URL！")
                return

            if not api_key:
                status_var.set("请输入API Key！")
                return

            # 检查模型是否已存在
            if model_name in self.model_info:
                status_var.set(f"模型 '{model_name}' 已存在！")
                return

            # 添加自定义模型
            self.model_info[model_name] = {
                'model': model_name,
                'base_url': base_url,
                'api_key': api_key,
                'is_custom': True
            }
            self.custom_models.append(model_name)

            # 保存到配置文件
            self.save_custom_models_config()

            # 更新下拉框
            model_names = list(self.model_info.keys())
            self.model_combo['values'] = model_names
            self.selected_model.set(model_name)
            self.on_model_changed()

            # 保存选中的模型
            self.save_config()

            status_var.set(f"模型 '{model_name}' 添加成功！")

            # 延迟关闭对话框
            self.root.after(1000, dialog.destroy)

        def cancel():
            """取消添加"""
            dialog.destroy()

        add_button = ttk.Button(button_frame, text="添加", command=add_model, width=10)
        add_button.pack(side=tk.LEFT, padx=(0, 10))

        cancel_button = ttk.Button(button_frame, text="取消", command=cancel, width=10)
        cancel_button.pack(side=tk.LEFT)

        # 绑定回车键到添加按钮
        dialog.bind('<Return>', lambda event: add_model())

        # 窗口关闭事件
        def on_closing():
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_closing)

    def delete_selected_model(self):
        """删除选中的模型"""
        selected_model = self.selected_model.get()
        if not selected_model:
            messagebox.showwarning("警告", "请先选择一个模型！")
            return

        if selected_model not in self.model_info:
            messagebox.showwarning("警告", "选择的模型不存在！")
            return

        # 检查是否是自定义模型
        model_info = self.model_info[selected_model]
        if not model_info.get('is_custom', False):
            messagebox.showwarning("警告", "只能删除自定义模型！")
            return

        # 确认删除
        if not messagebox.askyesno("确认删除", f"确定要删除模型 '{selected_model}' 吗？"):
            return

        # 删除模型
        del self.model_info[selected_model]
        if selected_model in self.custom_models:
            self.custom_models.remove(selected_model)

        # 保存配置
        self.save_custom_models_config()

        # 更新下拉框
        model_names = list(self.model_info.keys())
        self.model_combo['values'] = model_names

        # 选择另一个模型
        if model_names:
            self.selected_model.set(model_names[0])
            self.on_model_changed()
        else:
            self.selected_model.set("")
            self.model_info_var.set("请选择模型")

        # 保存选中的模型
        self.save_config()

        self.log(f"已删除模型: {selected_model}")
        messagebox.showinfo("成功", f"已删除模型 '{selected_model}'")

    def on_model_changed(self, event=None):
        """当选择的模型改变时"""
        # 检查服务器是否正在运行
        server_was_running = self.server_manager is not None

        if server_was_running:
            self.log("检测到服务器正在运行，正在停止服务器以切换模型...")
            self.stop_server()
            # 等待服务器完全停止
            time.sleep(0.5)

        selected_model_name = self.selected_model.get()

        if selected_model_name and selected_model_name in self.model_info:
            model_data = self.model_info[selected_model_name]
            self.model_name = model_data['model']
            self.model_base_url = model_data['base_url']
            self.model_api_key = model_data['api_key']

            # 判断是否是自定义模型
            is_custom = model_data.get('is_custom', False)

            # 更新输入框内容
            self.base_url_var.set(self.model_base_url)

            # 显示API Key，但用星号隐藏
            if self.model_api_key:
                # 如果是自定义模型，显示真实API Key的前4位，其余用星号
                if is_custom and len(self.model_api_key) > 4:
                    display_key = self.model_api_key[:4] + "*" * (len(self.model_api_key) - 4)
                else:
                    # 服务器模型的API Key完全显示为星号
                    display_key = "*" * len(self.model_api_key) if self.model_api_key else ""
                self.api_key_var.set(display_key)
            else:
                self.api_key_var.set("")

            # 更新模型信息显示
            display_url = self.model_base_url[:50] + "..." if len(self.model_base_url) > 50 else self.model_base_url
            model_type = "(自定义)" if is_custom else "(服务器)"
            self.model_info_var.set(f"当前模型：{self.model_name} {model_type}")

            # 记录日志
            self.log(f"已选择模型: {self.model_name} {model_type}")
            self.log(f"API基础URL: {self.model_base_url}")

            # 更新状态
            self.status_var.set(f"已选择模型: {self.model_name} {model_type}")

            # 如果是自定义模型，无论会员状态如何都启用启动按钮
            if is_custom:
                self.start_button.config(state="normal")
            else:
                # 服务器模型需要检查会员状态
                if self.member_status_checked and self.is_member and not self.member_expired:
                    self.start_button.config(state="normal")
                else:
                    self.start_button.config(state="disabled")

            # 保存选中的模型到配置
            self.save_config()

            # 如果服务器之前是运行状态，尝试重新启动
            if server_was_running:
                self.log("模型已切换，正在尝试重新启动服务器...")
                # 延迟一点时间确保UI更新
                self.root.after(100, self._restart_server_after_model_change)
        else:
            self.model_info_var.set("请选择有效的模型")
            self.log("请选择有效的模型")

            # 如果服务器之前是运行状态，禁用启动按钮
            if server_was_running:
                self.start_button.config(state="disabled")

    def _restart_server_after_model_change(self):
        """在模型更改后重新启动服务器"""
        # 检查模型信息是否完整
        if not self.model_name or not self.model_api_key or not self.model_base_url:
            self.log("模型信息不完整，无法重新启动服务器")
            self.status_var.set("模型信息不完整，无法启动服务器")
            return

        # 检查当前模型是否是自定义模型
        current_model = self.selected_model.get()
        is_custom_model = False
        if current_model and current_model in self.model_info:
            is_custom_model = self.model_info[current_model].get('is_custom', False)

        # 如果不是自定义模型，检查会员状态
        if not is_custom_model:
            if self.member_status_checked and (not self.is_member or self.member_expired):
                self.log("会员已到期，无法重新启动服务器")
                self.status_var.set("会员已到期，无法启动服务器")
                return

        # 尝试启动服务器
        if self.start_server():
            self.log("服务器重新启动成功")
        else:
            self.log("服务器重新启动失败")

    def on_api_key_changed(self, event=None):
        """当API Key输入改变时"""
        api_key = self.api_key_var.get()
        selected_model = self.selected_model.get()
        if selected_model and selected_model in self.model_info:
            # 只更新自定义模型的API Key
            model_info = self.model_info[selected_model]
            if model_info.get('is_custom', False):
                # 如果输入不是全星号，才更新
                if not all(c == '*' for c in api_key):
                    model_info['api_key'] = api_key
                    self.model_api_key = api_key
                    self.log(f"已更新模型 {selected_model} 的API Key")

                    # 保存自定义模型
                    self.save_custom_models_config()

    def on_base_url_changed(self, event=None):
        """当API基础URL输入改变时"""
        base_url = self.base_url_var.get()
        selected_model = self.selected_model.get()
        if selected_model and selected_model in self.model_info:
            # 只更新自定义模型的base_url
            model_info = self.model_info[selected_model]
            if model_info.get('is_custom', False):
                model_info['base_url'] = base_url
                self.model_base_url = base_url
                self.log(f"已更新模型 {selected_model} 的API基础URL")

                # 更新显示
                display_url = base_url[:50] + "..." if len(base_url) > 50 else base_url
                model_type = "(自定义)" if model_info.get('is_custom', False) else "(服务器)"
                self.model_info_var.set(f"模型: {self.model_name} {model_type} | API: {display_url}")

                # 保存自定义模型
                self.save_custom_models_config()

    def check_current_autostart(self):
        """检查当前的开机自启状态"""
        try:
            # 导入main.py中的函数
            from main import check_autostart_enabled
            app_name = "Educoder助手"
            is_enabled = check_autostart_enabled(app_name)
            self.autostart_var.set(is_enabled)
            self.log(f"开机自启状态: {'已启用' if is_enabled else '未启用'}")
        except Exception as e:
            self.log(f"检查开机自启状态失败: {e}")

    def toggle_autostart(self):
        """切换开机自启状态"""
        try:
            # 导入main.py中的函数
            from main import set_autostart_windows_registry
            app_name = "Educoder助手"
            path_to_exe = os.path.abspath(sys.argv[0])
            enable = self.autostart_var.get()

            success = set_autostart_windows_registry(app_name, path_to_exe, enable)
            if success:
                status = "已启用" if enable else "已禁用"
                self.log(f"开机自启{status}")
                self.status_var.set(f"开机自启{status}")
            else:
                self.log(f"设置开机自启失败")
                self.status_var.set("设置开机自启失败")
        except Exception as e:
            self.log(f"切换开机自启状态失败: {e}")
            self.status_var.set("设置开机自启失败")

    def check_member_status_and_start(self):
        """检查会员状态并根据状态决定是否启动服务器"""
        if not self.username or not self.machine_code:
            self.member_status_var.set("无法检查会员状态：缺少用户信息或机器码")
            self.member_button.config(state="normal")  # 即使检查失败也允许用户尝试开通会员
            self.activate_button.config(state="normal")  # 激活按钮也启用
            self.start_button.config(state="disabled")
            self.status_var.set("无法检查会员状态，服务器启动已禁用")
            return

        # 在新线程中检查会员状态
        self.member_check_thread = threading.Thread(
            target=self._check_member_status_and_start_thread,
            daemon=True
        )
        self.member_check_thread.start()

    def _check_member_status_and_start_thread(self):
        """在新线程中检查会员状态并根据状态决定是否启动服务器"""
        try:
            api_base_url = self.BASE_URL
            url = f"{api_base_url}?action=check_member"
            data = {
                'username': self.username,
                'machine_code': self.machine_code
            }

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('code') == 200:
                member_data = result.get('data', {})
                self.is_member = member_data.get('is_member', False)
                self.member_expire_date = member_data.get('expire_date', '')
                self.member_status_checked = True

                # 检查会员是否到期
                if self.member_expire_date:
                    try:
                        # 假设日期格式为 YYYY-MM-DD
                        expire_date = time.strptime(self.member_expire_date, "%Y-%m-%d")
                        current_date = time.localtime()
                        self.member_expired = expire_date < current_date
                    except:
                        # 如果日期解析失败，根据is_member判断
                        self.member_expired = not self.is_member
                else:
                    self.member_expired = not self.is_member

                # 更新UI
                self.root.after(0, self._update_member_status_and_start)
            else:
                self.root.after(0, lambda: self._handle_member_check_error(result.get('message', '检查会员状态失败')))

        except requests.exceptions.Timeout:
            self.root.after(0, lambda: self._handle_member_check_error("请求超时，请检查网络连接"))
        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self._handle_member_check_error("网络连接错误，请检查网络连接"))
        except Exception as e:
            self.root.after(0, lambda: self._handle_member_check_error(f"请求失败: {str(e)}"))

    def _update_member_status_and_start(self):
        """更新会员状态UI并根据状态决定是否启动服务器"""
        if self.is_member and not self.member_expired:
            if self.member_expire_date:
                self.member_status_var.set(f"会员有效期至: {self.member_expire_date}")
                self.member_button.config(state="normal", text="续费会员")
                # 会员有效，启用启动按钮
                self.start_button.config(state="normal")
                # 自动启动服务器
                self.auto_start_server()
            else:
                self.member_status_var.set("会员用户")
                self.member_button.config(state="normal", text="续费会员")
                # 会员有效，启用启动按钮
                self.start_button.config(state="normal")
                # 自动启动服务器
                self.auto_start_server()
        else:
            # 会员已到期或不是会员
            if self.member_expire_date:
                # 会员已到期
                self.member_status_var.set(f"会员已到期: {self.member_expire_date}")
                # 设置红色字体
                self.member_status_label.config(foreground="red")
            else:
                # 不是会员用户
                self.member_status_var.set("非会员用户")

            self.member_button.config(state="normal", text="开通会员")
            # 会员到期，禁用启动按钮（自定义模型除外）
            current_model = self.selected_model.get()
            if current_model and current_model in self.model_info:
                model_info = self.model_info[current_model]
                if model_info.get('is_custom', False):
                    # 自定义模型不禁用
                    pass
                else:
                    self.start_button.config(state="disabled")
            else:
                self.start_button.config(state="disabled")

            # 显示醒目的红色提示
            self.status_var.set("会员已到期，请开通会员后启动服务器")
            # 在日志中也记录
            self.log("会员已到期，无法启动服务器。请开通会员后再试。")

        # 激活按钮始终可用
        self.activate_button.config(state="normal")

        self.log(f"会员状态检查完成: {'会员' if self.is_member and not self.member_expired else '非会员或已到期'}")

    def _handle_member_check_error(self, error_message):
        """处理会员状态检查错误"""
        self.member_status_var.set(f"会员状态检查失败: {error_message}")
        self.member_button.config(state="normal")  # 允许用户尝试开通会员
        self.activate_button.config(state="normal")  # 激活按钮也启用
        self.start_button.config(state="disabled")  # 检查失败时禁用启动按钮
        self.log(f"会员状态检查失败: {error_message}")
        self.status_var.set("会员状态检查失败，服务器启动已禁用")

    def activate_member(self, username, code):
        """
        开通会员
        :param username: 用户名
        :param code: 授权码
        :return: 响应结果
        """
        url = f'{self.BASE_URL}?action=activate_member'
        data = {
            'username': username,
            'code': code
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {
                'code': 500,
                'message': '请求失败',
                'error': str(e)
            }

    def open_member_page(self):
        """打开会员页面"""
        webbrowser.open("https://yhsun.cn/server/member")
        self.log("已打开会员页面")
        self.status_var.set("已打开会员页面")

    def open_activate_dialog(self):
        """打开激活会员对话框"""
        # 创建自定义对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("激活会员")
        dialog.geometry("450x250")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()

        # 设置窗口居中
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

        # 创建主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 用户名显示
        ttk.Label(main_frame, text=f"用户名: {self.username}", font=('TkDefaultFont', 10)).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15)
        )

        # 授权码输入
        ttk.Label(main_frame, text="授权码:").grid(row=1, column=0, sticky=tk.W, pady=(0, 15))

        code_var = tk.StringVar()
        code_entry = ttk.Entry(main_frame, textvariable=code_var, width=30)
        code_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 15), padx=(10, 0))
        code_entry.focus_set()

        # 激活成功后的提示
        self.activate_status_var = tk.StringVar(value="")
        activate_status_label = ttk.Label(main_frame, textvariable=self.activate_status_var, foreground="green")
        activate_status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        def activate():
            """执行激活操作"""
            code = code_var.get().strip()
            if not code:
                messagebox.showwarning("输入错误", "请输入授权码！")
                return

            # 禁用按钮防止重复点击
            activate_button.config(state="disabled")
            cancel_button.config(state="disabled")
            self.activate_status_var.set("正在激活中...")

            # 在新线程中执行激活请求
            def activate_thread():
                try:
                    result = self.activate_member(self.username, code)

                    def handle_result():
                        if result.get('code') == 200:
                            self.activate_status_var.set("激活成功！正在重新检查会员状态...")
                            # 激活成功，先停止服务器（如果正在运行）
                            self.stop_server()
                            # 延迟100毫秒确保服务器完全停止，然后重新检查会员状态
                            self.root.after(100, self.check_member_status_and_start)
                            # 延迟关闭对话框，让用户看到成功信息
                            self.root.after(2000, dialog.destroy)
                        else:
                            self.activate_status_var.set("激活失败，请检查授权码！")
                            # 重新启用按钮
                            activate_button.config(state="normal")
                            cancel_button.config(state="normal")

                    dialog.after(0, handle_result)
                except Exception as e:
                    def handle_error():
                        self.activate_status_var.set(f"激活过程中发生错误: {str(e)}")
                        # 重新启用按钮
                        activate_button.config(state="normal")
                        cancel_button.config(state="normal")

                    dialog.after(0, handle_error)

            threading.Thread(target=activate_thread, daemon=True).start()

        def cancel():
            """取消激活"""
            dialog.destroy()

        activate_button = ttk.Button(button_frame, text="激活", command=activate, width=10)
        activate_button.pack(side=tk.LEFT, padx=(0, 10))

        cancel_button = ttk.Button(button_frame, text="取消", command=cancel, width=10)
        cancel_button.pack(side=tk.LEFT)

        # 绑定回车键到激活按钮
        dialog.bind('<Return>', lambda event: activate())

        # 窗口关闭事件
        def on_closing():
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_closing)

    def on_language_changed(self, *args):
        """当语言选择改变时调用"""
        selected_lang = self.selected_language.get()
        self.current_lang_label.config(text=f"当前语言: {selected_lang.upper()}")
        self.log(f"语言已更改为: {selected_lang.upper()}")

        # 保存选中的语言到配置
        self.save_config()

        # 如果服务器正在运行，通知服务器语言已更改
        if self.server_manager and hasattr(self.server_manager, 'assistant'):
            try:
                self.server_manager.assistant.update_language(selected_lang)
                self.log(f"已通知服务器更新语言为: {selected_lang.upper()}")
            except Exception as e:
                self.log(f"通知服务器更新语言时出错: {e}")

    def toggle_log_visibility(self):
        """切换日志区域的显示/隐藏"""
        if self.show_log_var.get():
            self.log_frame.grid()
        else:
            self.log_frame.grid_remove()

    def open_test_input_dialog(self):
        """打开输入测试对话框"""
        TestInputDialog(self.root)

    def open_extension_setup(self):
        """打开浏览器扩展安装工具"""
        try:
                # 在新线程中运行扩展安装工具，避免阻塞主界面
                threading.Thread(
                    target=self._run_extension_setup_thread,
                    daemon=True
                ).start()

        except Exception as e:
            self.log(f"打开扩展安装工具时出错: {e}")
            messagebox.showerror("错误", f"无法打开扩展安装工具:\n{str(e)}")
            self.status_var.set("打开扩展安装工具失败")

    def _run_extension_setup_thread(self):
        """在新线程中运行扩展安装工具"""
        run_extension_setup()


    def process_log_queue(self):
        """处理日志队列"""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self._add_log_message(msg)
            except queue.Empty:
                break
        # 如果正在关闭，不再安排下一次处理
        if not self.is_closing:
            self.root.after(100, self.process_log_queue)

    def _add_log_message(self, message):
        """在日志区域添加消息"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def check_update(self):
        """检测更新 - 使用更新界面的逻辑"""
        self.log("[INFO] 开始检测更新")
        self.status_var.set("正在检测更新...")

        # 在新线程中执行版本检查
        threading.Thread(target=self._perform_version_check, daemon=True).start()

    def _perform_version_check(self):
        """执行版本检查"""
        try:
            url = f"{self.BASE_URL}?action=check_update"
            data = {
                "current_version": self.CURRENT_VERSION
            }

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            self.log(f"[INFO] 版本检查响应: {result}")

            self.root.after(0, lambda: self._handle_update_result(result))

        except requests.exceptions.Timeout:
            self.log("[ERROR] 检查更新超时")
            self.root.after(0, lambda: self._handle_update_error("检查更新超时，请检查网络连接"))
        except requests.exceptions.ConnectionError:
            self.log("[ERROR] 检查更新连接错误")
            self.root.after(0, lambda: self._handle_update_error("网络连接错误，请检查网络连接"))
        except Exception as e:
            self.log(f"[ERROR] 检查更新异常: {str(e)}")
            self.root.after(0, lambda: self._handle_update_error(f"检查更新失败: {str(e)}"))

    def _handle_update_result(self, result):
        """处理更新检查结果"""
        try:
            if result.get('code') == 200:
                data = result.get('data', {})

                # 检查是否需要强制更新
                if data.get('need_update', 0) == 1 and data.get('force_update', 0) == 1:
                    # 需要强制更新，显示更新窗口
                    self.log("[INFO] 需要强制更新")
                    self.show_update_window(data)
                    return
                elif data.get('need_update', 0) == 1:
                    # 需要普通更新，询问用户是否更新
                    self.log("[INFO] 需要普通更新")
                    self.ask_for_optional_update(data)
                else:
                    # 不需要更新
                    self.log("[INFO] 当前已是最新版本")
                    self.root.after(0, lambda: messagebox.showinfo(
                        "检测更新",
                        f"当前版本 {self.CURRENT_VERSION} 已经是最新版本！"
                    ))
                    self.status_var.set("已经是最新版本")
            else:
                # API返回错误
                error_msg = result.get('message', '未知错误')
                self.log(f"[ERROR] 更新检查API返回错误: {error_msg}")
                self.root.after(0, lambda: messagebox.showwarning(
                    "检测更新失败",
                    f"检查更新失败: {error_msg}"
                ))
                self.status_var.set("检测更新失败")

        except Exception as e:
            self.log(f"[ERROR] 处理更新结果时出错: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror(
                "检测更新失败",
                f"处理更新结果时出错: {str(e)}"
            ))
            self.status_var.set("检测更新失败")

    def _handle_update_error(self, error_msg):
        """处理更新检查错误"""
        self.log(f"[ERROR] {error_msg}")
        self.root.after(0, lambda: messagebox.showwarning(
            "检测更新失败",
            error_msg
        ))
        self.status_var.set("检测更新失败")

    def ask_for_optional_update(self, update_data):
        """询问用户是否进行普通更新"""
        response = messagebox.askyesno(
            "发现新版本",
            f"发现新版本 {update_data.get('latest_version', '')}\n"
            f"更新内容：{update_data.get('update_content', '')}\n\n"
            "是否立即更新？"
        )

        if response:
            # 用户选择更新，显示更新窗口
            self.log("[INFO] 用户选择更新")
            self.show_update_window(update_data)
        else:
            # 用户选择不更新
            self.log("[INFO] 用户选择不更新")
            self.status_var.set("已取消更新")

    def show_update_window(self, update_data):
        """显示更新窗口"""
        self.log(f"[INFO] 显示更新窗口，更新数据: {update_data}")

        # 创建更新窗口
        update_root = tk.Toplevel(self.root)
        update_root.title("软件更新")
        update_root.geometry("600x600")
        update_root.resizable(True, True)

        # 居中显示
        update_root.update_idletasks()
        x = (update_root.winfo_screenwidth() - update_root.winfo_width()) // 2
        y = (update_root.winfo_screenheight() - update_root.winfo_height()) // 2
        update_root.geometry(f"+{x}+{y}")

        # 创建更新窗口实例
        update_window = UpdateWindow(
            update_root,
            update_data,
            self.CURRENT_VERSION,
            lambda: self.on_update_completed()
        )

        # 设置关闭更新窗口时的行为
        def on_update_window_close():
            update_root.destroy()
            if update_data.get('force_update', 0) == 1:
                # 如果是强制更新，关闭主窗口
                self.status_var.set("需要强制更新，请先更新后再使用")
            else:
                # 普通更新，恢复正常状态
                self.status_var.set("更新窗口已关闭")

        update_root.protocol("WM_DELETE_WINDOW", on_update_window_close)

    def on_update_completed(self):
        """更新完成后的回调"""
        self.log("[INFO] 更新完成")
        messagebox.showinfo("更新完成", "更新完成，请重启程序以应用更新")
        self.status_var.set("更新完成，请重启程序")

    def start_server(self):
        """启动WebSocket服务器"""
        # 检查是否已选择模型
        if not self.model_name:
            self.status_var.set("请先选择AI模型")
            messagebox.showwarning("未选择模型", "请先选择一个AI模型后再启动服务器")
            self.log("启动服务器失败：未选择AI模型")
            return False

        # 检查是否已填写API密钥和基础URL
        if not self.model_api_key:
            self.status_var.set("请填写API密钥")
            messagebox.showwarning("API密钥为空", "请填写API密钥后再启动服务器")
            self.log("启动服务器失败：API密钥为空")
            return False

        if not self.model_base_url:
            self.status_var.set("请填写API基础URL")
            messagebox.showwarning("API基础URL为空", "请填写API基础URL后再启动服务器")
            self.log("启动服务器失败：API基础URL为空")
            return False

        # 检查当前模型是否是自定义模型
        current_model = self.selected_model.get()
        is_custom_model = False
        if current_model and current_model in self.model_info:
            is_custom_model = self.model_info[current_model].get('is_custom', False)

        # 如果不是自定义模型，检查会员状态
        if not is_custom_model:
            if self.member_status_checked and (not self.is_member or self.member_expired):
                # 会员到期，显示红色提示
                self.member_status_label.config(foreground="red")
                self.status_var.set("会员已到期，请开通会员后启动服务器")
                messagebox.showwarning("会员到期", "您的会员已到期，请开通会员后再启动服务器！")
                self.log("启动服务器失败：会员已到期")
                return False

            if not self.member_status_checked:
                self.status_var.set("请等待会员状态检查完成")
                messagebox.showwarning("检查中", "请等待会员状态检查完成后再启动服务器")
                return False

        # 检查服务器是否已经在运行，如果是，先关闭
        if self.server_manager is not None:
            self.log("检测到服务器已在运行，正在停止现有服务器...")
            self.stop_server()
            # 等待服务器完全停止
            time.sleep(0.1)
            self.log("现有服务器已停止，准备启动新服务器")

        try:
            # 传递模型信息给ServerManager
            self.server_manager = ServerManager(
                self,
                model_info={
                    'model': self.model_name,
                    'base_url': self.model_base_url,
                    'api_key': self.model_api_key
                }
            )
            if self.server_manager.start():
                self.start_button.config(state="disabled")
                self.stop_button.config(state="normal")
                self.server_status_var.set("服务器状态: 启动中...")
                model_type = "自定义" if is_custom_model else "服务器"
                self.status_var.set(f"服务器启动中，使用{model_type}模型: {self.model_name}")
                self.log(f"正在启动WebSocket服务器，使用{model_type}模型: {self.model_name}")
                self.log(f"API基础URL: {self.model_base_url}")
                self.log(f"当前语言设置: {self.selected_language.get().upper()}")
                return True
            else:
                self.log("启动服务器失败")
                self.status_var.set("启动服务器失败")
                return False
        except Exception as e:
            self.log(f"启动服务器时发生错误: {e}")
            self.status_var.set("启动服务器失败")
            return False

    def stop_server(self):
        """停止WebSocket服务器"""
        if self.server_manager:
            self.server_manager.stop()
            # 根据会员状态和模型类型决定是否启用启动按钮
            current_model = self.selected_model.get()
            if current_model and current_model in self.model_info:
                is_custom_model = self.model_info[current_model].get('is_custom', False)
                if is_custom_model:
                    # 自定义模型始终可以启动
                    self.start_button.config(state="normal")
                elif self.member_status_checked and self.is_member and not self.member_expired:
                    # 服务器模型需要会员有效
                    self.start_button.config(state="normal")
                else:
                    self.start_button.config(state="disabled")
            else:
                self.start_button.config(state="disabled")

            self.stop_button.config(state="disabled")
            self.server_status_var.set("服务器状态: 停止中...")
            self.status_var.set("服务器停止中...")
            self.log("正在停止服务器...")

    def log(self, message):
        """添加日志消息"""
        self.log_queue.put(message)

    def open_remote_assist_dialog(self):
        """打开远程协助管理对话框"""
        try:
            # 检查是否已存在对话框
            if hasattr(self, 'remote_assist_dialog') and self.remote_assist_dialog:
                # 如果对话框已存在，将其提到前面
                try:
                    self.remote_assist_dialog.dialog.lift()
                    self.remote_assist_dialog.dialog.focus_force()
                    return
                except:
                    # 如果对话框已关闭，重新创建
                    self.remote_assist_dialog = None

            # 导入 RemoteAssistDialog
            from gui.remote_assist import RemoteAssistDialog

            # 创建新的对话框
            self.remote_assist_dialog = RemoteAssistDialog(self.root, self, self.config_manager)

        except Exception as e:
            self.log(f"打开远程协助对话框失败: {e}")
            messagebox.showerror("错误", f"打开远程协助对话框失败: {e}")

    def logout(self):
        """用户退出登录"""
        if messagebox.askyesno("确认", "确定要退出登录吗？"):
            self.real_close()

    def cleanup_processes(self):
        """清理所有进程"""
        if hasattr(self, 'is_closing') and self.is_closing:
            return

        if self.server_manager:
            self.server_manager.stop()
            time.sleep(0.1)  # 给服务器停止一点时间

        # 清理托盘图标
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass

        # 清理可能的子进程
        try:
            # 获取当前进程ID
            current_pid = os.getpid()
            current_process = psutil.Process(current_pid)

            # 获取所有子进程
            children = current_process.children(recursive=True)

            # 终止所有子进程
            for child in children:
                try:
                    child.terminate()
                except:
                    pass

            # 等待子进程终止
            gone, still_alive = psutil.wait_procs(children, timeout=3)

            # 强制杀死仍然存活的进程
            for child in still_alive:
                try:
                    child.kill()
                except:
                    pass

        except Exception as e:
            self.log(f"清理进程时出错: {e}")

    def on_close(self):
        """关闭窗口时处理"""
        # 保存所有配置
        self.save_config()

        # 检查是否启用最小化到托盘
        if (PYSTRAY_AVAILABLE and self.minimize_to_tray_var.get() and
                not self.is_closing and not self.is_minimized_to_tray):

            # 最小化到托盘而不是关闭
            if self.minimize_to_tray():
                return  # 成功最小化到托盘，不关闭程序

        # 否则执行真正的关闭
        self.real_close()

    def real_close(self):
        """真正的关闭程序"""
        if self.is_closing:
            return

        self.is_closing = True
        self.log("正在关闭应用...")

        # 保存配置
        self.save_config()

        # 停止托盘图标
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass

        # 停止服务器
        if self.server_manager:
            self.server_manager.stop()

        # 停止所有定时器
        try:
            for after_id in self.root.tk.call('after', 'info'):
                self.root.after_cancel(after_id)
        except:
            pass

        # 清理进程
        self.cleanup_processes()
        # 关闭窗口
        self.root.destroy()
        # 强制退出程序
        os._exit(0)

    def update_status(self, message):
        """更新状态信息"""
        self.status_var.set(message)

    def update_server_status(self, message):
        """更新服务器状态"""
        self.server_status_var.set(message)

    def auto_start_server(self):
        """程序启动时自动启动服务器（仅在会员有效时）"""
        # 检查会员状态
        if not self.member_status_checked:
            self.log("等待会员状态检查完成...")
            return

        if not self.is_member or self.member_expired:
            self.log("会员已到期，不自动启动服务器")
            self.status_var.set("会员已到期，请开通会员后启动服务器")
            return

        # 检查是否已选择模型
        if not self.model_name:
            self.log("未选择AI模型，不自动启动服务器")
            self.status_var.set("请先选择AI模型")
            return

        # 检查是否已填写API信息
        if not self.model_api_key or not self.model_base_url:
            self.log("未配置完整的API信息，不自动启动服务器")
            self.status_var.set("请配置API信息")
            return

        self.log("正在自动启动服务器...")

        # 延迟100毫秒启动，确保UI完全加载
        self.root.after(100, self._auto_start_server_task)

    def _auto_start_server_task(self):
        """自动启动服务器的实际任务"""
        try:
            # 再次检查会员状态和模型选择
            if (self.member_status_checked and self.is_member and not self.member_expired
                    and self.model_name and self.model_base_url and self.model_api_key):
                # 模拟点击启动按钮
                if self.start_server():
                    self.log("服务器自动启动成功")
                else:
                    self.log("服务器自动启动失败")
            else:
                self.log("会员状态无效或未选择模型，不启动服务器")
        except Exception as e:
            self.log(f"自动启动服务器时发生错误: {e}")
            messagebox.showerror("启动错误", f"自动启动服务器时发生错误：\n{e}")