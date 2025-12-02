import tkinter as tk
from tkinter import ttk
import configparser
import os


class FirstRunDialog:
    def __init__(self, parent):
        self.ok_button = None
        self.parent = parent
        self.dont_show_again = tk.BooleanVar(value=False)

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("使用指南")
        self.dialog.geometry("800x800")
        # 设置背景色为白色
        self.dialog.configure(bg='white')
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 设置窗口最小尺寸
        self.dialog.minsize(700, 550)

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
        # 更换主题，使用Windows默认主题以显示正确的复选框
        try:
            style.theme_use('vista')
        except:
            style.theme_use('winnative')

        # 设置全局背景色为白色
        style.configure('.', background='white')

        # 配置标题标签
        style.configure('Title.TLabel',
                        font=('微软雅黑', 16, 'bold'),
                        background='white',
                        foreground='#2c3e50')

        style.configure('Section.TLabel',
                        font=('微软雅黑', 11, 'bold'),
                        background='white',
                        foreground='#3498db')

        style.configure('Normal.TLabel',
                        font=('微软雅黑', 10),
                        background='white',
                        foreground='#34495e',
                        wraplength=700)

        style.configure('Warning.TLabel',
                        font=('微软雅黑', 10),
                        background='white',
                        foreground='#e74c3c',
                        padding=10)

        style.configure('Modern.TButton',
                        font=('微软雅黑', 10, 'bold'),
                        padding=8,
                        background='#3498db',
                        foreground='black')

        style.map('Modern.TButton',
                  background=[('active', '#2980b9')])

        # 配置复选框样式 - 使用Windows默认样式
        style.configure('Custom.TCheckbutton',
                        font=('微软雅黑', 11, 'bold'),
                        background='white',
                        foreground='#2c3e50')

    def setup_ui(self):
        """设置对话框界面"""
        # 主框架 - 白色背景
        main_frame = ttk.Frame(self.dialog, padding="25")
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

        # 欢迎标题
        title_label = ttk.Label(
            scrollable_frame,
            text="欢迎使用本应用 - 使用指南",
            style='Title.TLabel'
        )
        title_label.pack(pady=(0, 15), anchor='center')

        # 提示信息
        intro_text = """您好！

为了您能更好地使用本应用，请您务必完整阅读以下所有内容。"""

        intro_label = ttk.Label(
            scrollable_frame,
            text=intro_text,
            style='Normal.TLabel'
        )
        intro_label.pack(pady=(0, 20), anchor='w')

        # 浏览器插件安装部分
        section1_label = ttk.Label(
            scrollable_frame,
            text="浏览器插件安装方法",
            style='Section.TLabel'
        )
        section1_label.pack(pady=(0, 10), anchor='w')

        install_text = """1. 打开 Chrome 或 Edge 浏览器
2. 点击右上角三个点 → 扩展程序 → 管理扩展程序
3. 开启右上角的"开发者模式"
4. 点击"加载已解压的扩展程序"
5. 选择本应用目录下的 Chrome 文件夹
6. 确保扩展程序处于启用状态
7. 打开头歌平台答题界面，扩展主界面将会显示
8. 点击本应用的"启动服务器"按钮启动服务器"""

        install_frame = ttk.Frame(scrollable_frame)
        install_frame.pack(pady=(0, 20), fill='x')

        for i, line in enumerate(install_text.split('\n')):
            line_frame = ttk.Frame(install_frame)
            line_frame.pack(fill='x', pady=2)

            # 文本内容 - 移除左侧蓝点，直接显示文本
            text_label = ttk.Label(line_frame,
                                   text=line,
                                   style='Normal.TLabel',
                                   justify='left')
            text_label.pack(anchor='w')

        # 注意事项部分
        section2_label = ttk.Label(
            scrollable_frame,
            text="重要注意事项",
            style='Section.TLabel'
        )
        section2_label.pack(pady=(0, 10), anchor='w')

        notes_text = [
            "请勿使用搜狗输入法等第三方输入法，这些输入法会干扰代码输入。",
            "请使用 Windows 自带的微软拼音输入法，并提前切换至英文状态。",
            "代码输入过程中请勿切换界面，如需停止请将鼠标快速移至屏幕角落。",
            "如出现括号不对齐或多出大括号的情况，请自行检查修正代码。"
        ]

        notes_frame = ttk.Frame(scrollable_frame)
        notes_frame.pack(pady=(0, 20), fill='x')

        for note in notes_text:
            note_frame = ttk.Frame(notes_frame)
            note_frame.pack(fill='x', pady=3)

            # 警告图标 - 使用tk.Label确保白色背景
            warn_label = tk.Label(note_frame,
                                  text="●",
                                  font=('微软雅黑', 10),
                                  bg='white',
                                  fg='#e74c3c')
            warn_label.pack(side='left', padx=(0, 10))

            # 文本内容
            note_label = ttk.Label(note_frame,
                                   text=note,
                                   style='Normal.TLabel',
                                   justify='left')
            note_label.pack(side='left', anchor='w')

        # 警告部分
        warning_text = """警告：本应用仅供学习交流使用，不得用于商业和非法用途。
如您使用本应用造成账号封禁、处分、退学等后果，开发者不承担任何责任！"""

        warning_label = ttk.Label(scrollable_frame,
                                  text=warning_text,
                                  style='Warning.TLabel',
                                  justify='center',
                                  wraplength=650)
        warning_label.pack(pady=20, fill='x')

        # 底部按钮区域
        bottom_frame = ttk.Frame(scrollable_frame)
        bottom_frame.pack(fill='x', pady=(20, 0))

        # 左侧复选框
        left_frame = ttk.Frame(bottom_frame)
        left_frame.pack(side='left')

        # 创建复选框 - 使用Windows默认主题以显示正确的对钩
        self.checkbox = ttk.Checkbutton(
            left_frame,
            text="不再显示此提示",
            variable=self.dont_show_again,
            style='Custom.TCheckbutton'
        )
        self.checkbox.pack(side='left', padx=5)

        # 右侧按钮
        right_frame = ttk.Frame(bottom_frame)
        right_frame.pack(side='right')

        # 创建确定按钮时保存引用
        self.ok_button = ttk.Button(
            right_frame,
            text="我已阅读并同意",
            command=self.on_confirm,
            style='Modern.TButton',
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

    def on_confirm(self):
        """确定按钮点击事件"""
        # 保存设置
        config = configparser.ConfigParser()
        config['SETTINGS'] = {
            'show_welcome': str(not self.dont_show_again.get())
        }

        try:
            with open('config.ini', 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        except Exception as e:
            print(f"保存配置失败: {e}")

        self.dialog.destroy()