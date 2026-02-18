import tkinter as tk
import winreg

from gui.login_window import LoginWindow


def set_autostart_windows_registry(app_name, path_to_exe, enable=True):
    """设置或删除开机自启注册表项"""
    # 打开注册表键
    key = winreg.HKEY_CURRENT_USER
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        if enable:
            # 设置开机自启
            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, app_name, 0, winreg.REG_SZ, path_to_exe)
            winreg.CloseKey(registry_key)
            print(f"已添加注册表开机启动项: {app_name}")
            return True
        else:
            # 删除开机自启
            try:
                registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE)
                winreg.DeleteValue(registry_key, app_name)
                winreg.CloseKey(registry_key)
                print(f"已删除注册表开机启动项: {app_name}")
                return True
            except WindowsError as e:
                # 如果值不存在，忽略错误
                if e.errno == 2:  # 文件不存在
                    print(f"注册表项不存在: {app_name}")
                    return True
                else:
                    raise
    except WindowsError as e:
        print(f"注册表操作失败: {e}")
        return False


def check_autostart_enabled(app_name):
    """检查是否已设置开机自启"""
    key = winreg.HKEY_CURRENT_USER
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_READ)
        try:
            value, regtype = winreg.QueryValueEx(registry_key, app_name)
            winreg.CloseKey(registry_key)
            return True
        except WindowsError:
            winreg.CloseKey(registry_key)
            return False
    except WindowsError:
        return False


def main():
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    app_name = "Educoder助手"
    # path_to_exe = os.path.abspath(sys.argv[0])
    # set_autostart_windows_registry(app_name, path_to_exe)  # 设置开机自启
    main()