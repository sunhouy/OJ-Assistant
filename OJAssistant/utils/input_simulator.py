import time
import platform
import os
import shutil
import subprocess
from tkinter import messagebox

import keyboard
import pyautogui
import pyperclip


class InputSimulator:
    def __init__(self, gui):
        self.gui = gui
        self.typing_active = True
        self.left_brace_count = 0
        self.line_count = 0
        self.esc_pressed = False
        self.esc_hook = None
        self.is_linux = platform.system() == "Linux"
        self.xdotool_path = shutil.which("xdotool") if self.is_linux else None
        self.xdotool_available = bool(self.xdotool_path)

    def _check_xdotool_environment(self):
        """检查Linux下xdotool可用性与会话环境。"""
        if not self.is_linux:
            return True

        if not self.xdotool_available:
            self.gui.log("检测到Linux环境但未安装xdotool，无法执行自动输入")
            self.gui.log("请先安装xdotool: sudo apt install xdotool")
            return False

        session_type = os.getenv("XDG_SESSION_TYPE", "").lower()
        if session_type == "wayland":
            self.gui.log("当前是Wayland会话，xdotool通常无法控制键盘输入")
            self.gui.log("请切换到X11会话，或使用支持Wayland的输入工具")
            return False

        display = os.getenv("DISPLAY")
        if not display:
            self.gui.log("未检测到DISPLAY环境变量，xdotool无法连接图形会话")
            return False

        try:
            result = subprocess.run(
                [self.xdotool_path, "getactivewindow"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            window_id = result.stdout.strip()
            if not window_id:
                self.gui.log("未检测到激活窗口，请先激活目标编辑器窗口")
                return False
        except Exception as e:
            self.gui.log(f"无法获取当前激活窗口，自动输入无法开始: {e}")
            return False

        return True

    def reset(self):
        """重置状态"""
        self.typing_active = True
        self.left_brace_count = 0
        self.line_count = 0
        self.esc_pressed = False

    def set_esc_pressed(self, event=None):
        """设置ESC键按下标志"""
        if not self.esc_pressed:  # 避免重复触发
            self.esc_pressed = True
            self.typing_active = False

    def _install_esc_hook(self):
        """安装ESC监听（失败时降级，不中断主流程）。"""
        self._remove_esc_hook()
        try:
            self.esc_hook = keyboard.on_press_key('esc', self.set_esc_pressed, suppress=False)
        except Exception as e:
            self.esc_hook = None
            self.gui.log(f"ESC全局监听不可用，将继续输入但无法ESC中止: {e}")

    def _remove_esc_hook(self):
        """移除当前实例安装的ESC监听。"""
        if self.esc_hook is not None:
            try:
                keyboard.unhook(self.esc_hook)
            except Exception:
                pass
            self.esc_hook = None

    def _write_text(self, text):
        """Linux优先使用xdotool输入，其他平台使用keyboard。"""
        if self.is_linux and self.xdotool_available:
            self._xdotool_type(text)
            return

        try:
            keyboard.write(text)
        except Exception as e:
            if self.is_linux:
                raise RuntimeError(f"keyboard输入失败，且xdotool不可用: {e}")
            pyautogui.write(text, interval=0)

    def _press_key(self, key):
        """按键封装：Linux优先xdotool。"""
        if self.is_linux and self.xdotool_available:
            self._xdotool_key(key)
            return

        try:
            keyboard.press_and_release(key)
            return
        except Exception as e:
            if self.is_linux:
                raise RuntimeError(f"keyboard按键失败，且xdotool不可用: {e}")
            pass

        if '+' in key:
            pyautogui.hotkey(*key.split('+'))
        else:
            pyautogui.press(key)

    def _xdotool_type(self, text):
        """使用xdotool输入文本。"""
        subprocess.run(
            [self.xdotool_path, "type", "--clearmodifiers", "--delay", "1", "--", text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _xdotool_key(self, key):
        """使用xdotool发送按键。"""
        xdotool_key = key.replace('+', '+')
        subprocess.run(
            [self.xdotool_path, "key", "--clearmodifiers", xdotool_key],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _clear_editor_before_input(self):
        """在输入前清空当前编辑器内容，避免旧代码残留。"""
        try:
            self._press_key('ctrl+a')
            time.sleep(0.05)
            self._press_key('delete')
            time.sleep(0.05)
            return True
        except Exception as e:
            self.gui.log(f"清空编辑器失败: {e}")
            return False

    def paste_code(self, code):
        """使用复制粘贴方式输入代码"""
        try:
            if not self._check_xdotool_environment():
                return False

            # 安装ESC键监听
            self._install_esc_hook()

            # 输入前先清空编辑器
            self._clear_editor_before_input()

            # 激活编辑器（点击屏幕中央）
            """
            screen_width, screen_height = pyautogui.size()
            x = screen_width // 2
            y = screen_height // 2
            pyautogui.click(x=x, y=y)
            time.sleep(0.05)

            # 清空编辑器内容
            keyboard.press_and_release('ctrl+a')
            time.sleep(0.05)
            keyboard.press_and_release('delete')
            time.sleep(0.05)
            """

            # 检查ESC键
            if self.esc_pressed:
                self.gui.log("用户按下了ESC键，终止代码粘贴")
                # self._show_termination_message()
                self._remove_esc_hook()
                return False

            pasted = False
            try:
                # 复制代码到剪贴板并粘贴
                pyperclip.copy(code)
                time.sleep(0.05)
                self._press_key('ctrl+v')
                time.sleep(0.05)
                pasted = True
                self.gui.log("代码已通过复制粘贴完成输入")
            except Exception as e:
                # Linux下一些环境中剪贴板不可用，回退到直接输入
                self.gui.log(f"复制粘贴不可用，回退到直接输入: {e}")

            if not pasted:
                self._write_text(code)
                self.gui.log("代码已通过xdotool直接输入完成")

            # 移除ESC键监听
            self._remove_esc_hook()

            return True

        except Exception as e:
            self.gui.log(f"复制粘贴失败: {e}")
            self._remove_esc_hook()
            return False

    def simulate_typing(self, text, is_first_chunk=False):
        """模拟键盘输入代码"""
        try:
            if not self._check_xdotool_environment():
                return False

            # 如果是第一个块，开始模拟键盘输入
            if is_first_chunk:
                self.gui.log("开始模拟键盘输入代码...")
                self.line_count = 0
                self.esc_pressed = False

                # 安装ESC键监听
                self._install_esc_hook()

                # 检查ESC键
                if self.esc_pressed:
                    self.gui.log("用户按下了ESC键，终止代码输入")
                    # self._show_termination_message()
                    self._remove_esc_hook()
                    return False

                # 输入前先清空编辑器
                self._clear_editor_before_input()
                """
                # 激活编辑器（点击屏幕中央）
                screen_width, screen_height = pyautogui.size()
                x = screen_width // 2
                y = screen_height // 2
                pyautogui.click(x=x, y=y)
                time.sleep(0.05)

                # 清空编辑器内容
                keyboard.press_and_release('ctrl+a')
                time.sleep(0.05)
                keyboard.press_and_release('delete')
                time.sleep(0.05)
                """

            # 使用批量输入
            lines = text.split('\n')
            for line_index, line in enumerate(lines):
                # 检查ESC键
                if self.esc_pressed:
                    self.gui.log("用户按下了ESC键，终止代码输入")
                    # self._show_termination_message()
                    self._remove_esc_hook()
                    return False

                # 处理当前行：按原文本逐字符含空白输入，避免人为改缩进
                if line:
                    self._write_text(line)

                # 如果是最后一行且为空行，不需要处理
                # 如果不是最后一行，添加换行
                if line_index < len(lines) - 1:
                    self._press_key('enter')
                    time.sleep(0.05)  # 换行后的短暂等待

                # 记录行数（包括空行）
                if line_index < len(lines) - 1:
                    self.line_count += 1

            return True

        except Exception as e:
            self.gui.log(f"模拟键盘输入失败: {e}")
            if self.is_linux:
                self.gui.log("Linux自动输入依赖xdotool和目标窗口焦点，请确认已安装xdotool且编辑器窗口处于激活状态")
            else:
                self.gui.log("输入环境异常，可能与全局键盘权限或焦点有关；已尝试自动回退输入方式")
            self._remove_esc_hook()
            return False

    def finalize_formatting(self):
        """完成代码输入后的格式化操作"""
        try:
            self.gui.log(f"代码输入完成，共处理了{self.line_count}行")
            # 移除ESC键监听
            self._remove_esc_hook()
            self.gui.root.after(0, lambda: messagebox.showinfo("提示", "代码输入已完成。"))
            return True

        except Exception as e:
            self.gui.log(f"代码格式化失败: {e}")
            self._remove_esc_hook()
            return False

    def _show_termination_message(self):
        """显示终止消息"""
        self.gui.root.after(0, lambda: messagebox.showinfo("提示", "用户已终止代码输入"))