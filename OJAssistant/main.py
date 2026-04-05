import os
import platform
import shlex
import sys
from pathlib import Path

import tkinter as tk

try:
    import winreg
except ImportError:
    winreg = None

from gui.login_window import LoginWindow


def set_autostart_windows_registry(app_name, path_to_exe, enable=True):
    """设置或删除开机自启项，Windows 使用注册表，Linux 使用 XDG autostart。"""
    if platform.system() == "Windows" and winreg is not None:
        return _set_windows_autostart(app_name, path_to_exe, enable)

    if platform.system() == "Linux":
        return _set_linux_autostart(app_name, path_to_exe, enable)

    print(f"当前系统不支持开机自启: {platform.system()}")
    return False


def _set_windows_autostart(app_name, path_to_exe, enable=True):
    """设置或删除 Windows 注册表开机自启项。"""
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
            except OSError as e:
                # 如果值不存在，忽略错误
                if getattr(e, "errno", None) == 2:
                    print(f"注册表项不存在: {app_name}")
                    return True
                else:
                    raise
    except OSError as e:
        print(f"注册表操作失败: {e}")
        return False


def _get_linux_autostart_dir():
    return Path.home() / ".config" / "autostart"


def _get_linux_desktop_file(app_name):
    safe_name = "oj-assistant.desktop"
    return _get_linux_autostart_dir() / safe_name


def _build_launch_command(path_to_exe):
    executable_path = Path(path_to_exe)
    if executable_path.suffix == ".py" and executable_path.exists():
        return f"{shlex.quote(sys.executable)} {shlex.quote(str(executable_path))}"
    return shlex.quote(str(executable_path))


def _set_linux_autostart(app_name, path_to_exe, enable=True):
    """设置或删除 Linux XDG autostart 文件。"""
    desktop_file = _get_linux_desktop_file(app_name)

    try:
        if enable:
            desktop_file.parent.mkdir(parents=True, exist_ok=True)
            exec_command = _build_launch_command(path_to_exe)
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={app_name}\n"
                f"Exec={exec_command}\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            desktop_file.write_text(content, encoding="utf-8")
            print(f"已添加 Linux 开机启动项: {desktop_file}")
            return True

        if desktop_file.exists():
            desktop_file.unlink()
            print(f"已删除 Linux 开机启动项: {desktop_file}")
        else:
            print(f"Linux 开机启动项不存在: {desktop_file}")
        return True
    except OSError as e:
        print(f"Linux 开机自启设置失败: {e}")
        return False


def check_autostart_enabled(app_name):
    """检查是否已设置开机自启。"""
    if platform.system() == "Windows" and winreg is not None:
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(registry_key, app_name)
                winreg.CloseKey(registry_key)
                return True
            except OSError:
                winreg.CloseKey(registry_key)
                return False
        except OSError:
            return False

    if platform.system() == "Linux":
        return _get_linux_desktop_file(app_name).exists()

    return False


def main():
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    app_name = "OJ助手"
    # path_to_exe = os.path.abspath(sys.argv[0])
    # set_autostart_windows_registry(app_name, path_to_exe)  # 设置开机自启
    main()