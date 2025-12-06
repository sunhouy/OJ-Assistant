import tkinter as tk
from tkinter import ttk
import configparser
import os
import webbrowser

from utils.config import ConfigManager


class FirstRunDialog:
    def __init__(self, parent, on_close_callback=None):
        self.parent = parent
        self.config_manager = ConfigManager()  # 创建 ConfigManager 实例
        self.dont_show_again = tk.BooleanVar(value=False)
        self.on_close_callback = on_close_callback  # 关闭对话框时的回调函数

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("安装浏览器扩展")
        self.dialog.geometry("750x750")
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

        # 主按钮样式
        style.configure('Primary.TButton',
                        font=('微软雅黑', 11, 'bold'),
                        padding=10,
                        background='#3498db',
                        foreground='white')

        style.map('Primary.TButton',
                  background=[('active', '#2980b9')])

        # 次要按钮样式
        style.configure('Secondary.TButton',
                        font=('微软雅黑', 10, 'bold'),
                        padding=8,
                        background='#2ecc71',
                        foreground='white')

        style.map('Secondary.TButton',
                  background=[('active', '#27ae60')])

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

        why_text = """浏览器扩展是连接 Educoder 助手和头歌平台的桥梁，它可以：
• 自动读取题目要求和测试用例
• 将代码发送到本地服务器进行测试
• 将测试结果返回并显示在页面上
• 实现自动化代码输入和测试功能

没有扩展插件，Educoder 助手将无法正常工作！"""

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

        steps_text = """1. 选择您要安装扩展的浏览器
2. 点击下方"跳转安装扩展"按钮
3. 在新打开的页面中点击"添加扩展"按钮
4. 安装完成后刷新头歌平台页面"""

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
                                text="Google Chrome (推荐)",
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

        warning_text = """ """   # 重要提示

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

        # 跳转安装扩展按钮
        install_button = ttk.Button(
            right_frame,
            text="跳转安装扩展",
            command=self.open_extension_install,
            style='Secondary.TButton',
            cursor='hand2'
        )
        install_button.pack(side='left', padx=5)

        # 我已安装扩展按钮
        self.ok_button = ttk.Button(
            right_frame,
            text="我已安装扩展",
            command=self.on_confirm,
            style='Primary.TButton',
            cursor='hand2'
        )
        self.ok_button.pack(side='left', padx=5)

        # 绑定鼠标滚轮滚动
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # 绑定到Canvas和可滚动框架
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        scrollable_frame.bind_all("<MouseWheel>", on_mousewheel)

        # 确保窗口加载时焦点正确
        self.dialog.after(100, lambda: self.dialog.focus_force())

    def open_extension_install(self):
        """打开扩展安装页面"""
        # 这里可以打开浏览器检测和安装工具，或者直接打开安装页面
        # 由于我们不知道用户具体使用哪个浏览器，可以打开一个通用的引导页面
        # 或者让用户选择浏览器

        # 创建一个简单的选择对话框
        browser_dialog = tk.Toplevel(self.dialog)
        browser_dialog.title("选择浏览器")
        browser_dialog.geometry("400x200")
        browser_dialog.transient(self.dialog)
        browser_dialog.grab_set()

        # 居中显示
        browser_dialog.update_idletasks()
        x = self.dialog.winfo_x() + (self.dialog.winfo_width() - 400) // 2
        y = self.dialog.winfo_y() + (self.dialog.winfo_height() - 200) // 2
        browser_dialog.geometry(f"400x200+{x}+{y}")

        # 内容
        content_frame = ttk.Frame(browser_dialog, padding="20")
        content_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content_frame,
                  text="请选择您要安装扩展的浏览器：",
                  font=('微软雅黑', 11)).pack(pady=(0, 20))

        # Chrome按钮
        chrome_button = ttk.Button(
            content_frame,
            text="Google Chrome",
            command=lambda: self.open_chrome_install(browser_dialog),
            style='Primary.TButton',
            width=20
        )
        chrome_button.pack(pady=5)

        # Edge按钮
        edge_button = ttk.Button(
            content_frame,
            text="Microsoft Edge",
            command=lambda: self.open_edge_install(browser_dialog),
            style='Primary.TButton',
            width=20
        )
        edge_button.pack(pady=5)

        # 取消按钮
        cancel_button = ttk.Button(
            content_frame,
            text="取消",
            command=browser_dialog.destroy,
            width=10
        )
        cancel_button.pack(pady=(10, 0))

    def open_chrome_install(self, browser_dialog):
        """打开Chrome扩展安装页面"""
        browser_dialog.destroy()
        webbrowser.open("http://yhsun.cn/educoder/chrome.html")
        self.show_install_instructions("Chrome")

    def open_edge_install(self, browser_dialog):
        """打开Edge扩展安装页面"""
        browser_dialog.destroy()
        webbrowser.open("http://yhsun.cn/educoder/edge.html")
        self.show_install_instructions("Edge")

    def show_install_instructions(self, browser_name):
        """显示安装完成后的提示"""
        messagebox.showinfo(
            "安装提示",
            f"{browser_name}扩展安装页面已打开！\n\n"
            "请在打开的页面中：\n"
            "1. 点击\"添加扩展\"按钮\n"
            "2. 安装完成后刷新头歌平台页面\n"
            "3. 返回此窗口点击\"我已安装扩展\"按钮",
            parent=self.dialog
        )

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