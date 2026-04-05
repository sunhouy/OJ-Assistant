import asyncio
import json
import logging
import platform
import threading
import time
import tkinter as tk
import uuid
import webbrowser
from datetime import datetime
from tkinter import ttk, scrolledtext
from typing import Optional, Set, List, Callable

import keyboard
import pyautogui
import pyperclip
import qrcode
import websockets
from PIL import ImageTk

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RemoteAssistDialog:
    """远程协助对话框（与主界面集成的包装类）"""

    def __init__(self, parent, main_window, config_manager):
        """
        初始化远程协助对话框

        Args:
            parent: 父窗口
            main_window: 主窗口对象
            config_manager: 配置管理器
        """
        self.parent = parent
        self.main_window = main_window
        self.config_manager = config_manager

        # 创建聊天客户端实例
        self.client = PythonChatClient(
            server_host='101.200.216.53',
            server_port=8765,
            client_name=f"PythonClient-{uuid.uuid4().hex[:8]}"
        )

        # 自动输入相关变量
        self.auto_input_enabled = tk.BooleanVar(value=True)  # 默认启用自动输入
        self.auto_input_delay = tk.DoubleVar(value=0)  # 等待时间
        self.auto_input_interval = tk.DoubleVar(value=0.001)  # 字符间隔
        self.auto_input_special = tk.BooleanVar(value=True)  # 特殊字符处理
        self.auto_input_running = False
        self.stop_requested = False  # ESC键停止标志

        # 截图相关变量
        self.screenshot_enabled = tk.BooleanVar(value=True)  # 默认启用截图快捷键
        # 注册快捷键
        try:
            keyboard.add_hotkey('ctrl+alt+z', self.on_screenshot_shortcut)
            self.screenshot_hotkey_registered = True
        except Exception as e:
            self.screenshot_enabled = tk.BooleanVar(value=False)

        self.screenshot_hotkey_registered = False  # 热键是否已注册

        # 创建对话框窗口

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("远程协助")
        self.dialog.geometry("980x920")
        self.dialog.resizable(True, True)  # 允许调整大小
        self.dialog.minsize(840, 700)  # 设置最小尺寸

        if platform.system() == "Windows":
            try:
                self.dialog.attributes('-toolwindow', False)
            except Exception:
                pass

        # self.dialog.transient(parent)
        # self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 设置客户端回调函数
        self.client.set_callbacks(
            status_callback=self._update_status,
            otp_callback=self._update_otp,
            message_callback=self._add_message,
            paired_callback=self._on_paired,
            error_callback=self._show_error,
            remote_message_callback=self._add_remote_message
        )

        # 设置UI
        self.setup_ui()

        # 根据内容和屏幕大小重新定尺寸
        self.fit_dialog_to_content()

        # 启动客户端
        self.start_client()

        # 通知主窗口
        if hasattr(main_window, 'remote_assist_dialog'):
            main_window.remote_assist_dialog = self

    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        content_host = ttk.Frame(self.dialog)
        content_host.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(content_host, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(content_host, orient="vertical", command=canvas.yview)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        main_frame = ttk.Frame(canvas, padding="16")
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def update_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_canvas_width(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        def on_mousewheel(event):
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta, "units")

        main_frame.bind("<Configure>", update_scrollregion)
        canvas.bind("<Configure>", sync_canvas_width)
        canvas.bind("<MouseWheel>", on_mousewheel)
        canvas.bind("<Button-4>", on_mousewheel)
        canvas.bind("<Button-5>", on_mousewheel)

        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_var = tk.StringVar(value="正在启动客户端...")
        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT)

        # OTP显示区域
        otp_frame = ttk.LabelFrame(main_frame, text="一次性密码 (OTP)", padding="10")
        otp_frame.pack(fill=tk.X, pady=(0, 10))

        self.otp_var = tk.StringVar(value="等待生成...")
        ttk.Label(
            otp_frame,
            textvariable=self.otp_var,
            font=("Arial", 24, "bold"),
            foreground="blue"
        ).pack()

        # 二维码和链接区域
        qr_frame = ttk.LabelFrame(main_frame, text="快速连接", padding="10")
        qr_frame.pack(fill=tk.X, pady=(0, 10))

        # 创建框架用于水平排列二维码和链接
        qr_link_frame = ttk.Frame(qr_frame)
        qr_link_frame.pack(fill=tk.X, expand=True)

        # 二维码显示区域（左侧）
        qr_display_frame = ttk.Frame(qr_link_frame)
        qr_display_frame.pack(side=tk.LEFT, padx=(0, 20))

        self.qr_label = ttk.Label(qr_display_frame, text="等待生成二维码...")
        self.qr_label.pack()

        # 链接区域（右侧）
        link_frame = ttk.Frame(qr_link_frame)
        link_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(link_frame, text="快速访问链接:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.link_var = tk.StringVar(value="链接将在OTP生成后创建")
        link_entry = ttk.Entry(
            link_frame,
            textvariable=self.link_var,
            font=("Arial", 9),
            state="readonly"
        )
        link_entry.pack(fill=tk.X, pady=(0, 10))

        # 链接操作按钮
        button_frame = ttk.Frame(link_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            button_frame,
            text="复制链接",
            command=self.copy_link,
            width=12
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            button_frame,
            text="打开链接",
            command=self.open_link,
            width=12
        ).pack(side=tk.LEFT)

        # 聊天区域
        chat_frame = ttk.LabelFrame(main_frame, text="远程协助", padding="10")
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 消息显示区域
        msg_display_frame = ttk.Frame(chat_frame)
        msg_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.message_text = scrolledtext.ScrolledText(
            msg_display_frame,
            wrap=tk.WORD,
            height=8,
            state=tk.DISABLED
        )
        self.message_text.pack(fill=tk.BOTH, expand=True)

        # 消息输入区域
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X)

        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(
            input_frame,
            textvariable=self.input_var
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind('<Return>', self.send_message)

        ttk.Button(
            input_frame,
            text="发送",
            command=self.send_message,
            width=8
        ).pack(side=tk.LEFT)

        # 截图设置
        screenshot_frame = ttk.LabelFrame(main_frame, text="截图功能", padding="10")
        screenshot_frame.pack(fill=tk.X, pady=(0, 10))

        # 启用截图快捷键
        ttk.Checkbutton(
            screenshot_frame,
            text="启用截图快捷键 (ctrl+alt+z)",
            variable=self.screenshot_enabled,
            command=self.on_screenshot_changed
        ).pack(anchor=tk.W, pady=(0, 5))

        # 添加截图说明
        ttk.Label(
            screenshot_frame,
            text="启用后，按下ctrl+alt+z将截取屏幕并上传到服务器",
            font=("Arial", 9)
        ).pack(anchor=tk.W, pady=(0, 5))

        # 自动输入设置
        auto_frame = ttk.LabelFrame(main_frame, text="自动输入设置", padding="10")
        auto_frame.pack(fill=tk.X, pady=(0, 10))

        # 启用自动输入
        ttk.Checkbutton(
            auto_frame,
            text="启用自动输入 (按ESC键停止)",
            variable=self.auto_input_enabled,
            command=self.on_auto_input_changed
        ).pack(anchor=tk.W, pady=(0, 5))

        # 参数设置
        params_frame = ttk.Frame(auto_frame)
        params_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(params_frame, text="等待时间(秒)").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Spinbox(
            params_frame,
            from_=0.1,
            to=10.0,
            increment=0.1,
            textvariable=self.auto_input_delay,
            width=8
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(params_frame, text="字符间隔(秒)").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Spinbox(
            params_frame,
            from_=0.01,
            to=1.0,
            increment=0.01,
            textvariable=self.auto_input_interval,
            width=8
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(
            params_frame,
            text="特殊字符处理",
            variable=self.auto_input_special
        ).pack(side=tk.LEFT)

    def fit_dialog_to_content(self, min_width=840, min_height=700, max_width_ratio=0.98, max_height_ratio=0.96):
        """根据内容和屏幕大小调整窗口大小，确保界面完整可见。"""
        self.dialog.update_idletasks()

        width = max(min_width, self.dialog.winfo_reqwidth())
        height = max(min_height, self.dialog.winfo_reqheight())

        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        width = min(width, int(screen_width * max_width_ratio))
        height = min(height, int(screen_height * max_height_ratio))

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def start_client(self):
        """启动客户端"""
        self._update_status("正在连接服务器...")
        threading.Thread(
            target=self._run_client,
            daemon=True
        ).start()

    def _run_client(self):
        """在新线程中运行客户端"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.client.run_with_loop())
        except Exception as e:
            self._show_error(f"客户端运行错误: {e}")
        finally:
            loop.close()

    def _update_status(self, status: str):
        """更新状态"""

        def update():
            self.status_var.set(status)
            # self._add_message(f"状态: {status}", is_info=True)

        self.dialog.after(0, update)

    def _update_otp(self, otp: str, expires_in: int):
        """更新OTP显示，并生成二维码和链接"""

        def update():
            self.otp_var.set(otp)
            self._add_message(f"OTP已生成: {otp} (有效期: {expires_in}秒)", is_info=True)

            # 生成二维码
            self.generate_qr_code(otp)

            # 生成并显示链接
            link = self.generate_link(otp)
            self.link_var.set(link)

        self.dialog.after(0, update)

    def generate_qr_code(self, otp: str):
        """生成二维码"""
        try:
            # 生成链接
            link = self.generate_link(otp)

            # 生成二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=6,
                border=2,
            )
            qr.add_data(link)
            qr.make(fit=True)

            # 创建二维码图片
            img = qr.make_image(fill_color="black", back_color="white")

            # 转换为PhotoImage
            img_tk = ImageTk.PhotoImage(img)

            # 更新标签显示二维码
            self.qr_label.config(image=img_tk)
            self.qr_label.image = img_tk  # 保持引用

        except Exception as e:
            self.qr_label.config(text=f"二维码生成失败: {e}")
            self._add_message(f"二维码生成失败: {e}", is_info=True)

    def generate_link(self, otp: str) -> str:
        """生成访问链接"""
        # 使用客户端配置的服务器地址，或者默认的
        server_host = self.client.server_host

        # 移除http://或https://前缀（如果有）
        if server_host.startswith('http://'):
            server_host = server_host[7:]
        elif server_host.startswith('https://'):
            server_host = server_host[8:]

        # 创建链接
        link = f"http://{server_host}:8080?otp={otp}"
        return link

    def copy_link(self):
        """复制链接到剪贴板"""
        link = self.link_var.get()
        if link and link != "链接将在OTP生成后创建":
            try:
                pyperclip.copy(link)
                self._add_message("链接已复制到剪贴板", is_info=True)
            except Exception as e:
                self._show_error(f"复制失败: {e}")

    def open_link(self):
        """在浏览器中打开链接"""
        link = self.link_var.get()
        if link and link != "链接将在OTP生成后创建":
            try:
                webbrowser.open(link)
                self._add_message("正在浏览器中打开链接...", is_info=True)
            except Exception as e:
                self._show_error(f"打开链接失败: {e}")

    def send_message(self, event=None):
        """发送消息"""
        message = self.input_var.get().strip()
        if not message:
            return

        # 通过客户端发送消息，确保线程安全
        if self.client:
            self.client.send_message_threadsafe(message)
            self._add_message(f"你: {message}", is_own=True)
            self.input_var.set("")

    def _add_message(self, message: str, is_own=False, is_info=False):
        """添加聊天消息到显示区域"""

        def add():
            self.message_text.config(state=tk.NORMAL)

            # 添加时间戳
            timestamp = datetime.now().strftime("%H:%M:%S")

            # 设置消息颜色
            if is_info:
                tag = "info"
                prefix = f"[{timestamp}] 系统: "
            elif is_own:
                tag = "own"
                prefix = f"[{timestamp}] 你: "
            else:
                tag = "other"
                prefix = f"[{timestamp}] 网页用户: "

            self.message_text.insert(tk.END, prefix, tag)
            self.message_text.insert(tk.END, message + "\n")
            self.message_text.see(tk.END)
            self.message_text.config(state=tk.DISABLED)

            # 配置标签
            self.message_text.tag_config("info", foreground="blue")
            self.message_text.tag_config("own", foreground="green")
            self.message_text.tag_config("other", foreground="red")

            # 如果不是自己的消息，不是系统消息，且启用了自动输入，则自动输入
            # 只对来自网页用户的聊天消息进行自动输入
            if not is_own and not is_info and self.auto_input_enabled.get():
                # 从消息中提取纯文本内容（去掉时间戳和发送者信息）
                if ": " in message:
                    pure_text = message.split(": ", 1)[1] if ": " in message else message
                else:
                    pure_text = message
                self._auto_input_message(pure_text)

        self.dialog.after(0, add)

    def _add_remote_message(self, message: str):
        """添加远程协助消息到显示区域（不自动输入）"""

        def add():
            self.message_text.config(state=tk.NORMAL)

            # 添加时间戳
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = f"[{timestamp}] 远程协助: "

            self.message_text.insert(tk.END, prefix, "remote")
            self.message_text.insert(tk.END, message + "\n")
            self.message_text.see(tk.END)
            self.message_text.config(state=tk.DISABLED)

            # 配置远程消息标签
            self.message_text.tag_config("remote", foreground="purple")

        self.dialog.after(0, add)

    def _auto_input_message(self, message: str):
        """自动输入消息"""
        if self.auto_input_running:
            return

        threading.Thread(
            target=self._run_auto_input,
            args=(message,),
            daemon=True
        ).start()

    def _run_auto_input(self, message: str):
        """执行自动输入"""
        self.auto_input_running = True
        self.stop_requested = False

        esc_hook = None
        try:
            esc_hook = keyboard.on_press_key('esc', self._stop_auto_input_handler)
        except Exception as e:
            self.dialog.after(0, lambda: self._add_message(
                f"ESC全局监听不可用，将继续输入但无法ESC停止: {e}", is_info=True
            ))

        def safe_write(char):
            try:
                keyboard.write(char)
            except Exception:
                pyautogui.write(char, interval=0)

        def safe_press(key):
            try:
                keyboard.press_and_release(key)
                return
            except Exception:
                pass
            pyautogui.press(key)

        try:
            # 等待用户切换到目标窗口
            delay = self.auto_input_delay.get()
            if delay > 0:
                for i in range(int(delay * 10)):
                    if self.stop_requested:
                        break
                    time.sleep(0.1)

            # 输入消息（只输入纯文本，不包含时间信息）
            interval = self.auto_input_interval.get()
            special_chars = self.auto_input_special.get()

            if special_chars:
                # 处理特殊字符
                for char in message:
                    if self.stop_requested:
                        break

                    try:
                        if char == '\n':
                            safe_press('enter')
                        elif char == '\t':
                            safe_press('tab')
                        elif char == ' ':
                            safe_press('space')
                        elif len(char) == 1 and ord(char) < 128:
                            safe_write(char)
                        else:
                            safe_write(char)

                        time.sleep(interval)
                    except Exception as e:
                        self.dialog.after(0, lambda: self._add_message(
                            f"输入字符出错: {repr(char)} - {str(e)}", is_info=True
                        ))
                        time.sleep(interval)
            else:
                # 简单输入
                for char in message:
                    if self.stop_requested:
                        break

                    try:
                        safe_write(char)
                        time.sleep(interval)
                    except Exception as e:
                        self.dialog.after(0, lambda: self._add_message(
                            f"输入字符出错: {char} - {str(e)}", is_info=True
                        ))
                        time.sleep(interval)

            if self.stop_requested:
                self.dialog.after(0, lambda: self._add_message("自动输入已停止", is_info=True))
            else:
                self.dialog.after(0, lambda: self._add_message("自动输入完成", is_info=True))

        except Exception as e:
            self.dialog.after(0, lambda: self._add_message(
                f"自动输入出错: {str(e)}", is_info=True
            ))
        finally:
            self.auto_input_running = False
            # 仅移除本次自动输入注册的ESC监听，避免影响其他热键
            if esc_hook is not None:
                try:
                    keyboard.unhook(esc_hook)
                except Exception:
                    pass

    def _stop_auto_input_handler(self, event):
        """ESC键处理函数"""
        self.stop_requested = True

    def on_screenshot_changed(self):
        """截图设置改变"""
        enabled = self.screenshot_enabled.get()

        if enabled:
            # 注册快捷键
            try:
                keyboard.add_hotkey('ctrl+alt+z', self.on_screenshot_shortcut)
                self.screenshot_hotkey_registered = True
                self._add_message("截图快捷键已启用: ctrl+alt+z", is_info=True)
            except Exception as e:
                self._show_error(f"注册截图快捷键失败: {e}")
                self.screenshot_enabled.set(False)
        else:
            # 注销快捷键
            try:
                if self.screenshot_hotkey_registered:
                    keyboard.remove_hotkey('ctrl+alt+z')
                    self.screenshot_hotkey_registered = False
                self._add_message("截图快捷键已禁用", is_info=True)
            except Exception as e:
                self._show_error(f"注销截图快捷键失败: {e}")

    def on_screenshot_shortcut(self):
        """截图快捷键被按下时的处理函数"""
        if not self.screenshot_enabled.get():
            return

        # 在新线程中处理截图，避免阻塞UI
        threading.Thread(
            target=self._take_and_send_screenshot,
            daemon=True
        ).start()

    def _take_and_send_screenshot(self):
        """截图并发送到服务器"""
        try:
            # 在主线程中显示消息
            self.dialog.after(0, lambda: self._add_message("正在截取屏幕...", is_info=True))

            # 截图
            screenshot = pyautogui.screenshot()

            # 生成唯一文件名
            import os
            import tempfile
            temp_dir = tempfile.gettempdir()
            filename = f'screenshot_{uuid.uuid4().hex[:8]}_{int(time.time())}.png'
            screenshot_path = os.path.join(temp_dir, filename)

            # 保存截图
            screenshot.save(screenshot_path)

            # 在主线程中显示消息
            self.dialog.after(0, lambda: self._add_message(f"截图已保存到临时文件: {filename}", is_info=True))

            # 上传截图到服务器
            self._upload_screenshot(screenshot_path)

        except Exception as e:
            error_msg = f"截图失败: {str(e)}"
            self.dialog.after(0, lambda: self._show_error(error_msg))

    def _upload_screenshot(self, screenshot_path):
        """上传截图到服务器"""
        try:
            # 从配置管理器获取用户会话
            user_session = self.config_manager.load_user_session()
            if not user_session:
                self.dialog.after(0, lambda: self._show_error("未检测到用户登录信息，请先登录"))
                return

            username = user_session.get('username')
            machine_code = user_session.get('machine_code')
            token = user_session.get('token')

            if not username or not machine_code:
                self.dialog.after(0, lambda: self._show_error("用户信息不完整，请重新登录"))
                return

            # 服务器API地址
            base_url = "http://yhsun.cn/server/index.php"
            url = f'{base_url}?action=upload_screenshot'

            # 读取截图文件
            import os
            if not os.path.exists(screenshot_path):
                self.dialog.after(0, lambda: self._show_error("截图文件不存在"))
                return

            with open(screenshot_path, 'rb') as file:
                file_content = file.read()

            # 准备上传数据
            import requests
            files = {
                'screenshot': (os.path.basename(screenshot_path), file_content, 'application/octet-stream')
            }

            data = {
                'username': username,
                'machine_code': machine_code,
                'token': token
            }

            # 发送上传请求
            self.dialog.after(0, lambda: self._add_message("正在上传截图到服务器...", is_info=True))

            response = requests.post(url, files=files, data=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    file_url = result['data']['file_url']

                    # 在主线程中显示成功消息
                    self.dialog.after(0, lambda: self._add_message(
                        f"截图上传成功！文件URL: {file_url}", is_info=True
                    ))

                    # 向服务器发送图片URL消息
                    self._send_image_url_to_server(file_url)

                    # 删除临时文件
                    try:
                        os.remove(screenshot_path)
                    except:
                        pass
                else:
                    error_msg = result.get('message', '未知错误')
                    self.dialog.after(0, lambda: self._show_error(f"截图上传失败: {error_msg}"))
            else:
                self.dialog.after(0, lambda: self._show_error(f"上传请求失败，状态码: {response.status_code}"))

        except requests.exceptions.Timeout:
            self.dialog.after(0, lambda: self._show_error("上传请求超时，请检查网络连接"))
        except requests.exceptions.ConnectionError:
            self.dialog.after(0, lambda: self._show_error("网络连接错误，请检查网络连接"))
        except Exception as e:
            self.dialog.after(0, lambda: self._show_error(f"上传截图失败: {str(e)}"))
            import traceback
            traceback.print_exc()

    def _send_image_url_to_server(self, file_url):
        """向服务器发送图片URL消息"""
        message = f"发送屏幕截图{file_url}"
        if self.client:
            # 使用客户端的安全发送方法
            self.client.send_message_threadsafe(message)
            self._add_message(f"你: {message}", is_own=True)
            self.input_var.set("")

    def _on_paired(self, web_client_id: str):
        """配对成功回调"""

        def update():
            self._add_message(f"已与网页客户端 {web_client_id} 配对成功!", is_info=True)
            self.status_var.set(f"已配对: {web_client_id}")

        self.dialog.after(0, update)

    def _show_error(self, error: str):
        """显示错误"""

        def show():
            self._add_message(f"错误: {error}", is_info=True)

        self.dialog.after(0, show)

    def on_auto_input_changed(self):
        """自动输入设置改变"""
        enabled = self.auto_input_enabled.get()
        status = "启用" if enabled else "禁用"
        self._add_message(f"自动输入已{status} (按ESC键停止)", is_info=True)

    def stop_auto_input(self):
        """停止自动输入"""
        self.stop_requested = True
        self.auto_input_running = False

    def on_closing(self):
        """窗口关闭处理"""
        # 停止自动输入
        self.stop_auto_input()

        # 注销截图快捷键
        if self.screenshot_hotkey_registered:
            try:
                keyboard.remove_hotkey('ctrl+alt+z')
                self.screenshot_hotkey_registered = False
            except:
                pass

        # 关闭客户端
        if self.client:
            self.client.running = False

        # 关闭对话框
        if self.dialog:
            self.dialog.destroy()

        # 清理引用
        self.client = None

        # 通知主窗口
        if self.main_window and hasattr(self.main_window, 'remote_assist_dialog'):
            self.main_window.remote_assist_dialog = None


class PythonChatClient:
    """Python聊天客户端"""

    def __init__(self, server_host='101.200.216.53', server_port=8765, client_name=None):
        # 注意：server_host 不应该包含 http:// 前缀
        self.server_host = server_host
        self.server_port = server_port
        self.client_name = client_name or f"PythonClient-{uuid.uuid4().hex[:8]}"
        self.client_id = f"python-{uuid.uuid4().hex}"

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.otp: Optional[str] = None
        self.paired = False
        self.web_client_id: Optional[str] = None
        self.running = True
        self.loop = None  # 保存事件循环的引用

        # 回调函数
        self.status_callback: Optional[Callable] = None
        self.otp_callback: Optional[Callable] = None
        self.message_callback: Optional[Callable] = None
        self.paired_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        self.remote_message_callback: Optional[Callable] = None  # 新增：远程消息回调

        # 存储接收到的消息
        self.received_messages: List[str] = []

        # 新增：远程协助相关
        self.remote_server = None
        self.remote_clients: Set[websockets.WebSocketServerProtocol] = set()

    def set_callbacks(self, status_callback=None, otp_callback=None,
                      message_callback=None, paired_callback=None, error_callback=None,
                      remote_message_callback=None):
        """设置回调函数"""
        self.status_callback = status_callback
        self.otp_callback = otp_callback
        self.message_callback = message_callback
        self.paired_callback = paired_callback
        self.error_callback = error_callback
        self.remote_message_callback = remote_message_callback  # 新增

    def get_received_messages(self) -> List[str]:
        """获取接收到的消息"""
        return self.received_messages.copy()

    async def connect(self):
        """连接到服务器"""
        try:
            uri = f"ws://{self.server_host}:{self.server_port}"

            if self.status_callback:
                self.status_callback(f"正在连接到服务器: {uri}")

            # 设置更长的超时时间
            self.websocket = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=60
            )

            # 发送注册信息（注意：服务器期望 'type' 字段为 'python' 或 'web'）
            await self.websocket.send(json.dumps({
                'type': 'python',  # 关键：必须是 'python' 不是 'register'
                'client_id': self.client_id,
                'name': self.client_name
            }))

            if self.status_callback:
                self.status_callback(f"已连接到服务器")
                self.status_callback(f"客户端ID: {self.client_id}")
                self.status_callback(f"客户端名称: {self.client_name}")
                self.status_callback(f"远程协助服务器监听端口: 8003")

            # 启动心跳任务
            heartbeat_task = asyncio.create_task(self.send_heartbeat())

            # 开始处理消息
            await self.handle_messages()

            # 清理任务
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            error_msg = f"连接失败: {e}"
            logger.error(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)

    async def handle_messages(self):
        """处理来自服务器的消息"""
        try:
            while self.running and self.websocket and self.websocket.open:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )
                    await self.process_message(message)
                except asyncio.TimeoutError:
                    # 超时正常，继续循环
                    continue
                except asyncio.CancelledError:
                    break

        except websockets.exceptions.ConnectionClosed as e:
            error_msg = f"连接已断开 (代码: {e.code}, 原因: {e.reason})"
            logger.info(f"WebSocket连接已关闭: {e}")
            if self.error_callback:
                self.error_callback(error_msg)
        except Exception as e:
            error_msg = f"处理消息时出错: {e}"
            logger.error(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)

    async def process_message(self, message: str):
        """处理单条消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')

            if message_type == 'otp_generated':
                # 收到OTP
                self.otp = data.get('otp')
                expires_in = data.get('expires_in', 6000)

                if self.otp_callback:
                    self.otp_callback(self.otp, expires_in)

                if self.status_callback:
                    self.status_callback("等待网页用户连接...")

            elif message_type == 'paired':
                # 与Web客户端配对成功
                self.paired = True
                self.web_client_id = data.get('web_client_id')

                if self.paired_callback:
                    self.paired_callback(self.web_client_id)

            elif message_type == 'message':
                # 收到聊天消息
                from_client = data.get('from', 'unknown')
                text = data.get('text', '')
                timestamp = data.get('timestamp', '')

                if from_client == 'web':
                    # 存储消息（只存储纯文本）
                    self.received_messages.append(text)

                    # 显示消息（传递纯文本给回调函数）
                    if self.message_callback:
                        # 传递纯文本，GUI会添加时间戳
                        self.message_callback(text)

            elif message_type == 'typing':
                # 显示对方正在输入
                is_typing = data.get('is_typing', False)
                if is_typing and self.status_callback:
                    self.status_callback("网页用户正在输入...")

            elif message_type == 'disconnected':
                # 对方断开连接
                reason = data.get('message', '未知原因')
                if self.error_callback:
                    self.error_callback(reason)
                if self.status_callback:
                    self.status_callback("等待重新连接...")
                self.paired = False

            elif message_type == 'error':
                # 错误消息
                error_msg = data.get('message', '未知错误')
                if self.error_callback:
                    self.error_callback(error_msg)

            elif message_type == 'status_ack':
                # 心跳确认
                pass

        except json.JSONDecodeError as e:
            logger.warning(f"收到无效JSON: {message}, 错误: {e}")
            if self.error_callback:
                self.error_callback(f"收到无法解析的消息: {message}")

    async def send_heartbeat(self):
        """发送心跳保持连接"""
        while self.running and self.websocket and self.websocket.open:
            try:
                await asyncio.sleep(30)  # 每30秒发送一次
                if self.websocket and self.websocket.open:
                    await self.websocket.send(json.dumps({
                        'type': 'status',
                        'status': 'alive',
                        'client_id': self.client_id
                    }))
                    logger.debug("发送心跳")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"发送心跳失败: {e}")
                break

    async def send_message_async(self, message: str):
        """异步发送消息"""
        if self.websocket and self.websocket.open:
            await self.websocket.send(json.dumps({
                'type': 'message',
                'text': message
            }))

    def send_message_threadsafe(self, message: str):
        """线程安全地发送消息"""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.send_message_async(message),
                self.loop
            )

    # 新增：远程协助相关方法
    async def start_remote_server(self, host='localhost', port=8003):
        """启动远程协助服务器"""

        async def handle_remote_client(websocket, path):
            """处理远程协助客户端连接"""
            self.remote_clients.add(websocket)
            client_address = websocket.remote_address
            if self.status_callback:
                self.status_callback(f"远程协助客户端已连接: {client_address}")

            try:
                # 发送确认消息
                await websocket.send(json.dumps({
                    'type': 'acknowledge',
                    'message': '远程协助连接成功',
                    'timestamp': datetime.now().isoformat()
                }))

                # 监听客户端消息
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        message_type = data.get('type')

                        # 根据消息类型处理，使用远程消息回调
                        if message_type == 'question_content':
                            content = data.get('content', {})
                            if self.remote_message_callback:
                                self.remote_message_callback(
                                    f"📝 收到题目内容：{content.get('text_preview', '')[:100]}...")

                            # 转发给聊天服务器（作为普通聊天消息）
                            if self.websocket and self.websocket.open:
                                await self.send_message_async(
                                    f"📝 收到题目内容：{content.get('text_preview', '')[:50000]}..."
                                )

                        elif message_type == 'test_results':
                            results = data.get('results', {})
                            if self.remote_message_callback:
                                self.remote_message_callback(
                                    f"⚠️ 收到测试结果：{results.get('text_preview', '')[:100]}...")

                            # 转发给聊天服务器
                            if self.websocket and self.websocket.open:
                                await self.send_message_async(
                                    f"⚠️ 收到测试结果：{results.get('text_preview', '')[:50000]}..."
                                )

                        elif message_type == 'test_failures':
                            if self.remote_message_callback:
                                self.remote_message_callback(f"❌ 收到测试失败信息")

                        elif message_type == 'test_success':
                            if self.remote_message_callback:
                                self.remote_message_callback(f"✅ 所有测试通过")

                        elif message_type == 'code_generated':
                            if self.remote_message_callback:
                                self.remote_message_callback(f"💾 代码已生成")

                        elif message_type == 'code_revised':
                            if self.remote_message_callback:
                                self.remote_message_callback(f"🔄 代码已修正")

                        elif message_type == 'input_complete':
                            if self.remote_message_callback:
                                self.remote_message_callback(f"✅ 代码输入完成")

                        elif message_type == 'input_cancelled':
                            if self.remote_message_callback:
                                self.remote_message_callback(f"❌ 代码输入已取消")

                        elif message_type == 'input_error':
                            if self.remote_message_callback:
                                self.remote_message_callback(f"❌ 代码输入错误")

                        else:
                            if self.remote_message_callback:
                                self.remote_message_callback(f"收到远程消息: {data}")

                    except json.JSONDecodeError:
                        if self.remote_message_callback:
                            self.remote_message_callback(f"收到非JSON远程消息: {message}")

            except websockets.exceptions.ConnectionClosed:
                if self.status_callback:
                    self.status_callback(f"远程协助客户端断开: {client_address}")
            except Exception as e:
                if self.error_callback:
                    self.error_callback(f"处理远程客户端时出错: {e}")
            finally:
                self.remote_clients.remove(websocket)

        # 启动远程协助服务器
        try:
            self.remote_server = await websockets.serve(
                handle_remote_client,
                host,
                port
            )
            if self.status_callback:
                self.status_callback(f"远程协助服务器已启动，监听 {host}:{port}")
            return self.remote_server
        except Exception as e:
            if self.error_callback:
                self.error_callback(f"启动远程协助服务器失败: {e}")
            return None

    async def broadcast_to_remote_clients(self, message):
        """向所有远程协助客户端广播消息"""
        if not self.remote_clients:
            return

        disconnected_clients = set()
        for client in self.remote_clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                if self.error_callback:
                    self.error_callback(f"向远程客户端发送消息失败: {e}")
                disconnected_clients.add(client)

        # 移除断开连接的客户端
        for client in disconnected_clients:
            self.remote_clients.remove(client)

    async def run_with_loop(self):
        """通过事件循环运行客户端"""
        try:
            # 保存当前事件循环
            self.loop = asyncio.get_event_loop()

            if self.status_callback:
                self.status_callback("正在启动远程协助服务器...")

            # 启动远程协助服务器
            remote_server_task = asyncio.create_task(self.start_remote_server())

            if self.status_callback:
                self.status_callback("正在连接到服务器...")

            # 连接服务器
            await self.connect()

            # 等待远程服务器关闭
            await remote_server_task

        except KeyboardInterrupt:
            if self.status_callback:
                self.status_callback("客户端关闭")
        except Exception as e:
            error_msg = f"客户端运行失败: {e}"
            logger.error(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)
        finally:
            self.running = False

            # 关闭远程协助服务器
            if self.remote_server:
                self.remote_server.close()
                await self.remote_server.wait_closed()

            # 关闭所有远程客户端连接
            for client in self.remote_clients:
                await client.close()

            # 关闭主连接
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()