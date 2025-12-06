import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import sys
import webbrowser
import tempfile
import json
import winreg


class BrowserCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("浏览器检测与扩展安装工具")
        self.root.geometry("500x550")
        self.root.resizable(True, True)

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
            text="浏览器检测与扩展安装工具",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        # 浏览器状态显示区域
        self.status_frame = ttk.LabelFrame(main_frame, text="浏览器检测结果", padding="15")
        self.status_frame.pack(fill=tk.X, pady=(0, 20))

        # Chrome状态
        self.chrome_frame = ttk.Frame(self.status_frame)
        self.chrome_frame.pack(fill=tk.X, pady=(0, 10))

        self.chrome_icon_label = ttk.Label(
            self.chrome_frame,
            text="⚫",
            font=("Arial", 20),
            foreground="#4285F4"
        )
        self.chrome_icon_label.pack(side=tk.LEFT, padx=(0, 10))

        self.chrome_info_frame = ttk.Frame(self.chrome_frame)
        self.chrome_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.chrome_status_label = ttk.Label(
            self.chrome_info_frame,
            text="Chrome浏览器",
            font=("微软雅黑", 10, "bold")
        )
        self.chrome_status_label.pack(anchor=tk.W)

        self.chrome_detail_label = ttk.Label(
            self.chrome_info_frame,
            text="等待检测...",
            font=("微软雅黑", 9)
        )
        self.chrome_detail_label.pack(anchor=tk.W)

        # Edge状态
        self.edge_frame = ttk.Frame(self.status_frame)
        self.edge_frame.pack(fill=tk.X)

        self.edge_icon_label = ttk.Label(
            self.edge_frame,
            text="⚫",
            font=("Arial", 20),
            foreground="#0078D7"
        )
        self.edge_icon_label.pack(side=tk.LEFT, padx=(0, 10))

        self.edge_info_frame = ttk.Frame(self.edge_frame)
        self.edge_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.edge_status_label = ttk.Label(
            self.edge_info_frame,
            text="Edge浏览器",
            font=("微软雅黑", 10, "bold")
        )
        self.edge_status_label.pack(anchor=tk.W)

        self.edge_detail_label = ttk.Label(
            self.edge_info_frame,
            text="等待检测...",
            font=("微软雅黑", 9)
        )
        self.edge_detail_label.pack(anchor=tk.W)

        # 扩展安装选择区域
        self.install_frame = ttk.LabelFrame(main_frame, text="扩展安装选项", padding="10")
        self.install_frame.pack(fill=tk.X, pady=(0, 20))

        # 浏览器选择标签
        ttk.Label(
            self.install_frame,
            text="选择要安装扩展的浏览器:",
            font=("微软雅黑", 9)
        ).pack(anchor=tk.W, pady=(0, 5))

        # 浏览器选择下拉框
        self.browser_var = tk.StringVar(value="请选择浏览器")
        self.browser_combo = ttk.Combobox(
            self.install_frame,
            textvariable=self.browser_var,
            state="readonly",
            font=("微软雅黑", 10),
            width=25
        )
        self.browser_combo.pack(anchor=tk.W, pady=(0, 10))

        # 安装URL显示
        self.url_frame = ttk.Frame(self.install_frame)
        self.url_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            self.url_frame,
            text="安装页面:",
            font=("微软雅黑", 9)
        ).pack(side=tk.LEFT)

        self.url_label = ttk.Label(
            self.url_frame,
            text="请先选择浏览器",
            font=("微软雅黑", 9),
            foreground="#0078D7"
        )
        self.url_label.pack(side=tk.LEFT, padx=(5, 0))

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # 检测按钮
        self.detect_button = ttk.Button(
            button_frame,
            text="🔍 检测浏览器",
            command=self.detect_browsers,
            width=15
        )
        self.detect_button.pack(side=tk.LEFT, padx=(0, 10))

        # 安装按钮
        self.install_button = ttk.Button(
            button_frame,
            text="🚀 立即安装",
            command=self.install_extension,
            width=15,
            state=tk.DISABLED
        )
        self.install_button.pack(side=tk.LEFT, padx=(0, 10))

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

        # 存储浏览器信息
        self.browsers = {
            "chrome": {"installed": False, "path": None, "version": None},
            "edge": {"installed": False, "path": None, "version": None}
        }

        # 安装URL映射
        self.install_urls = {
            "chrome": "http://yhsun.cn/educoder/chrome.html",
            "edge": "http://yhsun.cn/educoder/edge.html"
        }

        # 初始检测
        self.detect_browsers()

    def detect_browsers(self):
        """检测Chrome和Edge浏览器"""
        self.status_bar.config(text="正在检测浏览器...")
        self.root.update()

        # 重置浏览器状态
        self.browsers = {
            "chrome": {"installed": False, "path": None, "version": None},
            "edge": {"installed": False, "path": None, "version": None}
        }

        # 检测Chrome
        self.detect_chrome()

        # 检测Edge
        self.detect_edge()

        # 更新UI显示
        self.update_browser_display()

        # 更新下拉选择框
        self.update_browser_combo()

        # 更新状态栏
        installed_count = sum(1 for b in self.browsers.values() if b["installed"])
        self.status_bar.config(text=f"检测完成：找到 {installed_count} 个浏览器")

    def detect_chrome(self):
        """检测Chrome浏览器"""
        chrome_installed = False
        chrome_path = None
        chrome_version = None

        try:
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
                        continue

                # 尝试从注册表获取版本信息
                if chrome_installed:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                             r"Software\Google\Chrome\BLBeacon")
                        chrome_version, _ = winreg.QueryValueEx(key, "version")
                    except:
                        pass
            except:
                pass

            # 如果注册表没找到，尝试检查常见路径
            if not chrome_installed:
                for path in possible_paths:
                    if os.path.exists(path):
                        chrome_installed = True
                        chrome_path = path
                        break

            # 保存Chrome信息
            self.browsers["chrome"]["installed"] = chrome_installed
            self.browsers["chrome"]["path"] = chrome_path
            self.browsers["chrome"]["version"] = chrome_version

        except Exception as e:
            print(f"检测Chrome时出错: {e}")

    def detect_edge(self):
        """检测Edge浏览器"""
        edge_installed = False
        edge_path = None
        edge_version = None

        try:
            # Windows中Edge可能的安装路径
            possible_paths = [
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            ]

            # 检查注册表
            try:
                # 检查Edge在注册表中的安装信息
                reg_paths = [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                    r"SOFTWARE\Classes\MSEdgeHTM\shell\open\command"
                ]

                for reg_path in reg_paths:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                        edge_path, _ = winreg.QueryValueEx(key, "")
                        edge_path = edge_path.strip('"')
                        if os.path.exists(edge_path):
                            edge_installed = True
                            break
                    except:
                        continue

                # 尝试从注册表获取版本信息
                if edge_installed:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                             r"Software\Microsoft\Edge\BLBeacon")
                        edge_version, _ = winreg.QueryValueEx(key, "version")
                    except:
                        pass
            except:
                pass

            # 如果注册表没找到，尝试检查常见路径
            if not edge_installed:
                for path in possible_paths:
                    if os.path.exists(path):
                        edge_installed = True
                        edge_path = path
                        break

            # 保存Edge信息
            self.browsers["edge"]["installed"] = edge_installed
            self.browsers["edge"]["path"] = edge_path
            self.browsers["edge"]["version"] = edge_version

        except Exception as e:
            print(f"检测Edge时出错: {e}")

    def update_browser_display(self):
        """更新浏览器状态显示"""
        # 更新Chrome显示
        chrome_info = self.browsers["chrome"]
        if chrome_info["installed"]:
            self.chrome_icon_label.config(text="✅")
            self.chrome_status_label.config(text="Chrome浏览器 (已安装)", foreground="green")

            if chrome_info["version"]:
                self.chrome_detail_label.config(
                    text=f"版本: {chrome_info['version']}\n路径: {chrome_info['path']}"
                )
            else:
                self.chrome_detail_label.config(
                    text=f"Chrome浏览器\n路径: {chrome_info['path']}"
                )
        else:
            self.chrome_icon_label.config(text="❌")
            self.chrome_status_label.config(text="Chrome浏览器 (未安装)", foreground="red")
            self.chrome_detail_label.config(text="未找到Chrome浏览器安装")

        # 更新Edge显示
        edge_info = self.browsers["edge"]
        if edge_info["installed"]:
            self.edge_icon_label.config(text="✅")
            self.edge_status_label.config(text="Edge浏览器 (已安装)", foreground="green")

            if edge_info["version"]:
                self.edge_detail_label.config(
                    text=f"版本: {edge_info['version']}\n路径: {edge_info['path']}"
                )
            else:
                self.edge_detail_label.config(
                    text=f"Edge浏览器\n路径: {edge_info['path']}"
                )
        else:
            self.edge_icon_label.config(text="❌")
            self.edge_status_label.config(text="Edge浏览器 (未安装)", foreground="red")
            self.edge_detail_label.config(text="未找到Edge浏览器安装")

    def update_browser_combo(self):
        """更新浏览器选择下拉框"""
        installed_browsers = []

        if self.browsers["chrome"]["installed"]:
            installed_browsers.append("Chrome浏览器")

        if self.browsers["edge"]["installed"]:
            installed_browsers.append("Edge浏览器")

        if installed_browsers:
            self.browser_combo['values'] = installed_browsers
            if len(installed_browsers) == 1:
                self.browser_var.set(installed_browsers[0])
                self.on_browser_select(None)  # 自动选择
        else:
            self.browser_combo['values'] = []
            self.browser_var.set("未找到可用浏览器")

        # 绑定选择事件
        self.browser_combo.bind("<<ComboboxSelected>>", self.on_browser_select)

    def on_browser_select(self, event):
        """浏览器选择事件处理"""
        selected = self.browser_var.get()

        if selected == "Chrome浏览器":
            self.url_label.config(text=self.install_urls["chrome"])
            self.install_button.config(state=tk.NORMAL)
        elif selected == "Edge浏览器":
            self.url_label.config(text=self.install_urls["edge"])
            self.install_button.config(state=tk.NORMAL)
        else:
            self.url_label.config(text="请先选择浏览器")
            self.install_button.config(state=tk.DISABLED)

    def install_extension(self):
        """安装扩展"""
        selected = self.browser_var.get()

        if selected == "Chrome浏览器":
            url = self.install_urls["chrome"]
            browser_name = "Chrome"
        elif selected == "Edge浏览器":
            url = self.install_urls["edge"]
            browser_name = "Edge"
        else:
            messagebox.showwarning("警告", "请先选择浏览器！", parent=self.root)
            return

        # 询问确认
        response = messagebox.askyesno(
            "确认安装",
            f"即将打开{browser_name}浏览器的扩展安装页面。\n\n是否继续？",
            parent=self.root
        )

        if response:
            self.status_bar.config(text=f"正在打开{browser_name}扩展安装页面...")
            try:
                webbrowser.open(url)
                self.status_bar.config(text=f"✅ 已打开{browser_name}扩展安装页面")
                messagebox.showinfo(
                    "成功",
                    f"{browser_name}扩展安装页面已打开！\n\n请按照页面指示完成安装。",
                    parent=self.root
                )
            except Exception as e:
                self.status_bar.config(text=f"❌ 打开页面失败: {str(e)}")
                messagebox.showerror(
                    "错误",
                    f"无法打开安装页面：\n{str(e)}",
                    parent=self.root
                )


def main():
    root = tk.Tk()
    app = BrowserCheckerApp(root)

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