import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import websockets
import json
import threading

from gui.main_window import EducoderGUI
from utils.config import ConfigManager


class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Educoder助手")
        self.root.geometry("400x400")
        self.root.resizable(False, True)
        
        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")
        
        self.config_manager = ConfigManager()
        self.auth_server_url = "ws://101.200.216.53:8001"  #  服务器地址
        
        self.setup_ui()
        self.load_saved_credentials()
        
    def setup_ui(self):
        """设置登录界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="Educoder助手", 
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # 用户名
        ttk.Label(main_frame, text="用户名:").pack(anchor=tk.W, pady=(10, 0))
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(main_frame, textvariable=self.username_var, width=30)
        self.username_entry.pack(fill=tk.X, pady=5)
        
        # 密码
        ttk.Label(main_frame, text="密码:").pack(anchor=tk.W, pady=(10, 0))
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(main_frame, textvariable=self.password_var, show="*", width=30)
        self.password_entry.pack(fill=tk.X, pady=5)
        
        # 记住密码和自动登录
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=10)
        
        self.remember_var = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame, 
            text="记住密码",
            variable=self.remember_var
        ).pack(side=tk.LEFT)
        
        self.auto_login_var = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame, 
            text="自动登录",
            variable=self.auto_login_var
        ).pack(side=tk.LEFT, padx=(20, 0))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.login_button = ttk.Button(
            button_frame, 
            text="登录", 
            command=self.login,
            width=10
        )
        self.login_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.register_button = ttk.Button(
            button_frame, 
            text="注册", 
            command=self.register,
            width=10
        )
        self.register_button.pack(side=tk.LEFT)
        
        # 状态标签
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="gray")
        status_label.pack(pady=5)
        
        # 绑定回车键
        self.root.bind('<Return>', lambda event: self.login())
        
    def load_saved_credentials(self):
        """加载保存的凭据"""
        credentials = self.config_manager.load_credentials()
        if credentials:
            self.username_var.set(credentials.get('username', ''))
            self.password_var.set(credentials.get('password', ''))
            self.remember_var.set(credentials.get('remember', False))
            self.auto_login_var.set(credentials.get('auto_login', False))
            
            # 如果启用自动登录，自动尝试登录
            if self.auto_login_var.get() and self.username_var.get() and self.password_var.get():
                self.root.after(500, self.auto_login)
                
    def save_credentials(self):
        """保存凭据"""
        if self.remember_var.get():
            credentials = {
                'username': self.username_var.get(),
                'password': self.password_var.get(),
                'remember': True,
                'auto_login': self.auto_login_var.get()
            }
        else:
            credentials = {
                'username': '',
                'password': '',
                'remember': False,
                'auto_login': False
            }
            
        self.config_manager.save_credentials(credentials)
        
    def auto_login(self):
        """自动登录"""
        self.status_var.set("正在自动登录...")
        self.login()
        
    def login(self):
        """用户登录"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码")
            return
            
        # 禁用按钮
        self.login_button.config(state="disabled")
        self.register_button.config(state="disabled")
        self.status_var.set("正在登录...")
        
        # 在新线程中执行登录
        threading.Thread(target=self._perform_login, args=(username, password), daemon=True).start()
        
    def register(self):
        """用户注册"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码")
            return
            
        # 禁用按钮
        self.login_button.config(state="disabled")
        self.register_button.config(state="disabled")
        self.status_var.set("正在注册...")
        
        # 在新线程中执行注册
        threading.Thread(target=self._perform_register, args=(username, password), daemon=True).start()
        
    def _perform_login(self, username, password):
        """执行登录操作"""
        try:
            # 使用asyncio在单独的事件循环中运行异步代码
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self._send_auth_request({
                'action': 'login',
                'username': username,
                'password': password
            }))
            
            loop.close()
            
            self.root.after(0, lambda: self._handle_login_result(result))
            
        except Exception as e:
            self.root.after(0, lambda: self._handle_auth_error(f"登录失败: {str(e)}"))
            
    def _perform_register(self, username, password):
        """执行注册操作"""
        try:
            # 使用asyncio在单独的事件循环中运行异步代码
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self._send_auth_request({
                'action': 'register',
                'username': username,
                'password': password
            }))
            loop.close()
            self.root.after(0, lambda: self._handle_register_result(result))

        except Exception as e:
            self.root.after(0, lambda: self._handle_auth_error(f"注册失败: {str(e)}"))
            
    async def _send_auth_request(self, data):
        """发送认证请求"""
        try:
            async with websockets.connect(self.auth_server_url) as websocket:
                 await websocket.send(json.dumps(data))
                 response = await websocket.recv()
                 return json.loads(response)
        except Exception as e:
                 messagebox.showerror("错误", "请检查网络连接是否正常")
                 return

            
    def _handle_login_result(self, result):
        """处理登录结果"""
        # 重新启用按钮
        self.login_button.config(state="normal")
        self.register_button.config(state="normal")
        try:
            if result.get('success'):
                # 保存凭据
                 self.save_credentials()
            
                # 保存用户会话
                 self.config_manager.save_user_session({
                'username': result.get('username'),
                'token': result.get('token')
                })
            
                 self.status_var.set("登录成功")
                 messagebox.showinfo("成功", "登录成功")
            
                 # 打开主窗口
                 self.open_main_window(result.get('username'), result.get('token'))
            else:
                self.status_var.set("登录失败")
                messagebox.showerror("错误", result.get('message', '登录失败'))
        except:
            return
            
    def _handle_register_result(self, result):
        """处理注册结果"""
        # 重新启用按钮
        self.login_button.config(state="normal")
        self.register_button.config(state="normal")
        try:
          if result.get('success'):
            self.status_var.set("注册成功")
            messagebox.showinfo("成功", "注册成功，请登录")
          else:
            self.status_var.set("注册失败")
            messagebox.showerror("错误", result.get('message', '注册失败'))
        except:
            return
            
    def _handle_auth_error(self, message):
        """处理认证错误"""
        # 重新启用按钮
        self.login_button.config(state="normal")
        self.register_button.config(state="normal")
        
        self.status_var.set("操作失败")
        messagebox.showerror("错误", message)
        
    def open_main_window(self, username, token):
        """打开主窗口"""
        # 隐藏登录窗口
        self.root.withdraw()
        
        # 创建主窗口
        main_window = tk.Toplevel(self.root)
        main_window.title("Educoder助手")
        main_window.geometry("800x800")
        
        # 设置关闭主窗口时退出程序
        main_window.protocol("WM_DELETE_WINDOW", lambda: self.on_main_window_close(main_window))
        
        # 创建主应用
        app = EducoderGUI(main_window, username, token)
        
    def on_main_window_close(self, main_window):
        """主窗口关闭时的处理"""
        # 保存会话
        self.config_manager.save_user_session(None)
        
        # 关闭所有窗口
        main_window.destroy()
        self.root.destroy()