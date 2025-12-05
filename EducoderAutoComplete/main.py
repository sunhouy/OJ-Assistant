import tkinter as tk
import sys
import os
import platform
import winreg
import json
from pathlib import Path
from gui.login_window import LoginWindow


class AutoStartManager:
    """Windows开机自启动管理器"""

    def __init__(self):
        self.app_name = "MyAppLogin"
        self.reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        self.config_file = self._get_config_path()

    def _get_config_path(self):
        """获取配置文件路径"""
        config_dir = os.path.join(os.path.expanduser("~"), ".myapp")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "config.json")

    def _get_app_path(self):
        """获取应用程序路径"""
        # 如果是打包后的exe
        if getattr(sys, 'frozen', False):
            return sys.executable
        # 如果是Python脚本
        else:
            return os.path.abspath(sys.argv[0])

    def is_auto_start_enabled(self):
        """检查是否已启用开机自启动"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 self.reg_path,
                                 0,
                                 winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                return bool(value)
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def enable_auto_start(self):
        """启用开机自启动"""
        try:
            app_path = self._get_app_path()

            # 如果是Python脚本，需要确保使用pythonw.exe运行以避免显示控制台窗口
            if app_path.endswith('.py'):
                pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
                command = f'"{pythonw_path}" "{app_path}"'
            else:
                command = f'"{app_path}"'

            # 写入注册表
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 self.reg_path,
                                 0,
                                 winreg.KEY_WRITE)
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)

            # 保存配置
            self._save_config(True)
            return True
        except Exception as e:
            print(f"启用自启动失败: {e}")
            return False

    def disable_auto_start(self):
        """禁用开机自启动"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 self.reg_path,
                                 0,
                                 winreg.KEY_WRITE)
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)

            # 保存配置
            self._save_config(False)
            return True
        except Exception as e:
            print(f"禁用自启动失败: {e}")
            return False

    def _save_config(self, enabled):
        """保存配置到文件"""
        config = {"auto_start": enabled}
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception:
            pass

    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get("auto_start", False)
        except Exception:
            pass
        return False


def create_settings_window():
    """创建设置窗口用于管理自启动"""

    def toggle_auto_start():
        if auto_start_manager.is_auto_start_enabled():
            if auto_start_manager.disable_auto_start():
                status_label.config(text="状态: 已禁用", fg="red")
                toggle_btn.config(text="启用开机自启动")
        else:
            if auto_start_manager.enable_auto_start():
                status_label.config(text="状态: 已启用", fg="green")
                toggle_btn.config(text="禁用开机自启动")

    settings_window = tk.Toplevel()
    settings_window.title("开机自启动设置")
    settings_window.geometry("400x200")
    settings_window.resizable(False, False)

    # 居中显示
    settings_window.update_idletasks()
    width = settings_window.winfo_width()
    height = settings_window.winfo_height()
    x = (settings_window.winfo_screenwidth() // 2) - (width // 2)
    y = (settings_window.winfo_screenheight() // 2) - (height // 2)
    settings_window.geometry(f'{width}x{height}+{x}+{y}')

    auto_start_manager = AutoStartManager()

    # 标题
    title_label = tk.Label(settings_window, text="开机自启动设置",
                           font=("Arial", 16, "bold"))
    title_label.pack(pady=20)

    # 状态显示
    status_text = "状态: 已启用" if auto_start_manager.is_auto_start_enabled() else "状态: 已禁用"
    status_color = "green" if auto_start_manager.is_auto_start_enabled() else "red"
    status_label = tk.Label(settings_window, text=status_text,
                            font=("Arial", 12), fg=status_color)
    status_label.pack(pady=10)

    # 切换按钮
    toggle_text = "禁用开机自启动" if auto_start_manager.is_auto_start_enabled() else "启用开机自启动"
    toggle_btn = tk.Button(settings_window, text=toggle_text,
                           command=toggle_auto_start,
                           font=("Arial", 12), width=20, height=2)
    toggle_btn.pack(pady=20)

    # 说明文字
    info_text = "启用后，程序将在Windows启动时自动运行"
    info_label = tk.Label(settings_window, text=info_text,
                          font=("Arial", 9), fg="gray")
    info_label.pack(pady=5)


def main():
    root = tk.Tk()

    # 可以在登录窗口前初始化自启动管理器
    auto_start_manager = AutoStartManager()

    # 如果需要程序启动时自动检查并启用自启动，取消下面的注释
    # if not auto_start_manager.is_auto_start_enabled():
    #     auto_start_manager.enable_auto_start()

    app = LoginWindow(root)

    # 假设LoginWindow有一个菜单或按钮可以打开设置窗口
    # 这里演示如何从主窗口添加一个设置按钮
    # 您可能需要根据实际界面调整

    # 方法1：添加一个设置按钮到主窗口（如果LoginWindow允许）
    # settings_btn = tk.Button(root, text="⚙", command=create_settings_window)
    # settings_btn.pack(side="top", anchor="ne")

    root.mainloop()


if __name__ == '__main__':
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--enable-autostart":
            manager = AutoStartManager()
            manager.enable_auto_start()
            print("已启用开机自启动")
            sys.exit(0)
        elif sys.argv[1] == "--disable-autostart":
            manager = AutoStartManager()
            manager.disable_auto_start()
            print("已禁用开机自启动")
            sys.exit(0)
        elif sys.argv[1] == "--settings":
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            create_settings_window()
            root.mainloop()
            sys.exit(0)

    main()