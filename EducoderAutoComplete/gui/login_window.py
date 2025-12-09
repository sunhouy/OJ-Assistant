import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

import requests

from gui.dialogs import FirstRunDialog
from gui.main_window import EducoderGUI
from utils.config import ConfigManager


class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Educoder助手")
        self.root.iconphoto(True, tk.PhotoImage(file='app.ico'))
        self.root.geometry("400x550")
        self.root.resizable(False, True)

        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")

        self.config_manager = ConfigManager()
        self.api_base_url = "http://yhsun.cn/server/index.php"

        # 获取或生成机器码
        self.machine_code = self.config_manager.get_machine_code()

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
        title_label.pack(pady=(0, 10))

        # 使用Notebook作为选择区
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.X, pady=(0, 20))

        # 创建登录和注册两个标签页
        self.login_frame = ttk.Frame(self.notebook)
        self.register_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.login_frame, text="    登录    ")
        self.notebook.add(self.register_frame, text="    注册    ")

        # 绑定标签切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 初始化登录界面
        self.setup_login_ui()

        # 初始化注册界面
        self.setup_register_ui()

        # 状态标签
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="gray")
        status_label.pack(pady=5)

        # 会员状态提示
        self.member_status_var = tk.StringVar()
        self.member_status_label = ttk.Label(
            main_frame,
            textvariable=self.member_status_var,
            foreground="blue",
            cursor="hand2"
        )
        self.member_status_label.pack(pady=5)
        self.member_status_label.bind("<Button-1>", lambda e: self.open_member_page())

        # 绑定回车键 - 根据当前标签页执行不同操作
        self.root.bind('<Return>', lambda event: self.on_enter_key())

    def setup_login_ui(self):
        """设置登录界面"""
        # 用户名
        ttk.Label(self.login_frame, text="用户名：").pack(anchor=tk.W, pady=(10, 0))
        self.login_username_var = tk.StringVar()
        self.login_username_entry = ttk.Entry(self.login_frame, textvariable=self.login_username_var, width=30)
        self.login_username_entry.pack(fill=tk.X, pady=5)

        # 密码
        ttk.Label(self.login_frame, text="密码：").pack(anchor=tk.W, pady=(10, 0))
        self.login_password_var = tk.StringVar()
        self.login_password_entry = ttk.Entry(self.login_frame, textvariable=self.login_password_var, show="*",
                                              width=30)
        self.login_password_entry.pack(fill=tk.X, pady=5)

        # 记住密码和自动登录
        options_frame = ttk.Frame(self.login_frame)
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

        # 登录按钮
        self.login_button = ttk.Button(
            self.login_frame,
            text="登录",
            command=self.login,
            width=10
        )
        self.login_button.pack(pady=10)

    def setup_register_ui(self):
        """设置注册界面"""
        # 用户名
        ttk.Label(self.register_frame, text="用户名:").pack(anchor=tk.W, pady=(10, 0))
        self.register_username_var = tk.StringVar()
        self.register_username_entry = ttk.Entry(self.register_frame, textvariable=self.register_username_var, width=30)
        self.register_username_entry.pack(fill=tk.X, pady=5)

        # 密码
        ttk.Label(self.register_frame, text="密码:").pack(anchor=tk.W, pady=(10, 0))
        self.register_password_var = tk.StringVar()
        self.register_password_entry = ttk.Entry(self.register_frame, textvariable=self.register_password_var, show="*",
                                                 width=30)
        self.register_password_entry.pack(fill=tk.X, pady=5)

        # 邀请码
        ttk.Label(self.register_frame, text="邀请码（选填）:").pack(anchor=tk.W, pady=(10, 0))
        self.invite_var = tk.StringVar()
        self.invite_entry = ttk.Entry(self.register_frame, textvariable=self.invite_var, width=30)
        self.invite_entry.pack(fill=tk.X, pady=5)

        # 邀请码提示文字
        invite_hint = ttk.Label(
            self.register_frame,
            text="使用邀请码注册免费送1天会员",
            foreground="green",
            font=("微软雅黑", 9)
        )
        invite_hint.pack(pady=(0, 10))

        # 注册按钮
        self.register_button = ttk.Button(
            self.register_frame,
            text="注册",
            command=self.register,
            width=10
        )
        self.register_button.pack(pady=10)

    def on_tab_changed(self, event=None):
        """标签页切换事件"""
        current_tab = self.notebook.index(self.notebook.select())

        # 同步账号密码信息
        if current_tab == 0:  # 登录标签页
            # 将注册页面的账号密码复制到登录页面
            if self.register_username_var.get():
                self.login_username_var.set(self.register_username_var.get())
            if self.register_password_var.get():
                self.login_password_var.set(self.register_password_var.get())
        else:  # 注册标签页
            # 将登录页面的账号密码复制到注册页面
            if self.login_username_var.get():
                self.register_username_var.set(self.login_username_var.get())
            if self.login_password_var.get():
                self.register_password_var.set(self.login_password_var.get())

    def on_enter_key(self):
        """回车键事件"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # 登录标签页
            self.login()
        else:  # 注册标签页
            self.register()

    def open_member_page(self):
        """打开会员页面"""
        webbrowser.open("https://yhsun.cn/server/member")

    def load_saved_credentials(self):
        """加载保存的凭据"""
        credentials = self.config_manager.load_credentials()
        if credentials:
            self.login_username_var.set(credentials.get('username', ''))
            self.login_password_var.set(credentials.get('password', ''))
            self.register_username_var.set(credentials.get('username', ''))
            self.register_password_var.set(credentials.get('password', ''))
            self.remember_var.set(credentials.get('remember', False))
            self.auto_login_var.set(credentials.get('auto_login', False))

            # 如果启用自动登录，自动尝试登录
            if self.auto_login_var.get() and self.login_username_var.get() and self.login_password_var.get():
                self.root.after(500, self.auto_login)

    def save_credentials(self):
        """保存凭据"""
        username = self.login_username_var.get()
        password = self.login_password_var.get()

        if self.remember_var.get():
            credentials = {
                'username': username,
                'password': password,
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
        username = self.login_username_var.get().strip()
        password = self.login_password_var.get().strip()

        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码")
            return

        # 更新注册页面的账号密码
        self.register_username_var.set(username)
        self.register_password_var.set(password)

        # 禁用按钮
        self.login_button.config(state="disabled")
        self.register_button.config(state="disabled")
        self.status_var.set("正在登录...")
        self.member_status_var.set("")  # 清空会员状态提示

        # 在新线程中执行登录
        threading.Thread(target=self._perform_login, args=(username, password), daemon=True).start()

    def register(self):
        """用户注册"""
        username = self.register_username_var.get().strip()
        password = self.register_password_var.get().strip()
        invite_code = self.invite_var.get().strip() or None

        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码")
            return

        # 更新登录页面的账号密码
        self.login_username_var.set(username)
        self.login_password_var.set(password)

        # 禁用按钮
        self.login_button.config(state="disabled")
        self.register_button.config(state="disabled")
        self.status_var.set("正在注册...")
        self.member_status_var.set("")  # 清空会员状态提示

        # 在新线程中执行注册
        threading.Thread(target=self._perform_register, args=(username, password, invite_code), daemon=True).start()

    def _perform_login(self, username, password):
        """执行登录操作"""
        try:
            # 使用新的API进行登录
            result = self._send_login_request(username, password)

            if result and result.get('code') == 200:
                # 登录成功，检查会员状态
                member_result = self._check_member_status(username)

                self.root.after(0, lambda: self._handle_login_result(result, member_result, username))
            else:
                self.root.after(0, lambda: self._handle_auth_error(result))

        except Exception as e:
            self.root.after(0, lambda: self._handle_auth_error(f"登录失败: {str(e)}"))

    def _perform_register(self, username, password, invite_code):
        """执行注册操作"""
        try:
            # 使用新的API进行注册
            result = self._send_register_request(username, password, invite_code)

            if result and result.get('code') == 200:
                # 注册成功，自动登录
                self.status_var.set("注册成功，正在自动登录...")

                # 尝试自动登录
                threading.Thread(target=self._perform_auto_login_after_register,
                                 args=(username, password), daemon=True).start()
            else:
                self.root.after(0, lambda: self._handle_register_result(result))

        except Exception as e:
            self.root.after(0, lambda: self._handle_auth_error(f"注册失败: {str(e)}"))

    def _send_login_request(self, username, password):
        """发送登录请求"""
        url = f"{self.api_base_url}?action=login"
        data = {
            'username': username,
            'password': password,
            'machine_code': self.machine_code
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            return response.json()
        except requests.exceptions.Timeout:
            return {'code': 408, 'message': '请求超时，请检查网络连接'}
        except requests.exceptions.ConnectionError:
            return {'code': 500, 'message': '网络连接错误，请检查网络连接'}
        except Exception as e:
            return {'code': 500, 'message': f'请求失败: {str(e)}'}

    def _send_register_request(self, username, password, invite_code):
        """发送注册请求"""
        url = f"{self.api_base_url}?action=register"
        data = {
            'username': username,
            'password': password,
            'machine_code': self.machine_code
        }

        # 如果有邀请码，添加到请求数据中
        if invite_code:
            data['invite_code'] = invite_code

        try:
            response = requests.post(url, json=data, timeout=10)
            return response.json()
        except requests.exceptions.Timeout:
            return {'code': 408, 'message': '请求超时，请检查网络连接'}
        except requests.exceptions.ConnectionError:
            return {'code': 500, 'message': '网络连接错误，请检查网络连接'}
        except Exception as e:
            return {'code': 500, 'message': f'请求失败: {str(e)}'}

    def _check_member_status(self, username):
        """检查会员状态"""
        url = f"{self.api_base_url}?action=check_member"
        data = {
            'username': username,
            'machine_code': self.machine_code
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            return response.json()
        except Exception as e:
            # 如果检查会员状态失败，仍然允许登录，但提示会员状态未知
            return {'code': 500, 'message': f'检查会员状态失败: {str(e)}', 'data': {}}

    def _handle_login_result(self, login_result, member_result, username):
        """处理登录结果"""
        # 重新启用按钮
        self.login_button.config(state="normal")
        self.register_button.config(state="normal")

        try:
            if login_result.get('code') == 200:
                # 保存凭据（登录成功时根据记住密码选项重写）
                self.save_credentials()

                # 保存用户会话
                self.config_manager.save_user_session({
                    'username': username,
                    'token': login_result.get('data', {}).get('token', ''),
                    'machine_code': self.machine_code
                })

                self.status_var.set("登录成功")

                # 检查会员状态
                if member_result.get('code') == 200:
                    member_data = member_result.get('data', {})
                    is_member = member_data.get('is_member', False)
                    expire_date = member_data.get('expire_date', '')

                    if is_member:
                        self.status_var.set(f"登录成功，会员有效期至: {expire_date}")
                    else:
                        self.status_var.set("登录成功，非会员用户")
                        self.member_status_var.set("点击此处开通会员")
                else:
                    # 会员状态检查失败，但仍允许登录
                    self.status_var.set("登录成功，会员状态未知")

                # 打开主窗口
                self.open_main_window(username, login_result.get('data', {}).get('token', ''))
            else:
                self.status_var.set("登录失败")
                messagebox.showerror("错误", login_result.get('message', '登录失败'))
        except Exception as e:
            self.status_var.set("登录失败")
            messagebox.showerror("错误", f"处理登录结果时出错: {str(e)}")

    def _handle_register_result(self, result):
        """处理注册结果"""
        try:
            if result.get('code') == 200:
                # 注册成功，启用按钮，等待自动登录
                self.login_button.config(state="normal")
                self.register_button.config(state="normal")
                self.status_var.set("注册成功，正在自动登录...")
            else:
                # 重新启用按钮
                self.login_button.config(state="normal")
                self.register_button.config(state="normal")
                self.status_var.set("注册失败")
                messagebox.showerror("错误", result.get('message', '注册失败'))
        except:
            # 重新启用按钮
            self.login_button.config(state="normal")
            self.register_button.config(state="normal")

    def _perform_auto_login_after_register(self, username, password):
        """注册成功后自动登录"""
        try:
            # 使用新的API进行登录
            result = self._send_login_request(username, password)

            if result and result.get('code') == 200:
                # 登录成功，检查会员状态
                member_result = self._check_member_status(username)

                self.root.after(0, lambda: self._handle_auto_login_after_register(result, member_result, username))
            else:
                self.root.after(0, lambda: self._handle_auth_error(result))
                # 重新启用按钮
                self.root.after(0, lambda: self._enable_buttons())

        except Exception as e:
            self.root.after(0, lambda: self._handle_auth_error(f"自动登录失败: {str(e)}"))
            # 重新启用按钮
            self.root.after(0, lambda: self._enable_buttons())

    def _handle_auto_login_after_register(self, result, member_result, username):
        """处理注册后的自动登录结果"""
        try:
            if result.get('code') == 200:
                # 保存用户会话
                self.config_manager.save_user_session({
                    'username': username,
                    'token': result.get('data', {}).get('token', ''),
                    'machine_code': self.machine_code
                })

                self.status_var.set("自动登录成功")

                # 检查会员状态
                if member_result.get('code') == 200:
                    member_data = member_result.get('data', {})
                    is_member = member_data.get('is_member', False)
                    expire_date = member_data.get('expire_date', '')

                    if is_member:
                        self.status_var.set(f"自动登录成功，会员有效期至: {expire_date}")
                    else:
                        self.status_var.set("自动登录成功，非会员用户")
                        self.member_status_var.set("点击此处开通会员")
                else:
                    self.status_var.set("自动登录成功，会员状态未知")

                # 打开主窗口
                self.open_main_window(username, result.get('data', {}).get('token', ''))
            else:
                # 重新启用按钮
                self.login_button.config(state="normal")
                self.register_button.config(state="normal")

                self.status_var.set("自动登录失败")
                messagebox.showerror("错误", "注册成功，但自动登录失败，请手动登录")
        except:
            # 重新启用按钮
            self.login_button.config(state="normal")
            self.register_button.config(state="normal")

    def _enable_buttons(self):
        """启用按钮"""
        self.login_button.config(state="normal")
        self.register_button.config(state="normal")

    def _handle_auth_error(self, message):
        """处理认证错误"""
        # 重新启用按钮
        self.login_button.config(state="normal")
        self.register_button.config(state="normal")

        self.status_var.set("操作失败")

        if isinstance(message, dict):
            # 如果是字典类型的错误消息
            error_msg = message.get('message', '未知错误')
            messagebox.showerror("错误", error_msg)
        else:
            # 如果是字符串类型的错误消息
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
        app = EducoderGUI(main_window, username, token, self.machine_code)

        # 检查是否需要显示首次运行对话框
        self.check_and_show_welcome_dialog(main_window)

    def check_and_show_welcome_dialog(self, parent_window):
        """检查并显示首次运行对话框"""
        try:
            # 使用 ConfigManager 检查是否需要显示欢迎对话框
            if self.config_manager.should_show_welcome():
                self.show_welcome_dialog(parent_window)
        except Exception as e:
            print(f"检查配置文件时出错: {e}")
            # 出错时默认显示欢迎对话框
            self.show_welcome_dialog(parent_window)

    def show_welcome_dialog(self, parent_window):
        """显示首次运行对话框"""
        try:
            # 创建并显示对话框
            welcome_dialog = FirstRunDialog(parent_window)
        except Exception as e:
            print(f"显示欢迎对话框时出错: {e}")

    def on_main_window_close(self, main_window):
        """主窗口关闭时的处理"""
        # 保存会话
        self.config_manager.save_user_session(None)

        # 关闭所有窗口
        main_window.destroy()
        self.root.destroy()