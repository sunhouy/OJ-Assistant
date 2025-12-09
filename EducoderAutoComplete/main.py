import os
import sys
import tkinter as tk
import winreg

from gui.login_window import LoginWindow


def main():
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()

def set_autostart_windows_registry(app_name, path_to_exe):
    # 打开注册表键
    key = winreg.HKEY_CURRENT_USER
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, app_name, 0, winreg.REG_SZ, path_to_exe)
        winreg.CloseKey(registry_key)
        print(f"已添加注册表开机启动项: {app_name}")
        return True
    except WindowsError as e:
        print(f"注册表操作失败: {e}")
        return False

if __name__ == "__main__":
    app_name = "Educoder助手"
    path_to_exe = os.path.abspath(sys.argv[0])
    set_autostart_windows_registry(app_name, path_to_exe)
    main()