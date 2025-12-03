import pyautogui
import time
import pyperclip
import keyboard
from tkinter import messagebox


class InputSimulator:
    def __init__(self, gui):
        self.gui = gui
        self.typing_active = True
        self.left_brace_count = 0
        self.line_count = 0
        self.esc_pressed = False

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

    def paste_code(self, code):
        """使用复制粘贴方式输入代码"""
        try:
            # 安装ESC键监听
            keyboard.on_press_key('esc', self.set_esc_pressed, suppress=False)

            # 清空编辑器
            screen_width, screen_height = pyautogui.size()
            x = screen_width // 2
            y = screen_height // 2
            pyautogui.click(x=x, y=y)
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('delete')
            time.sleep(0.5)

            # 检查ESC键
            if self.esc_pressed:
                self.gui.log("用户按下了ESC键，终止代码粘贴")
                self._show_termination_message()
                keyboard.unhook_all()
                return False

            # 复制代码到剪贴板
            pyperclip.copy(code)
            time.sleep(0.1)

            # 检查ESC键
            if self.esc_pressed:
                self.gui.log("用户按下了ESC键，终止代码粘贴")
                self._show_termination_message()
                keyboard.unhook_all()
                return False

            # 粘贴代码
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)

            # 检查ESC键
            if self.esc_pressed:
                self.gui.log("用户按下了ESC键，终止代码粘贴")
                self._show_termination_message()
                keyboard.unhook_all()
                return False

            # 格式化代码
            pyautogui.hotkey('alt', 'shift', 'f')
            time.sleep(0.5)

            self.gui.log("代码已通过复制粘贴完成输入")

            # 移除ESC键监听
            keyboard.unhook_all()

            # 显示完成消息
            self.gui.root.after(0, lambda: messagebox.showinfo("提示", "代码输入已完成"))
            return True

        except Exception as e:
            self.gui.log(f"复制粘贴失败: {e}")
            keyboard.unhook_all()
            return False

    def simulate_typing(self, text, is_first_chunk=False):
        """模拟键盘输入代码 - 输入左括号后删除编辑器自动补全的右括号，并处理换行和空格"""
        try:
            if is_first_chunk:
                self.gui.log("开始模拟键盘输入代码...")
                self.line_count = 0
                self.esc_pressed = False

                # 安装ESC键监听
                keyboard.on_press_key('esc', self.set_esc_pressed, suppress=False)

                # 检查ESC键
                if self.esc_pressed:
                    self.gui.log("用户按下了ESC键，终止代码输入")
                    self._show_termination_message()
                    keyboard.unhook_all()
                    return False

                # 点击屏幕中央激活编辑器
                screen_width, screen_height = pyautogui.size()
                x = screen_width // 2
                y = screen_height // 2
                pyautogui.click(x=x, y=y)

                time.sleep(0.1)

                # 检查ESC键
                if self.esc_pressed:
                    self.gui.log("用户按下了ESC键，终止代码输入")
                    self._show_termination_message()
                    keyboard.unhook_all()
                    return False

                pyautogui.hotkey('ctrl', 'a')  # 全选
                time.sleep(0.1)

                # 检查ESC键
                if self.esc_pressed:
                    self.gui.log("用户按下了ESC键，终止代码输入")
                    self._show_termination_message()
                    keyboard.unhook_all()
                    return False

                pyautogui.hotkey('delete')  # 删除
                time.sleep(0.1)

            if text.strip():
                i = 0
                while i < len(text):
                    # 检查ESC键
                    if self.esc_pressed:
                        self.gui.log("用户按下了ESC键，终止代码输入")
                        self._show_termination_message()
                        keyboard.unhook_all()
                        return False

                    char = text[i]

                    # 处理换行符
                    if char == '\n':
                        # 输入换行（回车键）
                        pyautogui.press('enter')
                        time.sleep(0.1)  # 等待编辑器自动缩进完成

                        self.line_count += 1

                        # 移动到下一个字符（跳过换行符本身）
                        i += 1

                        # 跳过原代码中紧跟换行符的所有空格
                        # 注意：这里只跳过原代码中的空格，编辑器自动添加的缩进保留
                        space_count = 0
                        while i < len(text) and text[i] == ' ':
                            space_count += 1
                            i += 1

                        if space_count > 0:
                            self.gui.log(f"第{self.line_count}行：跳过了{space_count}个空格")

                        # 继续处理下一个非空格字符
                        if i < len(text):
                            # 继续处理当前字符（已经指向非空格字符）
                            continue
                        else:
                            break

                    # 输入当前字符
                    pyautogui.write(char, interval=0.001)

                    # 如果是左括号，等待0.1秒后按Delete键删除编辑器自动补全的右括号
                    if char == '{':
                        time.sleep(0.1)  # 等待编辑器完成自动补全
                        pyautogui.press('delete')  # 删除自动补全的右括号

                    i += 1

            return True

        except Exception as e:
            self.gui.log(f"模拟键盘输入失败: {e}")
            keyboard.unhook_all()
            return False

    def finalize_formatting(self):
        """完成代码输入后的格式化操作"""
        try:
            time.sleep(0.2)
            self.gui.log(f"代码输入完成，共处理了{self.line_count}行")

            # 移除ESC键监听
            keyboard.unhook_all()

            self.gui.root.after(0, lambda: messagebox.showinfo("提示", "代码输入已完成。"))
            return True

        except Exception as e:
            self.gui.log(f"代码格式化失败: {e}")
            keyboard.unhook_all()
            return False

    def _show_termination_message(self):
        """显示终止消息"""
        self.gui.root.after(0, lambda: messagebox.showinfo("提示", "用户已终止代码输入"))