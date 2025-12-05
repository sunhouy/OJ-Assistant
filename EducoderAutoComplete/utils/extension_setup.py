import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import sys
import webbrowser
import tempfile
import json


class ChromeCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chrome浏览器检测工具")
        self.root.geometry("500x500")
        self.root.resizable(False, False)

        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap(default='icon.ico')
        except:
            pass

        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')

        # 主框架
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="Chrome浏览器检测与执行工具",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        # Chrome状态显示区域
        self.status_frame = ttk.LabelFrame(main_frame, text="浏览器状态", padding="15")
        self.status_frame.pack(fill=tk.X, pady=(0, 20))

        self.status_label = ttk.Label(
            self.status_frame,
            text="点击检测按钮检查Chrome安装状态",
            font=("微软雅黑", 10)
        )
        self.status_label.pack()

        # Chrome图标和版本信息
        self.chrome_info_frame = ttk.Frame(self.status_frame)
        self.chrome_info_frame.pack(pady=10)

        # Chrome图标标签（使用文本模拟）
        self.icon_label = ttk.Label(
            self.chrome_info_frame,
            text="⚫",
            font=("Arial", 24),
            foreground="#4285F4"
        )
        self.icon_label.pack(side=tk.LEFT, padx=(0, 10))

        # Chrome信息标签
        self.chrome_info_label = ttk.Label(
            self.chrome_info_frame,
            text="等待检测...",
            font=("微软雅黑", 9)
        )
        self.chrome_info_label.pack(side=tk.LEFT)

        # 要执行的代码输入区域
        code_frame = ttk.LabelFrame(main_frame, text="要执行的JavaScript代码", padding="10")
        code_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # 创建文本输入框和滚动条
        text_frame = ttk.Frame(code_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(text_frame)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # 代码输入文本框
        self.code_text = tk.Text(
            text_frame,
            height=6,
            width=50,
            wrap=tk.NONE,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            font=("Consolas", 10)
        )
        self.code_text.pack(fill=tk.BOTH, expand=True)

        # 配置滚动条
        v_scrollbar.config(command=self.code_text.yview)
        h_scrollbar.config(command=self.code_text.xview)

        # 预置示例代码
        example_code = """// 示例：在控制台输出消息并弹窗
console.log('Chrome浏览器已启动！');
alert('Hello from Chrome!');
console.log('当前URL:', window.location.href);"""

        self.code_text.insert(1.0, example_code)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # 检测按钮
        self.detect_button = ttk.Button(
            button_frame,
            text="🔍 检测Chrome",
            command=self.detect_chrome,
            width=15
        )
        self.detect_button.pack(side=tk.LEFT, padx=(0, 10))

        # 执行按钮
        self.execute_button = ttk.Button(
            button_frame,
            text="🚀 执行代码",
            command=self.execute_code,
            width=15,
            state=tk.DISABLED
        )
        self.execute_button.pack(side=tk.LEFT)

        # 退出按钮
        self.quit_button = ttk.Button(
            button_frame,
            text="退出",
            command=self.root.quit,
            width=10
        )
        self.quit_button.pack(side=tk.RIGHT)

        # 状态栏
        self.status_bar = ttk.Label(
            root,
            text="就绪",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 初始检测
        self.detect_chrome()

    def detect_chrome(self):
        """检测系统是否安装了Chrome浏览器"""
        self.status_bar.config(text="正在检测Chrome浏览器...")
        self.root.update()

        chrome_installed = False
        chrome_path = None
        chrome_version = None

        # Windows中Chrome可能的安装路径
        possible_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]

        # 检查注册表
        try:
            import winreg
            # 检查Chrome在注册表中的安装信息
            reg_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                r"SOFTWARE\Classes\ChromeHTML\shell\open\command"
            ]

            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    chrome_path, _ = winreg.QueryValueEx(key, "")
                    chrome_path = chrome_path.strip('"')
                    if os.path.exists(chrome_path):
                        chrome_installed = True
                        break
                except:
                    pass

            # 尝试从注册表获取版本信息
            if chrome_installed:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                         r"Software\Google\Chrome\BLBeacon")
                    chrome_version, _ = winreg.QueryValueEx(key, "version")
                except:
                    pass
        except ImportError:
            # 如果没有winreg模块（非Windows系统），使用其他方法
            pass

        # 如果注册表没找到，尝试检查常见路径
        if not chrome_installed:
            for path in possible_paths:
                if os.path.exists(path):
                    chrome_installed = True
                    chrome_path = path
                    break

        # 更新UI显示
        if chrome_installed:
            self.icon_label.config(text="✅")
            self.status_label.config(text="Chrome浏览器已安装", foreground="green")

            # 获取版本信息
            if chrome_version:
                info_text = f"Chrome {chrome_version}\n路径: {chrome_path}"
            else:
                info_text = f"Chrome 浏览器\n路径: {chrome_path}"

            self.chrome_info_label.config(text=info_text)
            self.execute_button.config(state=tk.NORMAL)
            self.status_bar.config(text="Chrome浏览器已安装 - 可以执行代码")
        else:
            self.icon_label.config(text="❌")
            self.status_label.config(text="Chrome浏览器未安装", foreground="red")
            self.chrome_info_label.config(text="未找到Chrome浏览器安装")
            self.execute_button.config(state=tk.DISABLED)
            self.status_bar.config(text="Chrome浏览器未安装")

            # 提示用户安装Chrome
            messagebox.showwarning(
                "Chrome未安装",
                "未检测到Chrome浏览器。\n\n是否要下载Chrome？",
                parent=self.root
            )

            # 询问用户是否要打开下载页面
            response = messagebox.askyesno(
                "下载Chrome",
                "是否要打开Chrome下载页面？",
                parent=self.root
            )

            if response:
                webbrowser.open("https://www.google.com/chrome/")

    def execute_code(self):
        """执行代码"""
        # 获取代码
        code = self.code_text.get(1.0, tk.END).strip()

        if not code:
            messagebox.showwarning("警告", "请输入要执行的JavaScript代码！", parent=self.root)
            return

        self.status_bar.config(text="正在执行代码...")
        self.root.update()

        try:
            # 创建临时HTML文件来执行JavaScript代码
            temp_html = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')

            html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chrome代码执行</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #4285F4;
            border-bottom: 2px solid #4285F4;
            padding-bottom: 10px;
        }}
        .code-box {{
            background-color: #f8f9fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            margin: 20px 0;
            font-family: 'Consolas', monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .result {{
            background-color: #e8f5e9;
            border: 1px solid #c8e6c9;
            border-radius: 6px;
            padding: 16px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Chrome代码执行器</h1>
        <p>已成功打开Chrome浏览器并执行以下代码：</p>

        <div class="code-box">
{code}
        </div>

        <div class="result">
            <h3>执行结果：</h3>
            <p id="output">请查看控制台(按F12)查看输出结果</p>
        </div>

        <script>
            // 用户代码开始
            try {{
                console.log("=== 开始执行用户代码 ===");
                console.log("执行时间: " + new Date().toLocaleString());

                {code}

                console.log("=== 用户代码执行完成 ===");

                // 尝试捕获可能的输出显示在页面上
                try {{
                    document.getElementById('output').innerHTML = 
                        '<strong>✅ 代码执行成功！</strong><br>' +
                        '请按F12打开开发者工具查看控制台输出。';
                }} catch(e) {{}}

            }} catch(error) {{
                console.error("代码执行出错: ", error);
                document.getElementById('output').innerHTML = 
                    '<strong>❌ 代码执行出错：</strong><br>' + error.toString();
            }}
        </script>
    </div>
</body>
</html>"""

            temp_html.write(html_content)
            temp_html.close()

            # 尝试用Chrome打开
            try:
                # 首先尝试通过注册表找到的路径
                chrome_path = None
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                         r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
                    chrome_path, _ = winreg.QueryValueEx(key, "")
                    chrome_path = chrome_path.strip('"')
                except:
                    pass

                if chrome_path and os.path.exists(chrome_path):
                    subprocess.Popen([chrome_path, temp_html.name])
                else:
                    # 如果找不到具体路径，使用默认浏览器打开
                    webbrowser.open(f"file:///{temp_html.name}")

                self.status_bar.config(text="✅ 代码执行成功 - 已打开Chrome浏览器")
                messagebox.showinfo(
                    "执行成功",
                    "代码执行成功！\n\nChrome浏览器已打开并执行您的JavaScript代码。\n按F12打开开发者工具查看控制台输出。",
                    parent=self.root
                )

            except Exception as e:
                self.status_bar.config(text=f"❌ 打开Chrome失败: {str(e)}")
                messagebox.showerror(
                    "执行错误",
                    f"打开Chrome浏览器时出错：\n{str(e)}",
                    parent=self.root
                )

        except Exception as e:
            self.status_bar.config(text=f"❌ 执行失败: {str(e)}")
            messagebox.showerror(
                "执行错误",
                f"执行代码时出错：\n{str(e)}",
                parent=self.root
            )


def main():
    root = tk.Tk()
    app = ChromeCheckerApp(root)

    # 居中显示窗口
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()