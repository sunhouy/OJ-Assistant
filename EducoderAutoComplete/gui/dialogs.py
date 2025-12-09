import configparser
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

from utils.config import ConfigManager


class FirstRunDialog:
    def __init__(self, parent, on_close_callback=None):
        self.parent = parent
        self.config_manager = ConfigManager()  # 创建 ConfigManager 实例
        self.dont_show_again = tk.BooleanVar(value=False)
        self.on_close_callback = on_close_callback  # 关闭对话框时的回调函数

        # 尝试导入 extension_setup 模块
        try:
            from utils.extension_setup import main as run_extension_setup
            self.EXTENSION_SETUP_AVAILABLE = True
            self.run_extension_setup = run_extension_setup
        except ImportError:
            self.EXTENSION_SETUP_AVAILABLE = False

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("安装浏览器扩展")
        self.dialog.geometry("750x850")
        # 设置背景色为白色
        self.dialog.configure(bg='white')
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 设置窗口最小尺寸
        self.dialog.minsize(650, 500)

        # 居中显示
        self.dialog.update_idletasks()
        x = (parent.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (parent.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # 设置现代化样式
        self.setup_styles()
        self.setup_ui()

    def find_extension_setup_file(self):
        """查找extension_setup.py文件"""
        # 尝试在当前目录查找
        current_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(current_dir, "extension_setup.py"),
            os.path.join(os.path.dirname(current_dir), "extension_setup.py"),
            os.path.join(current_dir, "gui", "extension_setup.py"),
            os.path.join(current_dir, "tools", "extension_setup.py"),
            os.path.join(current_dir, "utils", "extension_setup.py"),  # 添加utils路径
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # 如果在固定位置找不到，尝试搜索整个项目
        project_root = os.path.dirname(current_dir)
        for root, dirs, files in os.walk(project_root):
            if "extension_setup.py" in files:
                return os.path.join(root, "extension_setup.py")

        return None

    def setup_styles(self):
        """设置现代化样式"""
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except:
            style.theme_use('winnative')

        # 设置全局背景色为白色
        style.configure('.', background='white')

        # 配置标题标签
        style.configure('Title.TLabel',
                        font=('微软雅黑', 20, 'bold'),
                        background='white',
                        foreground='#2c3e50')

        style.configure('Subtitle.TLabel',
                        font=('微软雅黑', 12),
                        background='white',
                        foreground='#7f8c8d',
                        wraplength=600)

        style.configure('Section.TLabel',
                        font=('微软雅黑', 12, 'bold'),
                        background='white',
                        foreground='#3498db')

        style.configure('Normal.TLabel',
                        font=('微软雅黑', 10),
                        background='white',
                        foreground='#34495e',
                        wraplength=650)

        style.configure('Warning.TLabel',
                        font=('微软雅黑', 10, 'bold'),
                        background='white',
                        foreground='#e74c3c',
                        padding=5)

        # 统一按钮样式 - 黑色文字
        style.configure('Action.TButton',
                        font=('微软雅黑', 12, 'bold'),  # 增大字体使其更醒目
                        padding=12,
                        background='#ffffff',  # 白色背景
                        foreground='#000000',  # 黑色文字
                        borderwidth=2,
                        relief='raised')

        style.map('Action.TButton',
                  background=[('active', '#f0f0f0'), ('pressed', '#e0e0e0')],
                  foreground=[('active', '#000000'), ('pressed', '#000000')])

        # 配置复选框样式
        style.configure('Custom.TCheckbutton',
                        font=('微软雅黑', 10),
                        background='white',
                        foreground='#2c3e50')

    def setup_ui(self):
        """设置对话框界面"""
        # 主框架 - 白色背景
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建滚动区域
        canvas = tk.Canvas(main_frame, bg='white', highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)

        # 滚动框架
        scrollable_frame = ttk.Frame(canvas)

        # 窗口配置
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 使框架适应宽度
        def configure_canvas(event):
            canvas.itemconfig(canvas_frame, width=event.width)

        canvas.bind("<Configure>", configure_canvas)

        # 网格布局
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 2))
        scrollbar.pack(side="right", fill="y")

        # 图标和标题
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(pady=(0, 15), fill='x')

        # 图标（使用文字模拟）
        icon_label = tk.Label(title_frame,
                              text="🚀",
                              font=('Arial', 40),
                              bg='white',
                              fg='#3498db')
        icon_label.pack(side='left', padx=(0, 15))

        title_text_frame = ttk.Frame(title_frame)
        title_text_frame.pack(side='left', fill='x', expand=True)

        # 主标题
        title_label = ttk.Label(
            title_text_frame,
            text="安装浏览器扩展",
            style='Title.TLabel'
        )
        title_label.pack(anchor='w')

        # 副标题
        subtitle_label = ttk.Label(
            title_text_frame,
            text="为了正常使用 Educoder 助手，您需要安装浏览器扩展插件",
            style='Subtitle.TLabel'
        )
        subtitle_label.pack(anchor='w', pady=(5, 0))

        # 分隔线
        separator = ttk.Separator(scrollable_frame, orient='horizontal')
        separator.pack(fill='x', pady=(0, 20))

        # 为什么需要安装扩展
        why_section = ttk.Label(
            scrollable_frame,
            text="为什么需要安装扩展？",
            style='Section.TLabel'
        )
        why_section.pack(anchor='w', pady=(0, 10))

        why_text = """没有扩展插件，Educoder 助手无法正常工作
您可以选择手动安装或自动安装的方式，
手动安装后，您只需保持本客户端是启动状态，即可在
您安装拓展的浏览器使用Educoder助手
自动安装的拓展必须每次通过主页的“启动浏览器”启动"""
        why_label = ttk.Label(
            scrollable_frame,
            text=why_text,
            style='Normal.TLabel'
        )
        why_label.pack(anchor='w', pady=(0, 20))

        # 安装步骤
        steps_section = ttk.Label(
            scrollable_frame,
            text="安装步骤",
            style='Section.TLabel'
        )
        steps_section.pack(anchor='w', pady=(0, 10))

        steps_text = """点击下方"跳转安装扩展"按钮开始安装"""

        steps_label = ttk.Label(
            scrollable_frame,
            text=steps_text,
            style='Normal.TLabel'
        )
        steps_label.pack(anchor='w', pady=(0, 20))

        # 支持的浏览器
        browsers_section = ttk.Label(
            scrollable_frame,
            text="支持的浏览器",
            style='Section.TLabel'
        )
        browsers_section.pack(anchor='w', pady=(0, 10))

        browsers_frame = ttk.Frame(scrollable_frame)
        browsers_frame.pack(anchor='w', pady=(0, 20), fill='x')

        # Chrome浏览器
        chrome_frame = ttk.Frame(browsers_frame)
        chrome_frame.pack(fill='x', pady=2)

        chrome_icon = tk.Label(chrome_frame,
                               text="🌐",
                               font=('Arial', 16),
                               bg='white',
                               fg='#4285F4')
        chrome_icon.pack(side='left', padx=(0, 10))

        chrome_text = ttk.Label(chrome_frame,
                                text="Google Chrome",
                                style='Normal.TLabel',
                                font=('微软雅黑', 10, 'bold'))
        chrome_text.pack(side='left')

        # Edge浏览器
        edge_frame = ttk.Frame(browsers_frame)
        edge_frame.pack(fill='x', pady=2)

        edge_icon = tk.Label(edge_frame,
                             text="🌐",
                             font=('Arial', 16),
                             bg='white',
                             fg='#0078D7')
        edge_icon.pack(side='left', padx=(0, 10))

        edge_text = ttk.Label(edge_frame,
                              text="Microsoft Edge",
                              style='Normal.TLabel',
                              font=('微软雅黑', 10, 'bold'))
        edge_text.pack(side='left')

        # 重要提示
        warning_frame = ttk.Frame(scrollable_frame)
        warning_frame.pack(fill='x', pady=10)

        warning_icon = tk.Label(warning_frame,
                                text="⚠️",
                                font=('Arial', 16),
                                bg='white',
                                fg='#e74c3c')
        warning_icon.pack(side='left', padx=(0, 10))

        warning_text = """本应用仅供学习交流使用，不得用于商业和非法用途。"""  # 重要提示

        warning_label = ttk.Label(warning_frame,
                                  text=warning_text,
                                  style='Warning.TLabel')
        warning_label.pack(side='left')

        # 底部按钮区域
        bottom_frame = ttk.Frame(scrollable_frame)
        bottom_frame.pack(fill='x', pady=(20, 0))

        # 左侧复选框
        left_frame = ttk.Frame(bottom_frame)
        left_frame.pack(side='left')

        # 创建复选框
        self.checkbox = ttk.Checkbutton(
            left_frame,
            text="下次不再显示此提示",
            variable=self.dont_show_again,
            style='Custom.TCheckbutton'
        )
        self.checkbox.pack(side='left', padx=5)

        # 右侧按钮
        right_frame = ttk.Frame(bottom_frame)
        right_frame.pack(side='right')

        # 创建统一的按钮容器，确保两个按钮大小一致
        buttons_frame = ttk.Frame(right_frame)
        buttons_frame.pack(side='right')

        # 跳转安装扩展按钮
        install_button = ttk.Button(
            buttons_frame,
            text="跳转安装扩展",
            command=self.open_extension_install,
            style='Action.TButton',
            cursor='hand2',
            width=15  # 固定宽度确保两个按钮一样大
        )
        install_button.pack(side='left', padx=(0, 5))

        # 我已安装扩展按钮
        self.ok_button = ttk.Button(
            buttons_frame,
            text="我已安装扩展",
            command=self.on_confirm,
            style='Action.TButton',
            cursor='hand2',
            width=15  # 固定宽度确保两个按钮一样大
        )
        self.ok_button.pack(side='left', padx=(5, 0))

        # 绑定鼠标滚轮滚动
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # 绑定到Canvas和可滚动框架
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        scrollable_frame.bind_all("<MouseWheel>", on_mousewheel)

        # 确保窗口加载时焦点正确
        self.dialog.after(100, lambda: self.dialog.focus_force())

    def open_extension_install(self):
        """打开浏览器扩展安装工具"""
        try:
            if not hasattr(self, 'EXTENSION_SETUP_AVAILABLE') or not self.EXTENSION_SETUP_AVAILABLE:
                # 如果无法导入，尝试使用子进程方式
                script_path = self.find_extension_setup_file()
                if script_path and os.path.exists(script_path):
                    python_exe = sys.executable
                    subprocess.Popen([python_exe, script_path],
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    raise ImportError("无法找到 extension_setup.py 文件")
            else:
                # 在新线程中运行扩展安装工具，避免阻塞主界面
                threading.Thread(
                    target=self._run_extension_setup_thread,
                    daemon=True
                ).start()

        except Exception as e:
            # 显示错误信息
            messagebox.showerror("错误", f"无法打开扩展安装工具:\n{str(e)}")

    def _run_extension_setup_thread(self):
        """在新线程中运行扩展安装工具"""
        try:
            # 直接运行扩展安装工具的main函数
            self.run_extension_setup()
        except Exception as e:
            # 如果直接运行失败，尝试使用子进程
            try:
                script_path = self.find_extension_setup_file()
                if script_path and os.path.exists(script_path):
                    python_exe = sys.executable
                    subprocess.Popen([python_exe, script_path],
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    raise e
            except Exception as e2:
                # 在GUI线程中显示错误信息
                self.dialog.after(0, lambda: messagebox.showerror(
                    "错误",
                    f"无法打开扩展安装工具:\n{str(e2)}"
                ))

    def on_confirm(self):
        """确定按钮点击事件"""
        # 使用 ConfigManager 保存设置
        self.config_manager._ensure_config()

        # 使用 configparser 直接写入正确的配置文件
        config = configparser.ConfigParser()
        config['SETTINGS'] = {
            'show_welcome': str(not self.dont_show_again.get())
        }

        try:
            with open(self.config_manager.config_file, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        except Exception as e:
            print(f"保存配置失败: {e}")

        # 关闭对话框
        self.dialog.destroy()

        # 如果有回调函数，执行它
        if self.on_close_callback:
            self.on_close_callback()


def main():
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    def on_close():
        print("对话框已关闭")
        root.quit()

    dialog = FirstRunDialog(root, on_close)
    root.mainloop()


if __name__ == "__main__":
    main()