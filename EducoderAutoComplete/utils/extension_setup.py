import configparser
import os
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
import winreg
import zipfile
from io import BytesIO
from pathlib import Path
from tkinter import ttk, scrolledtext, messagebox

import requests
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService


def get_install_dir_from_registry():
    """从注册表获取安装目录"""
    try:
        # 你的AppId
        app_id = "{47A52B55-D3C4-4B88-904C-ADD610D87030}"

        # 尝试从注册表读取安装路径
        key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_id}"

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            install_location, _ = winreg.QueryValueEx(key, "InstallLocation")
            return install_location
    except WindowsError:
        # 如果注册表中没有找到，则回退到exe所在目录
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return None


class SimpleConfigManager:
    """简化版配置管理器，用于管理用户数据目录"""

    def __init__(self):
        # 获取 AppData 目录
        self.appdata_dir = self._get_appdata_dir()

        # 确保数据目录存在
        self.data_dir = os.path.join(self.appdata_dir, "BrowserExtensionTool")
        os.makedirs(self.data_dir, exist_ok=True)

        # 配置文件和驱动程序目录
        self.config_file = os.path.join(self.data_dir, 'config.ini')
        self.driver_dir = os.path.join(self.data_dir, 'edgedriver')

        self._ensure_config()

    def _get_appdata_dir(self):
        """获取 AppData 目录路径"""
        # 获取 AppData/Roaming 目录
        appdata = os.getenv('APPDATA')
        if not appdata:
            # 如果 APPDATA 环境变量不存在，使用备用路径
            home = Path.home()
            appdata = str(home / 'AppData' / 'Roaming')

        return appdata

    def _ensure_config(self):
        """确保配置文件存在"""
        if not os.path.exists(self.config_file):
            config = configparser.ConfigParser()
            config['SETTINGS'] = {
                'first_run': 'True',
                'last_edge_version': ''
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)

    def get_data_dir(self):
        """获取数据目录路径"""
        return self.data_dir

    def get_driver_dir(self):
        """获取驱动程序目录路径"""
        # 确保驱动程序目录存在
        os.makedirs(self.driver_dir, exist_ok=True)
        return self.driver_dir

    def get_last_edge_version(self):
        """获取上次记录的Edge版本"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')
                if 'SETTINGS' in config and 'last_edge_version' in config['SETTINGS']:
                    return config['SETTINGS']['last_edge_version']
        except:
            pass
        return None

    def save_edge_version(self, version):
        """保存Edge版本到配置"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')

            if 'SETTINGS' not in config:
                config['SETTINGS'] = {}

            config['SETTINGS']['last_edge_version'] = version

            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            return True
        except:
            return False


class FloatingTipWindow:
    """悬浮提示窗口 - 无系统标题栏，显示在左上角"""

    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("安装步骤")
        self.window.geometry("700x400")  # 初始大小

        # 移除系统标题栏（最小化、最大化、关闭按钮）
        self.window.overrideredirect(True)

        # 设置窗口属性
        self.window.attributes('-topmost', True)  # 始终置顶
        self.window.configure(bg='#f0f0f0')

        # 设置窗口阴影效果
        self.window.attributes('-alpha', 0.95)  # 轻微透明

        # 设置窗口位置为左上角
        self.set_top_left_position()

        # 使窗口可拖拽
        self.window.bind('<Button-1>', self.start_move)
        self.window.bind('<ButtonRelease-1>', self.stop_move)
        self.window.bind('<B1-Motion>', self.on_move)

        self.current_step = 0
        self.steps = [
            "第一步：获取Edge浏览器版本",
            "第二步：下载WebDriver",
            "第三步：启动浏览器加载扩展",
            "第四步：在桌面应用启动服务器后开始使用"
        ]

        self.setup_ui()

    def set_top_left_position(self):
        """设置窗口位置为左上角"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()

        # 获取屏幕尺寸
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # 设置左上角位置，距离左上角30像素
        x = 30
        y = 30

        # 确保窗口在屏幕内
        x = max(0, min(x, screen_width - width))
        y = max(0, min(y, screen_height - height))

        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        # 自定义标题栏
        title_frame = tk.Frame(self.window, bg='#4a86e8', height=40)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 标题
        tk.Label(title_frame, text="安装步骤", font=('微软雅黑', 12, 'bold'),
                 bg='#4a86e8', fg='white').pack(side='left', padx=10)

        # 自定义关闭按钮
        close_btn = tk.Button(title_frame, text="×", font=('微软雅黑', 14),
                              bg='#4a86e8', fg='white', bd=0,
                              command=self.hide, cursor='hand2')
        close_btn.pack(side='right', padx=10, pady=5)

        # 添加悬停效果
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg='#ff4444'))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg='#4a86e8'))

        # 内容区域
        content_frame = tk.Frame(self.window, bg='white')
        content_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # 步骤列表
        self.step_labels = []
        for i, step in enumerate(self.steps):
            frame = tk.Frame(content_frame, bg='white')
            frame.pack(fill='x', pady=5)

            # 步骤编号
            num_label = tk.Label(frame, text=str(i + 1), font=('微软雅黑', 12, 'bold'),
                                 width=3, height=1, bg='#e0e0e0')
            num_label.pack(side='left', padx=(0, 10))

            # 步骤文本
            step_label = tk.Label(frame, text=step, font=('微软雅黑', 10),
                                  bg='white', anchor='w')
            step_label.pack(side='left', fill='x', expand=True)

            self.step_labels.append((num_label, step_label))

        # 当前步骤指示器
        self.current_step_label = tk.Label(content_frame,
                                           text="请点击'开始安装'以自动安装拓展\n\n"
                                                "拓展安装成功后，如出现'关闭开发人员模式下的拓展'提示，\n"
                                                "点击右上角叉号关闭提示即可，切勿点击'关闭拓展'！",
                                           font=('微软雅黑', 10, 'bold'),
                                           bg='#e8f4f8', fg='#2c7da0', justify='left')
        self.current_step_label.pack(fill='x', pady=10, padx=5)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def on_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")

    def update_step(self, step_index):
        """更新当前步骤"""
        self.current_step = step_index

        # 重置所有步骤样式
        for i, (num_label, step_label) in enumerate(self.step_labels):
            if i < step_index:
                # 已完成步骤
                num_label.config(bg='#4CAF50', fg='white')
                step_label.config(fg='#4CAF50')
            elif i == step_index:
                # 当前步骤
                num_label.config(bg='#2196F3', fg='white')
                step_label.config(fg='#2196F3', font=('微软雅黑', 10, 'bold'))
            else:
                # 未开始步骤
                num_label.config(bg='#e0e0e0', fg='black')
                step_label.config(fg='#666')

        if step_index < len(self.steps):
            self.current_step_label.config(
                text=f"当前正在执行: {self.steps[step_index]}\n拓展安装成功后，如出现'关闭开发人员模式下的拓展'提示，\n点击右上角叉号关闭提示即可，切勿点击'关闭拓展'！")

    def show(self):
        """显示悬浮窗口"""
        # 设置窗口位置为左上角
        self.set_top_left_position()
        self.window.deiconify()

    def hide(self):
        """隐藏悬浮窗口"""
        self.window.withdraw()


class EducoderAutoCompleteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("浏览器启动工具")
        self.root.geometry("900x700")

        # 设置窗口居中
        self.center_window()

        # 设置图标和样式
        self.setup_styles()

        # 初始化配置管理器
        self.config_manager = SimpleConfigManager()

        # 创建悬浮提示窗口
        self.floating_tip = FloatingTipWindow(root)

        # 状态变量
        self.driver = None
        self.is_running = False

        # 设置UI
        self.setup_ui()

        # 初始显示悬浮提示
        self.floating_tip.show()

    def center_window(self):
        """居中显示主窗口"""
        self.root.update_idletasks()
        width = 900
        height = 700
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        style.theme_use('vista')

        # 自定义颜色
        self.bg_color = '#f5f5f5'
        self.primary_color = '#4a86e8'
        self.success_color = '#4CAF50'
        self.warning_color = '#FF9800'
        self.error_color = '#F44336'

        self.root.configure(bg=self.bg_color)

    def get_extension_dir(self):
        """获取扩展目录路径"""
        # 首先从注册表获取安装目录
        install_dir = get_install_dir_from_registry()

        if install_dir:
            self.log(f"从注册表获取的安装目录: {install_dir}", "INFO")
        else:
            self.log("使用exe所在目录作为安装目录", "INFO")
            # 如果没有安装目录，则使用exe所在目录
            if getattr(sys, 'frozen', False):
                install_dir = os.path.dirname(sys.executable)
            else:
                install_dir = os.path.dirname(os.path.abspath(__file__))

        # 扩展目录假设为安装目录下的"chrome"文件夹
        extension_dir = os.path.join(install_dir, "chrome")
        return extension_dir

    def setup_ui(self):
        """设置主界面"""
        # 标题栏
        title_frame = tk.Frame(self.root, bg=self.primary_color, height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        tk.Label(title_frame, text="浏览器启动工具",
                 font=('微软雅黑', 20, 'bold'), bg=self.primary_color,
                 fg='white').pack(pady=15)

        # 主内容区域
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill='both', expand=True, padx=20, pady=5)

        # 左侧控制面板
        control_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        control_frame.pack(side='left', fill='y', padx=(0, 20))

        # 步骤说明
        steps_frame = tk.LabelFrame(control_frame, text="提示",
                                    font=('微软雅黑', 11, 'bold'),
                                    bg='white', padx=15, pady=5)
        steps_frame.pack(fill='x', padx=15, pady=5)

        self.steps = [
            "本工具将启动新的浏览器",
            "您需重新登录头歌。",
            "若您想要将拓展安装到已有的浏览器",
            "请点击下方\"手动安装\"按钮查看教程"
        ]

        for i, step in enumerate(self.steps):
            step_frame = tk.Frame(steps_frame, bg='white')
            step_frame.pack(fill='x', pady=0)

            # 状态指示器
            status_circle = tk.Label(step_frame, text="",
                                     font=('微软雅黑', 12),
                                     bg='white', fg='#ccc')
            status_circle.pack(side='left')

            tk.Label(step_frame, text=step, font=('微软雅黑', 10),
                     bg='white', anchor='w').pack(side='left', padx=10)

        # 操作按钮
        btn_frame = tk.Frame(control_frame, bg='white')
        btn_frame.pack(fill='x', padx=15, pady=20)

        self.start_btn = tk.Button(btn_frame, text="▶ 立即启动",
                                   font=('微软雅黑', 11),
                                   bg=self.primary_color, fg='white',
                                   command=self.start_installation,
                                   padx=30, pady=10, relief='flat',
                                   cursor='hand2')
        self.start_btn.pack(fill='x', pady=5)

        self.toggle_tip_btn = tk.Button(btn_frame, text="📋 显示/隐藏安装步骤",
                                        font=('微软雅黑', 10),
                                        command=self.toggle_floating_tip,
                                        padx=20, pady=8,
                                        cursor='hand2')
        self.toggle_tip_btn.pack(fill='x', pady=5)

        self.manual_btn = tk.Button(btn_frame, text="📖 手动安装",
                                    font=('微软雅黑', 10),
                                    command=self.show_manual_guide,
                                    padx=20, pady=8,
                                    cursor='hand2')
        self.manual_btn.pack(fill='x', pady=5)

        # 右侧输出面板
        output_frame = tk.LabelFrame(main_frame, text="安装日志",
                                     font=('微软雅黑', 11, 'bold'))
        output_frame.pack(side='right', fill='both', expand=True)

        # 输出文本框
        self.output_text = scrolledtext.ScrolledText(output_frame,
                                                     height=25,
                                                     font=('微软雅黑', 10),
                                                     wrap=tk.WORD)
        self.output_text.pack(fill='both', expand=True, padx=10, pady=10)

        # 配置文本标签
        self.output_text.tag_config("INFO", foreground="black")
        self.output_text.tag_config("SUCCESS", foreground="green")
        self.output_text.tag_config("WARNING", foreground="orange")
        self.output_text.tag_config("ERROR", foreground="red")

        # 状态栏
        self.status_bar = tk.Label(self.root, text="就绪",
                                   bd=1, relief=tk.SUNKEN, anchor=tk.W,
                                   font=('微软雅黑', 9), bg='white')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def toggle_floating_tip(self):
        """切换悬浮提示窗口显示/隐藏"""
        if self.floating_tip.window.state() == 'withdrawn':
            self.floating_tip.show()
        else:
            self.floating_tip.hide()

    def log(self, message, level="INFO"):
        """输出日志到文本框"""
        self.output_text.insert(tk.END, f"[{level}] {message}\n", level)

        # 滚动到底部
        self.output_text.see(tk.END)
        self.root.update()

    def update_status(self, message):
        """更新状态栏"""
        self.status_bar.config(text=f"状态: {message}")
        self.root.update()

    def start_installation(self):
        """开始安装过程"""
        if self.is_running:
            return

        self.is_running = True
        self.start_btn.config(state='disabled')

        # 在新线程中运行安装过程
        thread = threading.Thread(target=self.run_installation)
        thread.daemon = True
        thread.start()

    def run_installation(self):
        """运行安装过程"""
        try:
            # 步骤1：获取Edge版本
            self.floating_tip.update_step(1)
            self.update_status("获取Edge浏览器信息...")
            self.log("正在获取Edge浏览器版本...", "INFO")

            edge_version = self.get_edge_version()
            if edge_version:
                self.log(f"✓ Edge浏览器版本: {edge_version}", "SUCCESS")
                # 保存Edge版本到配置
                self.config_manager.save_edge_version(edge_version)
            else:
                self.log("✗ 无法获取Edge版本，请确保Edge已安装", "ERROR")
                return

            # 步骤2：配置WebDriver
            self.floating_tip.update_step(2)
            self.update_status("配置Edge WebDriver...")
            self.log("开始配置Edge WebDriver...", "INFO")

            driver_path = self.setup_edgedriver()
            if not driver_path:
                self.log("WebDriver配置失败", "ERROR")
                return

            # 步骤3：加载扩展
            self.floating_tip.update_step(3)
            self.update_status("加载扩展程序...")
            self.log("正在加载扩展程序...", "INFO")

            # 步骤4：启动浏览器
            self.floating_tip.update_step(4)
            self.update_status("启动浏览器...")
            self.log("正在启动浏览器...", "INFO")

            self.driver = self.load_extension_in_edge(driver_path)

            if self.driver:
                self.log("✓ 浏览器启动成功！", "SUCCESS")
                self.update_status("就绪 - 浏览器已启动")
                self.show_success_dialog()
            else:
                self.log("✗ 浏览器启动失败", "ERROR")

        except Exception as e:
            self.log(f"安装过程中出现错误: {str(e)}", "ERROR")
        finally:
            self.is_running = False
            self.start_btn.config(state='normal')

    def get_edge_version(self):
        """获取Edge浏览器版本"""
        try:
            import winreg

            reg_paths = [
                r"Software\Microsoft\Edge\BLBeacon",
                r"Software\Microsoft\EdgeUpdate\Clients\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}",
                r"Software\WOW6432Node\Microsoft\EdgeUpdate\Clients\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}"
            ]

            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path)
                    version, _ = winreg.QueryValueEx(key, "version")
                    winreg.CloseKey(key)
                    if version:
                        return version
                except WindowsError:
                    continue

            # 如果通过注册表获取失败，尝试通过文件路径获取
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
            ]

            for edge_path in edge_paths:
                if os.path.exists(edge_path):
                    try:
                        # 使用powershell获取版本信息
                        cmd = f'powershell "(Get-Item \"{edge_path}\").VersionInfo.FileVersion"'
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                        if result.stdout and result.stdout.strip():
                            return result.stdout.strip()
                    except:
                        continue

            return None
        except Exception as e:
            self.log(f"获取Edge版本时出错: {e}", "ERROR")
            return None

    def setup_edgedriver(self):
        """设置Edge WebDriver"""
        # 尝试查找现有的edgedriver
        driver_path = self.find_edgedriver()

        if driver_path:
            self.log(f"✓ 找到现有的Edge WebDriver: {driver_path}", "SUCCESS")
            return driver_path

        # 下载新的
        self.log("未找到Edge WebDriver，开始自动下载...", "INFO")
        edge_version = self.get_edge_version()

        if edge_version:
            driver_path = self.download_edgedriver(edge_version)
            if driver_path:
                self.log(f"✓ Edge WebDriver下载完成: {driver_path}", "SUCCESS")
                return driver_path

        self.log("WebDriver配置失败，请手动下载", "ERROR")
        return None

    def find_edgedriver(self):
        """查找可用的Edge WebDriver"""
        driver_name = "msedgedriver.exe"

        # 1. 首先在用户数据目录中查找
        driver_dir = self.config_manager.get_driver_dir()
        path = os.path.join(driver_dir, driver_name)
        if os.path.exists(path):
            self.log(f"✓ 在用户数据目录中找到WebDriver: {path}", "SUCCESS")
            return path

        # 2. 在用户数据目录的子目录中查找
        if os.path.exists(driver_dir):
            for root, dirs, files in os.walk(driver_dir):
                if driver_name in files:
                    found_path = os.path.join(root, driver_name)
                    self.log(f"✓ 在用户数据子目录中找到WebDriver: {found_path}", "SUCCESS")
                    return found_path

        # 3. 在当前工作目录中查找（向后兼容）
        current_dir = os.getcwd()
        path = os.path.join(current_dir, driver_name)
        if os.path.exists(path):
            self.log(f"✓ 在当前目录中找到WebDriver: {path}", "SUCCESS")
            return path

        # 4. 在当前目录的edgedriver子目录中查找
        driver_dir_legacy = os.path.join(current_dir, "edgedriver")
        if os.path.exists(driver_dir_legacy):
            path = os.path.join(driver_dir_legacy, driver_name)
            if os.path.exists(path):
                self.log(f"✓ 在legacy目录中找到WebDriver: {path}", "SUCCESS")
                return path

        self.log("未找到任何可用的Edge WebDriver", "WARNING")
        return None

    def download_edgedriver(self, edge_version):
        """下载Edge WebDriver到用户数据目录"""
        try:
            self.log(f"Edge版本: {edge_version}", "INFO")

            # 检查系统架构
            import ctypes
            is_64bit = ctypes.sizeof(ctypes.c_voidp) == 8
            driver_filename = "edgedriver_win64.zip" if is_64bit else "edgedriver_win32.zip"

            # 构建下载URL
            major_version = edge_version.split('.')[0]  # 获取主版本号
            driver_url = f"https://msedgedriver.microsoft.com/{edge_version}/{driver_filename}"
            self.log(f"正在从 {driver_url} 下载...", "INFO")

            response = requests.get(driver_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            # 显示下载进度
            downloaded = 0
            block_size = 8192
            content = BytesIO()
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    content.write(chunk)
                    downloaded += len(chunk)
                    progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                    self.update_status(f"下载WebDriver: {progress:.1f}%")

            # 保存到用户数据目录
            driver_dir = self.config_manager.get_driver_dir()
            zip_path = os.path.join(driver_dir, driver_filename)

            # 保存zip文件
            with open(zip_path, 'wb') as f:
                f.write(content.getvalue())

            self.log(f"✓ 已下载WebDriver到: {zip_path}", "SUCCESS")

            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(driver_dir)

            self.log("✓ WebDriver解压完成", "SUCCESS")

            # 查找驱动程序
            driver_name = "msedgedriver.exe"
            for file in os.listdir(driver_dir):
                if file.lower() == driver_name.lower():
                    driver_path = os.path.join(driver_dir, file)
                    self.log(f"✓ WebDriver准备就绪: {driver_path}", "SUCCESS")
                    return driver_path

            # 如果不在根目录，可能在子目录中
            for root, dirs, files in os.walk(driver_dir):
                for file in files:
                    if file.lower() == driver_name.lower():
                        driver_path = os.path.join(root, file)
                        self.log(f"✓ 在子目录中找到WebDriver: {driver_path}", "SUCCESS")
                        return driver_path

            self.log("✗ 解压后未找到msedgedriver.exe", "ERROR")
            return None

        except requests.exceptions.RequestException as e:
            self.log(f"下载Edge WebDriver时网络错误: {e}", "ERROR")
        except zipfile.BadZipFile:
            self.log("下载的文件不是有效的ZIP文件", "ERROR")
        except Exception as e:
            self.log(f"下载Edge WebDriver时出错: {e}", "ERROR")

        return None

    def load_extension_in_edge(self, driver_path):
        """加载扩展并启动Edge浏览器"""
        try:
            edge_options = EdgeOptions()

            # 配置扩展路径 - 使用动态获取的扩展目录
            extension_dir = self.get_extension_dir()

            if os.path.exists(extension_dir):
                self.log(f"✓ 扩展目录存在: {extension_dir}", "SUCCESS")
                manifest_file = os.path.join(extension_dir, "manifest.json")

                if os.path.exists(manifest_file):
                    edge_options.add_argument(f'--load-extension={extension_dir}')
                    edge_options.add_argument('--enable-extensions')
                    self.log("✓ 扩展已添加到启动参数", "SUCCESS")
                else:
                    self.log("✗ 未找到manifest.json文件", "WARNING")
            else:
                self.log(f"✗ 扩展目录不存在: {extension_dir}", "WARNING")

            # 其他配置
            edge_options.add_argument("--start-maximized")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--no-sandbox")

            # 禁用自动化提示
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            edge_options.add_experimental_option('useAutomationExtension', True)
            edge_options.add_experimental_option("detach", True)

            # 启动浏览器
            self.log("正在启动Edge浏览器...", "INFO")
            service = EdgeService(driver_path)
            driver = webdriver.Edge(service=service, options=edge_options)

            self.log("✓ Edge浏览器启动成功", "SUCCESS")

            # 打开头歌网站
            driver.get('https://www.educoder.net/')

            return driver

        except Exception as e:
            self.log(f"启动浏览器时出错: {e}", "ERROR")
            return None

    def show_success_dialog(self):
        """显示成功对话框"""
        success_window = tk.Toplevel(self.root)
        success_window.title("安装成功")
        success_window.geometry("600x400")
        success_window.resizable(True, True)

        # 居中显示
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 250) // 2
        success_window.geometry(f"+{x}+{y}")

        # 成功图标
        tk.Label(success_window, text="✅", font=('Arial', 48)).pack(pady=20)

        # 成功消息
        tk.Label(success_window, text="安装成功！",
                 font=('微软雅黑', 16, 'bold')).pack(pady=10)

        tk.Label(success_window, text="拓展已成功安装，请在浏览器内打开头歌开始体验",
                 font=('微软雅黑', 10)).pack(pady=5)

        # 确定按钮
        tk.Button(success_window, text="确定",
                  command=success_window.destroy,
                  width=15, padx=10, pady=5).pack(pady=10)

    def show_manual_guide(self):
        """显示手动安装指南"""
        # 获取扩展目录
        extension_dir = self.get_extension_dir()

        # 创建一个选择浏览器对话框
        browser_dialog = tk.Toplevel(self.root)
        browser_dialog.title("选择浏览器")
        browser_dialog.geometry("400x600")
        browser_dialog.configure(bg='white')
        browser_dialog.transient(self.root)
        browser_dialog.grab_set()

        # 居中显示
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 400) // 2
        browser_dialog.geometry(f"+{x}+{y}")

        # 内容
        content_frame = tk.Frame(browser_dialog, bg='white', padx=20, pady=20)
        content_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(content_frame,
                 text="请选择您要安装扩展的浏览器：",
                 font=('微软雅黑', 12, 'bold'),
                 bg='white').pack(pady=(0, 20))

        # 显示扩展目录
        tk.Label(content_frame,
                 text=f"扩展目录：\n{extension_dir}",
                 font=('微软雅黑', 9),
                 bg='white',
                 fg='#666',
                 wraplength=350,
                 justify='left').pack(pady=(0, 20))

        # Chrome按钮
        chrome_button = tk.Button(
            content_frame,
            text="Google Chrome",
            command=lambda: self.open_chrome_install(browser_dialog, extension_dir),
            bg='#4285f4',
            fg='white',
            font=('微软雅黑', 11),
            width=20,
            height=2,
            relief='flat',
            cursor='hand2'
        )
        chrome_button.pack(pady=10)

        # 添加Chrome图标悬停效果
        chrome_button.bind("<Enter>", lambda e: chrome_button.config(bg='#3367d6'))
        chrome_button.bind("<Leave>", lambda e: chrome_button.config(bg='#4285f4'))

        # Edge按钮
        edge_button = tk.Button(
            content_frame,
            text="Microsoft Edge",
            command=lambda: self.open_edge_install(browser_dialog, extension_dir),
            bg='#0078d7',
            fg='white',
            font=('微软雅黑', 11),
            width=20,
            height=2,
            relief='flat',
            cursor='hand2'
        )
        edge_button.pack(pady=10)

        # 添加Edge图标悬停效果
        edge_button.bind("<Enter>", lambda e: edge_button.config(bg='#0063b1'))
        edge_button.bind("<Leave>", lambda e: edge_button.config(bg='#0078d7'))

        # 分隔线
        sep = tk.Frame(content_frame, height=1, bg='#e0e0e0')
        sep.pack(fill='x', pady=20)

        # 提示文本
        tk.Label(content_frame,
                 text="选择后将在浏览器中打开安装教程",
                 font=('微软雅黑', 10),
                 bg='white',
                 fg='#666').pack(pady=(0, 10))

        # 取消按钮
        cancel_button = tk.Button(
            content_frame,
            text="取消",
            command=browser_dialog.destroy,
            bg='#f5f5f5',
            fg='#333',
            font=('微软雅黑', 10),
            width=10,
            height=1,
            relief='flat',
            cursor='hand2'
        )
        cancel_button.pack(pady=5)

        cancel_button.bind("<Enter>", lambda e: cancel_button.config(bg='#e0e0e0'))
        cancel_button.bind("<Leave>", lambda e: cancel_button.config(bg='#f5f5f5'))

    def open_chrome_install(self, browser_dialog, extension_dir):
        """打开Chrome扩展安装页面"""
        browser_dialog.destroy()
        # 构建包含扩展目录参数的URL
        chrome_url = f"https://yhsun.cn/educoder/chrome.html?file={extension_dir}"
        webbrowser.open(chrome_url)
        self.show_install_instructions("Chrome")

    def open_edge_install(self, browser_dialog, extension_dir):
        """打开Edge扩展安装页面"""
        browser_dialog.destroy()
        # 构建包含扩展目录参数的URL
        edge_url = f"https://yhsun.cn/educoder/edge.html?file={extension_dir}"
        webbrowser.open(edge_url)
        self.show_install_instructions("Edge")

    def show_install_instructions(self, browser_name):
        """显示安装完成后的提示"""
        messagebox.showinfo(
            "安装提示",
            f"{browser_name}扩展安装教程页面已打开！\n"
            "请按照教程中的步骤进行操作，安装完成后可关闭此页面。",
            parent=self.root
        )


def main():
    root = tk.Tk()
    app = EducoderAutoCompleteApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()