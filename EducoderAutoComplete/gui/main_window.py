import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import os
import asyncio
import websockets
import json
import urllib.request
import urllib.error
import webbrowser
import socket
import time

from utils.config import ConfigManager
from core.server import ServerManager
from gui.input_test import TestInputDialog


class EducoderGUI:
    # 当前应用版本号
    CURRENT_VERSION = "0.1"  # 请根据实际情况更新版本号

    def __init__(self, root, username, token):
        self.root = root
        self.username = username
        self.token = token

        # 初始化变量
        self.server_manager = None
        self.log_queue = queue.Queue()
        self.use_copy_paste = tk.BooleanVar(value=False)
        self.config_manager = ConfigManager()
        self.show_log_var = tk.BooleanVar(value=False)  # 默认不显示日志

        # API Key
        self.api_key = "sk-7cc25be93a9540328aa4c104da6c4612"

        # 设置窗口属性
        self.root.title(f"Educoder助手 - 版本 {self.CURRENT_VERSION}")
        self.root.geometry("800x500")  # 增加高度以容纳日志区域
        self.root.resizable(True, True)

        # 设置关闭窗口的处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 如果首次运行，先隐藏主窗口
        if self.config_manager.should_show_welcome():
            # 立即显示首次运行提示
            self._show_first_run_dialog()
        else:
            # 不是首次运行，直接设置UI并显示
            self.setup_ui()

    def _show_first_run_dialog(self):
        """显示首次运行提示对话框"""
        print("显示首次运行对话框")  # 调试输出
        # 隐藏主窗口
        self.root.withdraw()
        print("主窗口已隐藏")  # 调试输出

        # 创建首次运行对话框
        dialog = FirstRunDialog(self.root)
        print("对话框已创建")  # 调试输出

        # 等待对话框关闭
        self.root.wait_window(dialog.dialog)
        print("对话框已关闭")  # 调试输出

        # 对话框关闭后，设置UI并显示主窗口
        self.setup_ui()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        print("主窗口已显示")  # 调试输出

        # 标记已显示过欢迎界面
        self.config_manager.set_welcome_shown()
        print("已标记欢迎界面已显示")  # 调试输出

    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)  # 日志区域可扩展

        # 用户信息区域
        user_frame = ttk.Frame(main_frame)
        user_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        user_frame.columnconfigure(0, weight=1)

        ttk.Label(user_frame, text=f"欢迎, {self.username} (版本: {self.CURRENT_VERSION})").grid(row=0, column=0,
                                                                                                 sticky=tk.W)

        # 添加检测更新按钮和输入测试按钮
        button_frame = ttk.Frame(user_frame)
        button_frame.grid(row=0, column=1, sticky=tk.E)

        ttk.Button(button_frame, text="输入测试", command=self.open_test_input_dialog, width=10).pack(side=tk.LEFT,
                                                                                                      padx=2)
        ttk.Button(button_frame, text="检测更新", command=self.check_update, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="退出登录", command=self.logout, width=10).pack(side=tk.LEFT, padx=2)

        # 复制粘贴模式选项和日志显示选项
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)

        ttk.Checkbutton(
            options_frame,
            text="允许复制粘贴（一次性输入完整代码）",
            variable=self.use_copy_paste
        ).pack(side=tk.LEFT)

        # 新增日志显示复选框
        ttk.Checkbutton(
            options_frame,
            text="显示日志",
            variable=self.show_log_var,
            command=self.toggle_log_visibility
        ).pack(side=tk.LEFT, padx=(20, 0))

        # 服务器控制区域
        server_frame = ttk.LabelFrame(main_frame, text="服务器控制", padding="5")
        server_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        server_frame.columnconfigure(1, weight=1)

        self.server_status_var = tk.StringVar(value="服务器状态: 未启动")
        ttk.Label(server_frame, textvariable=self.server_status_var).grid(row=0, column=0, sticky=tk.W)

        self.start_button = ttk.Button(server_frame, text="启动服务器", command=self.start_server)
        self.start_button.grid(row=0, column=1, padx=5)

        self.stop_button = ttk.Button(server_frame, text="停止服务器", command=self.stop_server, state="disabled")
        self.stop_button.grid(row=0, column=2, padx=5)

        # 连接信息
        ttk.Label(server_frame, text="WebSocket 地址: ws://localhost:8000").grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=2
        )

        # 状态显示
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)

        # 日志区域（默认隐藏）
        self.log_frame = ttk.LabelFrame(main_frame, text="日志输出", padding="5")
        self.log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, state='disabled', height=8)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 默认隐藏日志区域
        self.log_frame.grid_remove()

        # 启动日志处理
        self.process_log_queue()

    def toggle_log_visibility(self):
        """切换日志区域的显示/隐藏"""
        if self.show_log_var.get():
            self.log_frame.grid()
        else:
            self.log_frame.grid_remove()

    def open_test_input_dialog(self):
        """打开输入测试对话框"""
        TestInputDialog(self.root)

    def process_log_queue(self):
        """处理日志队列"""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self._add_log_message(msg)
            except queue.Empty:
                break
        self.root.after(100, self.process_log_queue)

    def _add_log_message(self, message):
        """在日志区域添加消息"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def check_update(self):
        """检测更新"""
        self.status_var.set("正在检测更新...")
        # 在新线程中执行网络请求，避免界面卡顿
        threading.Thread(target=self._check_update_thread, daemon=True).start()

    def _check_update_thread(self):
        """检测更新的线程函数"""
        try:
            # 获取最新版本号
            version_url = "http://101.200.216.53/educoder/version.txt"

            # 设置请求头，模拟浏览器请求
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/plain',
                'Connection': 'close'
            }

            req = urllib.request.Request(version_url, headers=headers)

            # 设置超时和重试机制
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        latest_version = response.read().decode('utf-8').strip()
                    break  # 成功则跳出重试循环
                except socket.timeout:
                    if attempt == 1:  # 最后一次尝试也失败
                        raise
                    time.sleep(1)  # 等待1秒后重试
                except urllib.error.HTTPError as e:
                    if e.code == 503 and attempt < 1:  # 服务暂时不可用，重试一次
                        time.sleep(2)
                        continue
                    else:
                        raise
                except ConnectionResetError:
                    if attempt == 1:  # 最后一次尝试也失败
                        raise
                    time.sleep(1)  # 等待1秒后重试

            if not latest_version:
                raise ValueError("从服务器获取的版本号为空")

            # 比较版本号
            if self._compare_version(latest_version, self.CURRENT_VERSION) > 0:
                # 有新版本，获取更新内容和下载地址
                content_url = "http://101.200.216.53/educoder/content.txt"
                download_url = "http://101.200.216.53/educoder/download.txt"

                # 获取更新内容
                req = urllib.request.Request(content_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    update_content = response.read().decode('utf-8').strip()

                # 获取下载地址
                req = urllib.request.Request(download_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    download_link = response.read().decode('utf-8').strip()

                # 在GUI线程中显示更新信息
                self.root.after(0, lambda: self._show_update_info(
                    latest_version, update_content, download_link
                ))
            else:
                # 已经是最新版本
                self.root.after(0, lambda: messagebox.showinfo(
                    "检测更新",
                    f"当前版本 {self.CURRENT_VERSION} 已经是最新版本！"
                ))
                self.root.after(0, lambda: self.status_var.set("已经是最新版本"))

        except urllib.error.URLError as e:
            error_msg = str(e.reason) if hasattr(e, 'reason') else str(e)
            self.root.after(0, lambda: messagebox.showwarning(
                "检测更新失败",
                f"无法连接到更新服务器，请检查网络连接。\n错误代码: {getattr(e, 'code', 'N/A')}\n错误详情: {error_msg}"
            ))
            self.root.after(0, lambda: self.status_var.set("检测更新失败"))
        except socket.timeout:
            self.root.after(0, lambda: messagebox.showwarning(
                "检测更新失败",
                "连接服务器超时，请稍后重试。"
            ))
            self.root.after(0, lambda: self.status_var.set("检测更新失败"))
        except ConnectionResetError:
            self.root.after(0, lambda: messagebox.showwarning(
                "检测更新失败",
                "连接被服务器重置，请稍后重试。"
            ))
            self.root.after(0, lambda: self.status_var.set("检测更新失败"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "检测更新失败",
                f"检测更新时发生错误：{str(e)}"
            ))
            self.root.after(0, lambda: self.status_var.set("检测更新失败"))

    def _compare_version(self, version1, version2):
        """比较版本号大小

        Args:
            version1: 版本号1 (如 "1.2.3")
            version2: 版本号2 (如 "1.2.4")

        Returns:
            >0: version1 > version2
            =0: version1 = version2
            <0: version1 < version2
        """

        def parse_version(v):
            parts = []
            for part in v.split('.'):
                try:
                    parts.append(int(part))
                except ValueError:
                    # 如果不能转换为整数，则按字符串处理
                    parts.append(part)
            return parts

        v1_parts = parse_version(version1)
        v2_parts = parse_version(version2)

        # 补齐位数
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))

        # 逐级比较
        for v1, v2 in zip(v1_parts, v2_parts):
            if isinstance(v1, int) and isinstance(v2, int):
                if v1 != v2:
                    return v1 - v2
            else:
                # 如果有一个不是整数，都转为字符串比较
                if str(v1) != str(v2):
                    return 1 if str(v1) > str(v2) else -1

        return 0

    def _show_update_info(self, latest_version, update_content, download_link):
        """显示更新信息对话框"""
        # 检查是否已经有其他对话框在显示
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and widget.winfo_viewable():
                # 如果有其他对话框，先将其提升到最前面
                widget.lift()
                return

        # 创建自定义对话框
        dialog = tk.Toplevel(self.root)
        dialog.title(f"发现新版本 {latest_version}")
        dialog.geometry("600x400")
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
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 版本信息
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(version_frame, text=f"发现新版本: {latest_version}",
                  font=('TkDefaultFont', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Label(version_frame, text=f"当前版本: {self.CURRENT_VERSION}").pack(side=tk.RIGHT)

        # 更新内容标题
        ttk.Label(main_frame, text="更新内容:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)

        # 更新内容文本框（可滚动）
        content_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=10)
        content_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        content_text.insert('1.0', update_content or "暂无更新内容描述")
        content_text.config(state='disabled')

        # 下载地址
        download_frame = ttk.Frame(main_frame)
        download_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(download_frame, text="下载地址:",
                  font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT, anchor=tk.W)

        # 下载地址文本框（可复制）
        download_var = tk.StringVar(value=download_link or "暂无下载地址")
        download_entry = ttk.Entry(download_frame, textvariable=download_var, width=50)
        download_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))

        # 复制按钮
        def copy_download_link():
            if download_link:
                self.root.clipboard_clear()
                self.root.clipboard_append(download_link)
                self.root.update()
                messagebox.showinfo("复制成功", "下载地址已复制到剪贴板")
            else:
                messagebox.showwarning("复制失败", "没有可复制的下载地址")

        ttk.Button(download_frame, text="复制", command=copy_download_link, width=8).pack(side=tk.RIGHT)

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # 打开下载页面按钮
        def open_download_page():
            if download_link and download_link.startswith(('http://', 'https://')):
                webbrowser.open(download_link)
            dialog.destroy()

        if download_link and download_link.startswith(('http://', 'https://')):
            ttk.Button(button_frame, text="打开下载页面", command=open_download_page, width=15).pack(side=tk.LEFT,
                                                                                                     padx=(0, 10))

        # 稍后提醒按钮
        ttk.Button(button_frame, text="关闭", command=dialog.destroy, width=10).pack(side=tk.RIGHT)

        # 关闭按钮
        def on_dialog_close():
            self.status_var.set(f"有新版本 {latest_version} 可用")
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

        # 更新主界面状态
        self.status_var.set(f"有新版本 {latest_version} 可用")

    def start_server(self):
        """启动WebSocket服务器"""
        # 使用硬编码的API Key
        self.server_manager = ServerManager(self)
        if self.server_manager.start():
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.server_status_var.set("服务器状态: 启动中...")
            self.status_var.set("服务器启动中...")
            self.log("正在启动WebSocket服务器...")

    def stop_server(self):
        """停止WebSocket服务器"""
        if self.server_manager:
            self.server_manager.stop()
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.server_status_var.set("服务器状态: 停止中...")
            self.status_var.set("服务器停止中...")
            self.log("正在停止服务器...")

    def log(self, message):
        """添加日志消息"""
        self.log_queue.put(message)

    def logout(self):
        """用户退出登录"""
        if messagebox.askyesno("确认", "确定要退出登录吗？"):
            # 发送登出请求
            threading.Thread(target=self._perform_logout, daemon=True).start()

            # 关闭主窗口
            self.root.destroy()

    def _perform_logout(self):
        """执行登出操作"""
        try:
            # 使用asyncio在单独的事件循环中运行异步代码
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def logout():
                async with websockets.connect("ws://localhost:8001") as websocket:
                    await websocket.send(json.dumps({
                        'action': 'logout',
                        'username': self.username,
                        'token': self.token
                    }))

            loop.run_until_complete(logout())
            loop.close()
        except:
            pass  # 忽略登出错误

    def on_close(self):
        """关闭窗口时的处理"""
        # 停止服务器
        if self.server_manager:
            self.server_manager.stop()

        # 发送登出请求
        threading.Thread(target=self._perform_logout, daemon=True).start()

        # 关闭窗口
        self.root.destroy()

    def update_status(self, message):
        """更新状态信息"""
        self.status_var.set(message)

    def update_server_status(self, message):
        """更新服务器状态"""
        self.server_status_var.set(message)


class FirstRunDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("欢迎使用 Educoder 助手")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

        frame = ttk.Frame(self.dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="欢迎使用 Educoder 助手!", font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(frame, text="这是一个专为 Educoder 平台设计的辅助工具", wraplength=350).pack(pady=5)
        ttk.Label(frame, text="点击确定开始使用", wraplength=350).pack(pady=5)

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=15)

        ttk.Button(button_frame, text="确定", command=self.dialog.destroy, width=10).pack()
